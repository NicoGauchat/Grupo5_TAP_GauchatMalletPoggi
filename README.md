# LibreNews

Aplicación web universitaria para reunir noticias de fuentes seleccionadas, organizarlas por categoría y permitir que cada usuario configure sus temas de interés. Prioriza RSS, atribuye siempre al medio original y muestra varias fuentes.

La marca visible es **LibreNews**. Los identificadores ya usados por PostgreSQL, Docker Compose, Render y el repositorio GitHub conservan sus nombres técnicos anteriores para mantener los datos locales y el servicio desplegado.

## Ya implementado

- Registro con nombre real e inicio de sesión con usuarios de Django. La bienvenida usa sólo el primer nombre; las cuentas anteriores sin nombre conservan el usuario como saludo.
- Preferencias individuales para once categorías, incluidas Salud, Medioambiente y Deportes.
- Página de noticias para usuarios autenticados, separada por sus categorías, con fuente, fecha y enlace original.
- Modelos y administración de categorías, fuentes, feeds y artículos.
- Ingesta de 26 feeds RSS de ocho medios, clasificación por etiquetas aprobadas y deduplicación exacta con categorías conservadas por origen.
- Filtros combinables por fuente, idioma y fecha; orden por recientes o importancia general estimada con IA.
- Categorías navegables con apertura editorial, grilla y carga progresiva sin recarga.
- Agrupamiento LLM persistente con una tarjeta por acontecimiento y todas sus coberturas originales desplegables.
- Fotografías temáticas locales y fotografías RSS de fuentes habilitadas, con crédito y respaldo ilustrativo.
- Arranque local con un comando PowerShell y PostgreSQL aislado.
- Búsqueda en títulos con stop words, stemming por idioma, índice GIN y ranking de relevancia.
- Botones para guardar o quitar noticias y una página privada Mis guardadas para cada usuario.
- Identidad editorial compartida en inicio, ingreso, registro, preferencias y noticias; fuentes locales y diseño adaptable.
- Limpieza de noticias de más de 14 días, con vista previa.
- Preparación de despliegue gratuito de Django en Render y PostgreSQL administrado en Supabase.
- Workflow de GitHub Actions para limpieza e ingesta cada dos horas, de 06:00 a medianoche en hora argentina; pendiente de activar.

## Funcionalidades previstas

- Crear el proyecto de Supabase, desplegar Django en Render y activar la recolección periódica.
- Evaluar precisión de agrupamiento, clasificación e importancia con Gemini real y ampliar cobertura según su resultado.
- Incorporar GDELT como complemento y evaluar la calidad del agrupamiento de coberturas.

## Stack acordado

- Python y Django para la aplicación web, autenticación, interfaz del servidor e ingesta.
- PostgreSQL para usuarios, preferencias, fuentes y noticias.
- Plantillas HTML de Django, CSS y JavaScript mínimo para la interfaz.
- Render para alojar Django y servir archivos estáticos.
- Supabase para PostgreSQL; GitHub Actions para ejecutar periódicamente el comando de ingesta.

## Arquitectura resumida

```text
Feeds RSS → comando de ingesta Django → normalización y deduplicación → PostgreSQL
                                                                      ↑
Navegador → páginas Django con autenticación y preferencias ──────────┘
```

Render aloja la aplicación Django y Supabase PostgreSQL mantiene los datos. La configuración se declara en `render.yaml`; las credenciales se cargan al crear el servicio y no se versionan. Se prevé usar los planes gratuitos sin agregar recursos pagos.

## Estado

El proyecto incluye Django, PostgreSQL, usuarios y 26 feeds de Clarín, EL PAÍS, MIT News, Los Andes, Cinco Días, Perfil, NASA y elDiario.es. Los artículos importados pueden consultarse desde `/admin/` y cada usuario ve los de sus categorías en `/noticias/`. Agência Brasil no se incorpora por decisión del usuario.

El próximo paso vigente se mantiene en [STATUS.md](./STATUS.md).

## Desarrollo local en Windows

Requisitos: Python 3.13 y Docker Desktop con el motor iniciado. Desde PowerShell, en la raíz del repositorio:

```powershell
.\dev.ps1
```

El comando prepara `.venv`, instala las dependencias existentes, crea `.env.local` con claves aleatorias cuando falta, inicia PostgreSQL 17 en el proyecto Docker independiente `sitio-noticias-local`, espera a que esté disponible, aplica migraciones e importa RSS reales si no hay noticias. Si `.env.local` contiene `GEMINI_API_KEY`, genera el resumen cuando falta un resultado de las últimas dos horas. Luego sirve Django con recarga automática en `http://127.0.0.1:8000/`. Registrarse y elegir categorías; no se crean cuentas predeterminadas. Ctrl+C detiene la web; el volumen conserva la base.

Para actualizar los RSS antes de abrir la aplicación:

```powershell
.\dev.ps1 -RefreshFeeds
```

Para forzar también un resumen nuevo, combinar ambos modificadores:

```powershell
.\dev.ps1 -RefreshFeeds -RefreshBriefing
```

`-RefreshFeeds` descarga los RSS aunque no hayan cambiado, para completar las fotografías de noticias existentes. `-RefreshBriefing` puede usarse solo. Configurar `GEMINI_API_KEY` únicamente en `.env.local`, nunca en el código ni por chat. Una falla de Gemini se informa y no impide iniciar la web; la recarga automática y las visitas no llaman al modelo.

Un feed inaccesible produce un aviso y se inicia la web con los datos disponibles. Si Docker está detenido o no responde, se solicita iniciarlo o reiniciarlo. El puerto inicial de PostgreSQL es `5433`; puede cambiarse en `.env.local` si ya está ocupado. El perfil `config.local_settings` exige un host local y carga ese archivo antes que cualquier configuración de producción. El script restaura las variables del proceso al salir; no utiliza credenciales remotas. `.env.local` y `.venv` están ignorados por Git.

Con la base iniciada, también pueden ejecutarse comandos locales directamente:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser --settings=config.local_settings
.\.venv\Scripts\python.exe manage.py ingest_feeds --refresh --settings=config.local_settings
.\.venv\Scripts\python.exe manage.py generate_news_briefing --force --settings=config.local_settings
```

Para detener la base conservando los datos:

```powershell
docker compose --env-file .env.local --project-name sitio-noticias-local down
```

## Explorar noticias

Mis noticias (`/noticias/`) presenta tarjetas fotográficas de las categorías elegidas, en orden alfabético estable. Incluye las categorías sin noticias y conserva el módulo de presentación LLM existente. Cada tarjeta lleva a `/noticias/categoria/<slug>/`; sólo se accede a categorías elegidas en Mis categorías.

Al crear una cuenta se pide «Nombre real» además del usuario y la contraseña. Se guarda en el campo `first_name` del usuario integrado de Django, sin migración nueva. El saludo toma la primera palabra del nombre; el nombre de usuario sigue siendo el dato para ingresar. Las cuentas creadas antes de este cambio conservan el saludo con su usuario si no tienen nombre registrado.

Dentro de cada categoría se combinan búsqueda en títulos, fuente, idioma, fecha y orden. Sin búsqueda, la primera tarjeta abre el listado como «La más reciente» o «La más importante», seguida de nueve tarjetas. La grilla tiene tres columnas en escritorio amplio, dos en tamaños intermedios y una en móvil; la apertura se apila en móvil. Al buscar, se muestran diez tarjetas uniformes y el selector permite relevancia, recientes o importancia. Los titulares completos permanecen visibles. Títulos y fotografías enlazan al medio original en una nueva pestaña, al igual que Mis guardadas y las fuentes del resumen.

«Fecha» ofrece Hoy, Últimas 24 horas, Últimos 3 días, Última semana y Últimos 14 días (inicial). Hoy comienza a medianoche en Buenos Aires; los otros períodos son ventanas móviles y se excluyen fechas futuras. Se selecciona un acontecimiento si alguna cobertura de la categoría coincide con el período; el desplegable conserva las demás coberturas autorizadas de los últimos 14 días. Cambiar fecha u orden reinicia la lista; Ver más y Guardar conservan ambas selecciones. Un cursor de Hoy vence al cambiar el día local. No hay archivo histórico ni rangos fuera de los 14 días.

«Más importantes» ordena por el puntaje general del acontecimiento, luego por relevancia si hay búsqueda, fecha e ID. No oculta las noticias de puntaje bajo; las no evaluadas quedan al final, identificadas. «Más recientes» ordena por fecha e ID, también al buscar. Sin elegir otro orden, una búsqueda mantiene el ranking de relevancia anterior. La explicación se despliega bajo «Importancia general N/5 · IA»: es una estimación del modelo, no una medida objetiva ni una certificación de veracidad.

«Ver más» agrega nueve noticias sin recargar ni desplazar la lectura. Mantiene filtros, controla solicitudes repetidas y permite reintentar ante fallos. Al finalizar indica que ya se vieron todas. La continuación usa un cursor firmado vinculado a categoría, filtros y modo de clasificación, ordenado por fecha/ID y también relevancia cuando corresponde. No depende de posiciones desplazadas por nuevas ingestas. Los enlaces vencen a los 14 días. La URL conserva `visible` para reconstruir la cantidad cargada; la posición se recuerda temporalmente por usuario en el navegador. Los resultados se vuelven a validar al reconstruir: pueden variar si ingresaron o vencieron noticias. Sin JavaScript, Ver más y Guardar funcionan mediante navegación y POST normales. Guardar/quitar dentro de una categoría conserva los lotes y la posición mediante los mismos POST con CSRF.

La búsqueda admite hasta 200 caracteres y se limita a títulos. PostgreSQL aplica stop words y stemming en español, inglés y portugués, incluidos códigos regionales, y exige todas las palabras significativas. Otros idiomas usan `simple`. No busca fragmentos arbitrarios, no traduce ni agrega sinónimos. Una consulta compuesta sólo por stop words no devuelve resultados. El índice GIN existente se conserva.

Las fotografías de categoría son ocho archivos WebP locales con licencia Pexels, documentados con sus autores y enlaces en SOURCES. El collage de la portada pública reutiliza Argentina, geopolítica y tecnología en blanco y negro mediante HTML/CSS. En Mis noticias, un solo banner reúne el saludo, el acceso a Mis categorías y el resumen de las últimas 24 horas, sin ese collage. Los títulos de categorías conservan el blanco al pasar el cursor o enfocar; la acción cambia a coral claro.

Las fotografías RSS requieren `Feed.show_images`; `0013` incorpora URL/crédito, `0014` habilitó MIT y `0015` habilita los once feeds actuales por decisión expresa del usuario para su presentación educativa. Esa decisión no acredita una licencia de los medios; SOURCES conserva las condiciones revisadas. Nuevas fuentes siguen deshabilitadas por defecto. Se mantienen créditos, atribución y respaldo temático rotulado «Imagen ilustrativa» si falta o falla una fotografía o se deshabilita el feed para imágenes. No se descargan ni almacenan fotografías RSS en el servidor.

Se investigó una posible imagen diaria por categoría ligada al acontecimiento más importante. Aún no se implementó: se puede elegir entre las noticias publicadas ese día en Buenos Aires que pertenezcan a la categoría, tengan importancia IA y una imagen RSS permitida, y enlazar la tarjeta a esa noticia; si no hay candidata, conservar la imagen ilustrativa. El resultado del día sería provisional mientras ingresan noticias y se calculan puntajes. Para fijarlo durante toda la jornada haría falta guardar la selección diaria; para afirmar el acontecimiento definitivo habría que esperar al cierre del día. No se propone usar una foto de stock como si documentara un hecho concreto. SOURCES registra la evaluación de permisos y rendimiento.

La ingesta actualiza imágenes y créditos de noticias existentes de su feed original, sin sustituir la atribución por un origen secundario. Para completar imágenes autorizadas ya almacenadas, ejecutar `ingest_feeds --refresh`; sólo pueden recuperarse las entradas que todavía estén en el RSS. Los resúmenes RSS siguen deshabilitados en los once feeds. No se guardan cuerpos de artículos.

La clasificación por reglas conserva los alias revisados en `news/category_aliases.py` y las categorías por origen. `--refresh` reemplaza el aporte del feed consultado y combina las categorías de los otros orígenes. La clasificación LLM permanece independiente, como se describe a continuación.

### Una tarjeta por acontecimiento

Las categorías reúnen las coberturas agrupadas por Gemini en una tarjeta. Se conserva el titular original de la cobertura más reciente que coincide con categoría y filtros (la de mayor relevancia al buscar), identificando su medio; no se genera un titular supuestamente neutral. «Ver N fuentes · M coberturas» despliega todos los titulares, medios, fechas y enlaces originales disponibles del acontecimiento, en orden alfabético de medio. N cuenta medios distintos, aunque alguno publique varias coberturas. El filtro por fuente, idioma o búsqueda selecciona acontecimientos; el desplegable mantiene sus otras coberturas aunque no coincidan con esos filtros o categorías. Los totales y «Ver más» cuentan acontecimientos. Guardar sigue guardando el artículo representativo, no todas las coberturas.

Aplicar las migraciones antes de ejecutar el comando:

```powershell
python manage.py migrate
python manage.py group_news_ai
```

En el entorno de desarrollo se agrega `--settings=config.local_settings` a ambos comandos. La migración `0016` crea `Story`, vincula opcionalmente cada artículo y habilita `Feed.allow_ai_grouping` en los once feeds originales; `0018` lo habilita en los quince RSS nuevos revisados. Otras fuentes creadas en administración comienzan deshabilitadas. Revocar el permiso deja inmediatamente de agrupar y de exponer sus coberturas dentro de otros grupos; sus artículos siguen disponibles individualmente y sin puntaje visible.

Se procesan hasta cien pendientes por ejecución, en lotes de treinta. Primero se revisan noticias de grupos anteriores a la comprobación de identidad y después las aún no agrupadas, priorizando las publicaciones recientes dentro de los 14 días. `--limit 500` permite avanzar más en una reparación o carga inicial. Cada lote compara noticias con el artículo de menor ID aún vigente de cada acontecimiento autorizado y comprobado: la referencia no cambia al entrar un titular más reciente. Se envían únicamente ID, título, medio, idioma, fecha e ID del grupo. El modelo debe devolver todos los IDs nuevos exactamente una vez, sin referencias inventadas. Una noticia sola también forma un acontecimiento; las nuevas coberturas pueden incorporarse después.

Antes de guardar una unión, una segunda llamada independiente compara cada noticia con la referencia del grupo propuesto. Exige coincidencia del hecho concreto; compartir tema, protagonista o empresa no alcanza. Una negativa deja esa noticia separada; una respuesta inválida o un fallo de API deja el lote pendiente. Los grupos individuales no necesitan esta llamada. Cada llamada tiene timeout de 60 segundos y un intento. No hay llamadas al navegar. Los candidatos se comparan en bloques de hasta 500; las noticias sin coincidencia continúan al siguiente bloque. Esto puede aumentar las solicitudes. Los grupos comprobados existentes siguen sin fusionarse automáticamente.

La migración `0019` marca los grupos anteriores como pendientes de revisión, conservando asociaciones, titulares, guardados e importancia histórica. Mientras se reprocesan se muestran sus noticias individualmente, sin atribuirles el puntaje anterior del grupo ni contar noticias ajenas como coberturas. `group_news_ai` los revisa automáticamente y crea grupos comprobados; sus puntajes se calculan después con `score_news_ai`. Incorporar una cobertura borra el puntaje anterior de ese grupo hasta reevaluarlo. La importancia sigue correspondiendo al acontecimiento completo.

Para reparar remotamente, ejecutar **Ingesta y limpieza de noticias → Run workflow → mode: repair-grouping**, con `grouping_limit` de 100 o 500. Si el despliegue aún no aplicó `0019`, marcar `apply_grouping_migration`: permite únicamente esa migración hacia adelante y rechaza cualquier otro plan o retroceso. Este permiso es manual; las ejecuciones programadas continúan comprobando el esquema sin modificarlo. Después evalúa Gemini con seis titulares ficticios sobre tres hechos y, sólo si conserva los pares correctos separados de los demás, ejecuta agrupamiento e importancia. Omite descarga RSS, clasificación y resumen. También se puede ejecutar la comprobación sin leer ni escribir noticias con `python manage.py check_news_grouping`; requiere la clave principal y consume una o dos solicitudes. El flujo periódico normal sigue usando cien pendientes y las etapas habituales.

El agrupamiento es conservador: compartir tema, empresa o protagonista no basta. No fusiona automáticamente grupos ya existentes y puede equivocarse al interpretar titulares; todavía requiere evaluación con Gemini real en este entorno. Desde la administración de artículos, `story` permite corregir el grupo o dejarlo vacío para reprocesar; la administración de acontecimientos permite inspeccionar sus miembros. Borrar un grupo no borra artículos. La limpieza de 14 días elimina grupos sin artículos, sin extender la retención de guardados. Ante ingestas, correcciones o vencimientos durante la lectura, la continuación refleja los datos vigentes; el navegador evita repetir tarjetas por ID de acontecimiento.

### Dos claves Gemini: reparto por función

| Variable / secreto | Funciones asignadas |
|---|---|
| `GEMINI_API_KEY` (existente) | Clasificación y agrupamiento |
| `GEMINI_API_KEY_SECONDARY` (nueva) | Importancia general y resumen diario |

Agregar tu segunda clave en **GitHub → Settings → Secrets and variables → Actions → New repository secret**, con nombre `GEMINI_API_KEY_SECONDARY`, conservando el secreto existente. Para desarrollo local, agregarla a `.env.local`; el perfil local carga ambas variables automáticamente. No versionar valores ni compartirlos por chat. El código no crea claves ni copia secretos de GitHub a la computadora; son configuraciones independientes. La presencia del secreto principal se comprobó, pero el secundario todavía debe cargarlo el usuario.

El reparto es fijo: cada función usa la clave asignada y no cambia de cuenta al agotarse una cuota, fallar la conexión o recibirse una respuesta inválida. Si la segunda variable está ausente o vacía, se conserva compatibilidad con la instalación anterior: todas las funciones usan `GEMINI_API_KEY`, con aviso en Actions y en el arranque local. Si sólo existe la secundaria, se pueden actualizar importancia de grupos existentes y resumen; clasificación y agrupamiento quedan pendientes. Los estados de la web reconocen la clave de resumen correspondiente. Las visitas siguen sin llamar al proveedor.

Con cien pendientes en cada etapa y un bloque de candidatos por lote, la principal puede hacer diez llamadas de clasificación y hasta ocho de agrupamiento, incluidas las comprobaciones de identidad; la secundaria, diez de importancia y una de resumen si corresponde regenerarlo. La caché, cantidad de grupos y bloques extra de candidatos cambian esa cuenta; no garantiza 50 % de tokens, gasto o cuota. Los límites efectivos y la facturación se revisan en AI Studio para cada proyecto autorizado. Según la [documentación de Gemini](https://ai.google.dev/gemini-api/docs/rate-limits), la cuota es por proyecto y no por clave: dos claves del mismo proyecto no reparten la capacidad. No se implementa rotación de claves como respuesta a un límite ni se habilita facturación.

### Clasificación de titulares

La clasificación admite once categorías. Salud, Medioambiente y Deportes se incorporan en `0018`, con descripciones LLM y etiquetas RSS observadas. Las once vigentes son Argentina, Política argentina, Geopolítica, Economía, Mercados y finanzas, Tecnología, Inteligencia artificial, Ciencia, Salud, Medioambiente y Deportes.

El comando `python manage.py classify_news_ai` envía en lotes de diez el título, la fuente y el idioma de noticias recientes aún pendientes a `gemini-3.1-flash-lite`. Sólo acepta respuestas con IDs del lote y slugs de las once categorías previstas. Guarda las categorías LLM separadas de las categorías por reglas, junto con fecha y modelo; una respuesta inválida o un error de API deja el lote pendiente para la siguiente ejecución. Procesa hasta cien noticias por ejecución, empezando por las más recientes dentro de los últimos 14 días. Puede reducirse con `--limit 20`. No envía artículos completos, resúmenes RSS, etiquetas no guardadas ni datos de usuarios.

Cada usuario elige en «Mis categorías» entre «Ambas», «Sólo reglas» y «Sólo IA»; «Ambas» es el valor inicial y muestra la unión de ambas clasificaciones. «Sólo IA» puede mostrar menos noticias hasta que termine el procesamiento; las pendientes más recientes se procesan primero. Esta combinación no quita una categoría incorrecta asignada por las reglas; las predicciones se conservan aparte para poder compararlas. Mis guardadas sigue mostrando los artículos guardados según su política de 14 días.

Para activar la IA sin pagar, el titular de la cuenta crea un proyecto y una clave de **Gemini API Free Tier** en [Google AI Studio](https://aistudio.google.com/apikey), comprueba allí la cuota de `gemini-3.1-flash-lite` y mantiene la facturación desactivada. Luego agrega la clave como secreto de repositorio `GEMINI_API_KEY` en **GitHub → Settings → Secrets and variables → Actions**. El workflow de ingesta ejecuta la clasificación después de `ingest_feeds` cuando existe ese secreto. Para el perfil local, colocar la clave sólo en `.env.local` y usar `--settings=config.local_settings`. No pegar la clave en el código ni enviarla por chat. Google indica que los datos enviados en su nivel gratuito pueden utilizarse para mejorar sus productos; revisar sus [condiciones](https://ai.google.dev/gemini-api/terms) antes de activar la clave. Los límites efectivos se muestran en [AI Studio](https://ai.google.dev/gemini-api/docs/rate-limits).

### Presentación de las últimas 24 horas

En Mis noticias aparece como «Resumen»: sucesos en columnas en escritorio y apilados en móvil, con fecha de actualización y fuentes plegadas bajo «Ver N fuentes». Los desplegables funcionan con teclado y sin JavaScript; al abrirlos muestran el medio y el titular completo, enlazados en otra pestaña. El número de titulares analizados queda al pie.

El workflow y el arranque local ejecutan el mismo comando `generate_news_briefing`. La migración `0015` habilita los once feeds actuales para esta síntesis educativa; fuentes nuevas conservan el permiso desactivado. Se analizan hasta 250 titulares elegibles de las últimas 24 horas, los más recientes primero con desempate por ID; si hay más se informa el recorte. Se envían título, fuente, fecha e idioma, sin artículos completos ni resúmenes RSS. El modelo agrupa sucesos y selecciona hasta tres de importancia alta (4 o 5), con referencias validadas. Un resultado vacío también es válido y se reutiliza durante dos horas; `--force` permite regenerar.

Cada intento conserva estado generado/vacío/error y un código seguro. La llamada tiene un timeout de 60 segundos y un solo intento. Ante cuota, conexión o respuesta inválida se mantiene el último resultado válido mientras sus fuentes sigan activas, habilitadas y dentro de las últimas 24 horas, con un aviso de actualización fallida. La interfaz diferencia falta de configuración, fuentes deshabilitadas, noticias ausentes, sucesos sin importancia suficiente y generación pendiente. Las visitas no llaman a Gemini y los mensajes no exponen secretos ni respuestas técnicas del proveedor.

También puede ejecutarse manualmente con `python manage.py generate_news_briefing` después de aplicar las migraciones. Como ocurre con la clasificación, el nivel gratuito no garantiza cuotas fijas: se revisan en AI Studio y una cuota agotada no activa facturación por sí sola.

«Argentina» combina noticias de política nacional de Clarín y Los Andes con economía argentina de Los Andes. «Mercados y finanzas» muestra noticias sobre bolsa, inversiones y finanzas de Cinco Días y artículos pertinentes de EL PAÍS. Son titulares y enlaces periodísticos; no hay cotizaciones bursátiles en tiempo real. Las dos categorías se pueden elegir en «Mis categorías» y aparecen como tarjetas en `/noticias/`.

## Actualizar una instalación existente

Aplicar `0017` y `0018` con `python manage.py migrate`. `0017` agrega puntaje, explicación, fecha/modelo de evaluación, autoría RSS y enlace de licencia por medio, conservando artículos y grupos existentes. `0018` suma tres categorías y quince feeds revisados (26 en total, ocho medios): nueve canales argentinos de Perfil, Clarín y Los Andes; cuatro nuevos de EL PAÍS y uno de elDiario.es en Europa; y NASA Technology en Estados Unidos. Los nuevos canales mantienen imágenes, resúmenes RSS y síntesis desactivados; permiten agrupar y evaluar titulares. La licencia y autoría de elDiario.es acompañan sus enlaces, también en guardadas. La reversión de `0018` desactiva los canales agregados, sin borrar artículos, categorías ni preferencias. Reaplicarla no fuerza la activación de canales ya existentes que el usuario haya desactivado.

Después de importar, ejecutar:

```powershell
python manage.py classify_news_ai
python manage.py group_news_ai
python manage.py score_news_ai
```

`score_news_ai` usa el modelo existente para hasta cien acontecimientos por ejecución, en lotes de diez; `--limit 500` aumenta la carga y `--force` reevalúa los ya puntuados. Envía hasta tres titulares de medios distintos por grupo, con fechas e idiomas. Asigna importancia absoluta 1–5 por alcance, impacto, novedad y urgencia; fama, marca y número de publicaciones no bastan. Conserva una razón de hasta 300 caracteres, fecha y modelo. Valida IDs, puntajes y explicaciones antes de guardar cada lote de manera atómica. Nuevas coberturas o correcciones administrativas del grupo dejan pendiente la reevaluación, conservando el puntaje anterior ante fallos. El cliente tiene timeout de 60 segundos y un intento. Sin clave o ante cuota no oculta noticias ni transforma pendientes en puntaje cero: cero sólo se usa internamente para colocarlas al final. Actions y `dev.ps1` incorporan estas etapas cuando hay clave. Las visitas siguen sin llamar a Gemini.

Las tres categorías nuevas utilizan ilustraciones SVG locales propias, sin descargar fotografías adicionales. Los controles de fecha y orden no requieren variables nuevas; `.env.example` mantiene `GEMINI_API_KEY`. La configuración de producción y los secretos se cargan como antes.

La migración `0015_educational_feeds_and_briefing_status` habilita imágenes y síntesis en los once feeds actuales, elimina sus validadores HTTP para que la siguiente ingesta descargue el contenido y añade estado/código de los intentos. Su reversión restaura los permisos previos (sólo MIT con imágenes, ningún feed en la síntesis). Los validadores se reconstruyen al consultar cada RSS. Aplicar migraciones y ejecutar `ingest_feeds --refresh` para completar fotografías existentes. Las migraciones anteriores incorporan la presentación, el permiso individual y las categorías IA; la clasificación continúa independiente. Sin clave, RSS y reglas siguen funcionando.

La migración `0009_article_article_title_search_gin` crea el índice de búsqueda para los títulos existentes y futuros en PostgreSQL. Aplicar con `python manage.py migrate`; el build de Render ejecuta este comando. La construcción normal del índice puede bloquear escrituras mientras termina.

La migración `0008_savedarticle` crea la tabla de noticias guardadas. Ejecutar `python manage.py migrate` al actualizar la aplicación; el build configurado de Render ya incluye ese comando.

Cada noticia de Mis noticias tiene un botón Guardar. Después de guardarla, el botón permite quitarla. Mis guardadas (`/guardadas/`) muestra sólo las noticias del usuario conectado, empezando por las guardadas más recientemente, con diez por página. Se pueden consultar aunque cambien las categorías elegidas. Las noticias vencen a los 14 días desde su publicación, incluidas las guardadas; guardar no extiende ese plazo. Los formularios conservan filtros y página al regresar.

Cuando no hay resultados, el sitio indica si falta elegir categorías, si hay filtros inválidos, si los filtros no encuentran noticias o si las categorías todavía no tienen noticias disponibles, y ofrece un enlace para continuar. Mis guardadas vacía invita a visitar Mis noticias.

Después de incorporar estos cambios, ejecutar `python manage.py migrate` contra la base correspondiente antes de la ingesta. La migración `0007_article_origins` añade los orígenes y copia feed, GUID y categorías de las noticias existentes; conserva títulos, enlaces, fechas y atribución. No requiere recrear ni vaciar la base. Render la aplicará mediante el build ya configurado; Actions exige que esté aplicada y no modifica el esquema por su cuenta.

La migración se verificó con datos sintéticos en SQLite. Su aplicación y comprobación en PostgreSQL real quedan para el siguiente bloque de despliegue.

## Limpieza de noticias antiguas

```powershell
python manage.py purge_old_articles --dry-run
python manage.py purge_old_articles
```

El primer comando cuenta sin borrar; el segundo elimina de la base configurada. Se toma la fecha de publicación: se conserva una noticia de exactamente 14 días y se elimina cuando supera esa edad. Para registros sin fecha de publicación se usa la captura. Se limpian también noticias de feeds desactivados. Se conservan fuentes, feeds, categorías y preferencias; se eliminan sus orígenes y todas las asociaciones de categorías de los artículos borrados.

## Ingesta periódica con GitHub Actions

[.github/workflows/ingest-feeds.yml](./.github/workflows/ingest-feeds.yml) tiene diez ejecuciones previstas todos los días: **06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00 y 00:00**, en `America/Argentina/Buenos_Aires`. Usa el cron `0 0,6,8,10,12,14,16,18,20,22 * * *` y la zona horaria explícita. Ejecuta limpieza e ingesta, y permite una ejecución manual desde Actions fuera de esa franja. Usa Python 3.13, permisos de lectura y una única ejecución de mantenimiento a la vez. La limpieza ocurre antes de consultar los feeds para que un fallo de RSS no impida aplicar la conservación.

Medianoche cierra la jornada: no hay consultas previstas entre 00:00 y 06:00. Los feeds cortos pueden perder entradas durante esa pausa o en ráfagas. Las consultas cada dos horas reducen el riesgo durante el día, sin garantizar captura exhaustiva ni puntualidad del job. La comprobación de actividad se documenta en `SOURCES.md`.

GitHub Actions y Render usan el mismo proyecto PostgreSQL de Supabase. GitHub no puede acceder al PostgreSQL local en `127.0.0.1`. No se crea una base temporal para la ingesta ni se expone el puerto local.

Para activarlo:

1. Crear el proyecto de Supabase en **East US (North Virginia)** para usar una región cercana a Render Virginia.
2. En Connect → Session pooler, copiar host, nombre de base, usuario y contraseña. La configuración esperada es puerto `5432` y SSL `require`; el pooler compartido admite IPv4, necesario para estos servicios.
3. Subir `render.yaml` a `main` y crear un Blueprint desde el panel de Render. Al aplicarlo, completar las variables de conexión a Supabase cuando Render las solicite. El build instala las dependencias, recoge archivos estáticos y aplica migraciones; no crea una segunda base.
4. En el servicio web de Render, completar `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_HOST`; `DJANGO_SECRET_KEY` se genera automáticamente por el Blueprint. La configuración de servidor usa puerto `5432` y SSL `require`, y falla temprano si falta una credencial en lugar de intentar PostgreSQL local.
5. En Settings → Secrets and variables → Actions, agregar los secretos `DJANGO_SECRET_KEY`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_HOST`. Usar los mismos valores de conexión de Supabase; `DJANGO_SECRET_KEY` puede generarse con el comando indicado arriba.
6. En Variables → Actions, establecer `POSTGRES_PORT=5432`, `POSTGRES_SSLMODE=require` y `NEWS_INGESTION_ENABLED=true`. Ejecutar manualmente «Ingesta y limpieza de noticias» para comprobar la conexión. Para pausar, cambiar `NEWS_INGESTION_ENABLED` a `false`.
7. El plan gratuito de Render no incluye Shell. Para crear la cuenta administradora, configurar temporalmente el `.env` local con las credenciales de Supabase y ejecutar `python manage.py createsuperuser`; después, restaurar la configuración local. Gestionar feeds desde `/admin/`.

El workflow comprueba los secretos sin imprimir sus valores y exige migraciones aplicadas; no modifica automáticamente el esquema público. Las ejecuciones 62 a 65 del 25/10/2026 se detuvieron en `migrate --check`, antes de la limpieza, la ingesta y el resumen. Las últimas migraciones se deben aplicar a la misma base que usa Actions, mediante el build de Render o `python manage.py migrate` desde un entorno autorizado; luego conviene ejecutar el workflow manualmente y comprobar cada etapa. Si el control vuelve a fallar, la etapa de diagnóstico muestra el plan de migraciones o un error de conexión. Si falla un feed, continúa con los demás y finalmente marca la ejecución como fallida. Los resultados están en Actions. GitHub puede retrasar horarios y desactiva la programación en repositorios públicos tras 60 días sin actividad. Revisar la cuota gratuita de Actions antes de activarlo. Referencias: [horarios](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) y [secretos](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).

## Despliegue web en Render

`render.yaml` describe un servicio web gratuito, vinculado a la rama `main`, con Django, Gunicorn y WhiteNoise. Render genera `DJANGO_SECRET_KEY`; el resto de las credenciales de Supabase se solicitan al crear el Blueprint. Los cambios desplegados sirven archivos estáticos mediante WhiteNoise. Las migraciones se ejecutan durante el build, y las noticias continúan en PostgreSQL aunque el servicio se reinicie. `config.settings` es el perfil de producción: no lee `.env.local`, usa PostgreSQL por el puerto 5432 con SSL obligatorio y agrega automáticamente el hostname público de Render a `ALLOWED_HOSTS` y a los orígenes CSRF. Para un dominio propio, agregarlo en `DJANGO_ALLOWED_HOSTS` y su origen HTTPS en `DJANGO_CSRF_TRUSTED_ORIGINS`; `config.local_settings` y `dev.ps1` quedan reservados al desarrollo.

El plan gratuito de Render duerme el servicio tras 15 minutos sin solicitudes y puede tardar cerca de un minuto en despertar. Tiene 750 horas de instancia por espacio de trabajo al mes y un sistema de archivos efímero; por eso no guardamos noticias en el disco de Render. Supabase Free ofrece 500 MB de base de datos y puede pausar proyectos con poca actividad durante siete días. La ingesta programada puede ayudar a mantener actividad, pero hay que revisar el estado y el uso desde ambos paneles. Render indica que Free es para pruebas y proyectos personales, no para aplicaciones con requisitos de disponibilidad; además, los excesos de cuota pueden generar cargos si se agrega un medio de pago. Para mantener este despliegue sin costo, no agregar recursos pagos ni un medio de pago y revisar las cuotas. Referencias: [límites gratuitos y condiciones de Render](https://render.com/docs/free), [preguntas frecuentes de facturación de Render](https://render.com/docs/faq), [despliegue Django en Render](https://render.com/docs/deploy-django), [conexiones PostgreSQL de Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres) y [pausa de proyectos Supabase](https://supabase.com/docs/guides/platform/free-project-pausing).

## Verificación

### Visitas automáticas para reducir la suspensión

El workflow **Mantener LibreNews activo** (`.github/workflows/keep-alive.yml`) visita `https://sitio-noticias.onrender.com/` cada diez minutos, todos los días, en los minutos 7, 17, 27, 37, 47 y 57. Se activa al publicar el archivo en `main`, con Actions habilitado; también admite **Run workflow**. Hace una solicitud HTTPS a la portada, sin iniciar sesión, ejecutar IA ni descargar imágenes. Comprueba que responda LibreNews y reintenta hasta tres veces si el servicio está despertando; una página de espera de Render no cuenta como éxito.

Para pausarlo, establecer la variable de repositorio `WEB_KEEP_ALIVE_ENABLED=false` o deshabilitar este workflow en Actions. Para cambiar el destino, establecer `WEB_KEEP_ALIVE_URL` con la URL HTTPS de la portada. No necesita secretos ni variables en `.env`. Corre por separado de la ingesta y no ocupa su grupo de concurrencia.

Render Free suspende tras quince minutos sin tráfico entrante. Diez minutos dejan margen, pero GitHub puede retrasar u omitir ejecuciones y desactivar la programación en repositorios públicos tras sesenta días sin actividad: no garantiza disponibilidad continua. Mantener una única instancia encendida todo un mes de 31 días consume hasta 744 de las 750 horas gratuitas compartidas del workspace; otras instancias también consumen ese cupo. Referencias: [Render Free](https://render.com/docs/free) y [programación de Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

### Controles locales

Con el entorno virtual activado:

```powershell
python manage.py test --settings=config.test_settings
python manage.py check --settings=config.test_settings
python manage.py makemigrations --check --dry-run --settings=config.test_settings
```

`config.test_settings` usa SQLite en memoria y una clave exclusiva para pruebas: permite verificar sin `.env`, Docker, credenciales reales ni `collectstatic`. Sólo en pruebas se desactiva la redirección HTTPS, se usa almacenamiento estático sin manifiesto y se excluye WhiteNoise; producción mantiene su configuración. La suite cubre filtros, protección de acceso, categorías, paginación, guardadas, conservación, orígenes, reclasificación, GUID y migración con datos existentes. En SQLite se omiten las trece pruebas específicas de PostgreSQL y el índice GIN no se crea; buscar muestra un aviso de indisponibilidad, sin simular stemming ni ranking.

Para ejecutar la suite completa, configurar las variables `POSTGRES_*` para una instancia PostgreSQL de desarrollo y una cuenta con permiso para crear bases, y ejecutar:

```powershell
python manage.py test --settings=config.postgres_test_settings --noinput
```

Django crea una base `test_<POSTGRES_DB>` separada y la elimina al terminar. Esta configuración conserva los ajustes aislados de pruebas; verifica búsqueda por idioma, stop words, stemming, relevancia, paginación, uso del índice y migración reversible con noticias existentes. Las configuraciones de pruebas no deben usarse para ejecutar o desplegar la aplicación.

## Documentación

- [PROJECT.md](./PROJECT.md): alcance, arquitectura y decisiones vigentes.
- [ARCHITECTURE-LEGACY.md](./ARCHITECTURE-LEGACY.md): copia de referencia de la arquitectura anterior de TypeScript, Next.js y Supabase.
- [STATUS.md](./STATUS.md): estado operativo y único próximo paso.
- [SOURCES.md](./SOURCES.md): feeds investigados y políticas por fuente.
- [AGENTS.md](./AGENTS.md): reglas de trabajo y actualización documental.
- [.env.example](./.env.example): variables previstas, sin credenciales reales.
