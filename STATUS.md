# Estado del proyecto

**Última actualización:** 2026-10-23
**Objetivo actual:** completar el primer bloque de la entrega 3 con clasificación por IA y presentación de la última ingesta.

## Último paso completado

Se implementó la clasificación adicional de titulares con `gemini-3.1-flash-lite`: migración `0010`, categorías LLM separadas de las reglas, fecha y modelo de procesamiento, lotes de diez con validación estricta de IDs y slugs, y comando `classify_news_ai` para noticias pendientes de los últimos 14 días. Cada usuario puede elegir «Ambas», «Sólo reglas» o «Sólo IA» en preferencias; el valor inicial es «Ambas». GitHub Actions ejecuta el comando después de la ingesta cuando el usuario cargue el secreto `GEMINI_API_KEY`. La clave y AI Studio quedan exclusivamente a cargo del usuario; no se creó ni configuró ninguna credencial. Un fallo de API deja las noticias pendientes y no cambia la clasificación por reglas. Se agregó `google-genai==2.33.0`; PROJECT registra revisión de licencia, mantenimiento, documentación oficial y proyectos comparables. Se actualizaron README y `.env.example`. SOURCES no requiere cambios: siguen los mismos feeds, campos permitidos y políticas. La API real y PostgreSQL remoto no se probaron sin la clave ni credenciales del usuario. Las pruebas locales SQLite fueron 57 en total: 45 aprobadas y 12 omitidas por requerir PostgreSQL; `manage.py check`, `makemigrations --check --dry-run` y `git diff --check` pasaron.

Se definió el primer bloque de la entrega 3 sin cambiar código: conservar la clasificación actual por etiquetas y respaldo, agregar predicciones LLM separadas, y generar una presentación breve a partir de los titulares nuevos de cada ingesta. Se eligió inicialmente `gemini-3.1-flash-lite` en su nivel gratuito, con salida estructurada, ejecución por lotes desde el proceso de GitHub Actions y clave fuera del repositorio. Se revisaron documentación oficial, licencia y mantenimiento del SDK `google-genai`, y dos proyectos comparables. La clasificación y el resumen usarán sólo títulos y metadatos permitidos; el saludo se compondrá en Django según usuario y hora local. Las imágenes rotarán diariamente desde un banco propio o fuente licenciada que aún debe investigarse; no se generarán. PROJECT registra el diseño. README, SOURCES y `.env.example` no requieren cambios en esta etapa de planificación porque no se modificaron funciones, feeds, políticas ni variables. La implementación y la comprobación con una clave gratuita real siguen pendientes.

Se amplió el experimento visual local por pedido del usuario: encabezado con la etiqueta «Tu edición personal» y luces azul/coral, entrada escalonada de columnas, elevación y acento coral al pasar el mouse, destello en botones y respuesta del marcador. Barra decorativa de avance mediante `animation-timeline: scroll(root)` sólo en navegadores compatibles. Animaciones de entrada finitas y efectos de hover limitados a puntero preciso; `prefers-reduced-motion` elimina animaciones, transiciones y desplazamientos de interacción. Sin JavaScript ni dependencias nuevas. Se conservan columnas, formularios, enlaces, colores y lógica. Se reinició el servidor local para actualizar las plantillas y se verificó el encabezado renderizado con sesión. Se inspeccionaron capturas del resultado y el ancho móvil de 375 px, sin desbordamiento en la página visible. `manage.py check` y `git diff --check` pasaron. La reducción de movimiento se revisó en CSS, sin emulación de la preferencia del sistema. README y PROJECT actualizados; SOURCES y `.env.example` no requieren cambios nuevos. No se publicó en Render.

Se pulió la interfaz con UI/UX Pro Max, ya instalada globalmente: superficies con sombras suaves, radios compartidos, filtros elevados, navegación activa, controles con profundidad, foco y titulares con jerarquía más clara. Se conservan azul/coral, fuentes locales, columnas, puntos de corte, HTML funcional y recorridos. Sólo cambian CSS y la versión de su enlace en la plantilla base. No se desplegó ni se modificó ingesta, clasificación o datos remotos.

Vista local iniciada en `http://127.0.0.1:8000/noticias/`, abierta con sesión de demostración y 24 titulares sintéticos. Script, entorno y SQLite temporales fuera del repositorio; se reutilizó `config.test_settings` con ajustes sólo en el proceso local. Esta vista es para diseño: la búsqueda con stemming requiere PostgreSQL y no se valida en SQLite. Suite existente: 52 pruebas, 40 aprobadas y 12 omitidas por requerir PostgreSQL; `git diff --check` pasó. Se inspeccionaron capturas de escritorio y móvil de 375 px; sin desbordamiento horizontal ni controles de formulario inferiores a 44 px. README y PROJECT actualizados. SOURCES no requiere nuevos cambios en este bloque y conserva el diagnóstico anterior; `.env.example` tampoco requiere cambios. No se agregaron dependencias de la aplicación ni skills dentro del repositorio.

Se diagnosticó ruido en IA causado por etiquetas secundarias de Cinco Días Mercados y EL PAÍS Economía. Se comprobó la página publicada con sesión iniciada y se reprodujo la clasificación con ambos RSS en memoria. Cinco Días: 25 entradas, 3 clasificadas en IA; EL PAÍS Economía: 39 entradas, 2 clasificadas en IA y 2 en tecnología. Una etiqueta aprobada no acredita que el tema sea central. El usuario descartó limitar canales completos porque también pueden publicar noticias pertinentes de IA. Se retiraron la restricción, la migración y las pruebas propuestas antes de incorporarlas; no se cambió código ni se tocó la base remota. La clasificación actual permanece vigente.

Se plantea evaluar título y etiquetas por noticia, con ejemplos pertinentes y financieros, midiendo falsos positivos y falsos negativos antes de decidir reglas. No se eligió un algoritmo ni se amplió alcance. SOURCES registra la evidencia agregada; PROJECT, README y `.env.example` no requieren cambios porque no se modificó arquitectura, decisiones de implementación, funciones, comandos ni variables.

El control de guardar/quitar de cada noticia ahora es un icono de marcador de 44 × 44 px, accesible con nombre para lectores de pantalla, con estado visual para noticias guardadas y ubicado junto a la fuente/fecha en la esquina inferior derecha. Se mantiene el POST, CSRF, retorno a la búsqueda y la misma acción en Mis guardadas.

Se agregó Buscar en títulos con `q` de hasta 200 caracteres, integrado a preferencias, fuente, idioma y paginación. Usa stop words y stemming de PostgreSQL para español, inglés y portugués según el idioma de cada noticia, con variantes regionales. Otros idiomas usan `simple`. Las consultas requieren todas las palabras significativas; si sólo hay stop words no muestran noticias. Con búsqueda, cada categoría ordena por relevancia, fecha e ID; sin búsqueda conserva el orden cronológico. Los botones Guardar y Quitar conservan también la búsqueda al regresar.

La migración `0009_article_article_title_search_gin` crea un índice funcional GIN que PostgreSQL mantiene para títulos existentes y cambios futuros, sin nuevas columnas ni servicios. Se verificó en una instancia PostgreSQL 17 temporal, independiente de las bases del usuario, con datos sintéticos externos al repositorio. No se agregaron dependencias ni comentarios al código nuevo. README y PROJECT incluyen uso, límites, comandos de prueba y decisión técnica investigada. SOURCES y `.env.example` no requieren cambios: no se modifican feeds, permisos ni variables.

## Noticias guardadas del bloque anterior

Se agregaron botones Guardar y Quitar de guardadas y la página privada Mis guardadas, con diez noticias por página, ordenadas por fecha de guardado. La migración `0008_savedarticle` incorpora la relación única usuario/noticia. Los formularios POST requieren sesión y CSRF, conservan filtros y página al regresar y rechazan redirecciones externas. Las noticias guardadas respetan los 14 días de conservación y se eliminan en cascada junto con la noticia; no se copian contenidos ni se extiende la retención.

Se agregaron avisos generales para filtros inválidos, filtros sin resultados y categorías sin noticias, conservando el mensaje para usuarios sin categorías y los avisos por sección. Mis guardadas vacía ofrece volver a Mis noticias. Se mantuvo el diseño existente y no se agregaron comentarios al código nuevo.

README y PROJECT actualizados. SOURCES y `.env.example` no requieren cambios: no se modificaron feeds, permisos de contenido ni variables de entorno. Sin nuevas dependencias ni servicios. El usuario informó que puede acceder al sitio de Render, pero no se verificó el despliegue remoto ni la ingesta desde esta tarea.

## Trabajo anterior

Se implementó la identidad editorial en inicio, ingreso, registro, preferencias y noticias: fuentes locales, azul intenso, marca tipográfica y controles compartidos. Inicio e ingreso/registro usan composiciones más expresivas; noticias conserva las categorías en columnas y agrega paginación independiente de diez artículos. Los filtros y las páginas restantes se conservan en los enlaces; aplicar o limpiar reinicia las páginas. Se mantuvieron textos de acciones y recorridos.

Se preservaron las correcciones del bloque anterior: pruebas reproducibles, `ArticleOrigin` y migración de noticias existentes, unión de categorías por origen y diez consultas RSS previstas por día. No se modificaron nuevamente la ingesta, los modelos ni su configuración.

La corrección de Gunicorn 26.2.0 ya está integrada en `main` mediante el commit `6a7b61d`; no queda pendiente integrarla. La autenticación actual de Django se conserva, sin cambios de registro, ingreso, sesiones, preferencias ni permisos.

## Próximo paso

Implementar el registro de cada ingesta y la presentación superior de sus titulares nuevos con saludo personalizado.

## Completado

- Clasificación adicional de titulares por Gemini, conservada por separado de las reglas, y preferencia individual entre IA, reglas o ambas.

- Búsqueda en títulos con índice GIN, stop words, stemming por idioma y ranking dentro de cada categoría.

- Guardar y quitar noticias por usuario, Mis guardadas paginada y mensajes generales para estados vacíos.

- Django, PostgreSQL local con Docker Compose y arquitectura anterior conservada como referencia histórica.
- Registro, ingreso, salida y preferencias individuales, sin cambios en este bloque.
- Ocho categorías y once feeds activos precargados mediante las seis migraciones anteriores, sin cambiar fuentes, permisos ni equivalencias.
- Ingesta RSS/Atom, deduplicación por GUID dentro del feed y URL canónica, y solicitudes condicionales.
- Orígenes por noticia y feed con categorías independientes, unión sin duplicados y conservación del feed original para atribución y filtros.
- `--refresh` reemplaza el aporte del origen consultado sin borrar las categorías aportadas por los demás.
- Migración `0007_article_origins`: conserva los metadatos existentes y copia feed, GUID y categorías al origen inicial.
- Página personalizada con noticias por categoría, filtros de fuente e idioma y conservación de 14 días.
- Paginación real con `page_<slug>`, diez noticias por sección, totales completos y navegación sin JavaScript; «Más reciente» sólo en la primera página.
- Rediseño de las cinco páginas, con fuentes Archivo y Source Sans 3 locales y licencias OFL, cuatro/dos/una columnas de noticias y formularios con campos y validaciones existentes.
- Foco visible, enlace para saltar al contenido, controles de al menos 44 px, movimiento reducido y errores y estados vacíos conservados.
- Workflow preparado todos los días a las 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00 y 00:00 en `America/Argentina/Buenos_Aires`; ejecución manual disponible fuera de la franja.
- Configuración de Render Free, Gunicorn, WhiteNoise y conexión prevista a Supabase Session pooler con SSL.
- README, PROJECT, SOURCES y STATUS sincronizados. La comprobación RSS del 13/10/2026 sólo conserva evidencia agregada, sin noticias ni XML en el repositorio.

## Pendiente y limitaciones

- Aplicar y verificar las migraciones recientes en PostgreSQL remoto; la búsqueda y la suite se comprobaron en PostgreSQL local, pero no se verificó la ingesta concurrente entre procesos ni el despliegue remoto.
- Verificar el build de Render, conexión a Supabase, aplicación publicada y persistencia; la configuración preparada no acredita un despliegue correcto.
- Configurar o comprobar credenciales en los paneles y `NEWS_INGESTION_ENABLED`, y verificar la primera ejecución manual y programada en Actions. Este bloque no carga secretos ni activa servicios remotos.
- Los horarios de Actions son previstos: puede haber retrasos u omisiones. La pausa de 00:00 a 06:00 y los feeds cortos pueden causar pérdidas de entradas; las consultas cada dos horas no garantizan captura exhaustiva.
- Sigue pendiente evaluar el ruido de Clarín Mundo y Economía y la cobertura de ciencia. No se incorporaron fuentes ni se cambiaron los criterios de clasificación en esta tarea.
- No se guardan artículos completos ni imágenes; los once feeds conservan los resúmenes deshabilitados.

## Bloqueos

No hay bloqueos conocidos para validar el despliegue. La comprobación remota requiere acceso a las cuentas y credenciales configuradas fuera del repositorio.

## Última verificación

- Cambio sólo de presentación y documentación de estado. README, PROJECT y SOURCES no requieren cambios; `.env.example` tampoco porque no se agregaron variables. `git diff --check` pasó. El detector Impeccable no encontró coincidencias, pero se ejecutó en modo degradado por faltar sus módulos HTML/CSS; no evaluó selectores ni contraste. La revisión visual en el navegador no fue posible porque el servidor local no respondió (`ERR_CONNECTION_REFUSED`).

- Suite completa en PostgreSQL 17: **52 pruebas aprobadas**, incluyendo búsqueda, stop words, stemming en tres idiomas, ranking y desempates, filtros, retención, paginación, guardados y migración reversible con noticias existentes.
- Suite SQLite: **40 pruebas aprobadas y 12 omitidas** por requerir PostgreSQL. Conserva las verificaciones generales y el formulario de búsqueda; no implementa búsqueda alternativa.
- `EXPLAIN` con 2001 noticias sintéticas comprobó el uso natural de `article_title_search_gin` en una búsqueda selectiva. La prueba de migración conserva todos los campos de la noticia y verifica la creación y eliminación del índice GIN.
- Microsoft Edge contra PostgreSQL local: búsqueda con stemming y stop words, Enter, resultados vacíos, limpieza, paginación y guardado/quita conservando `q` comprobados. Capturas revisadas a 375 y 1440 px, sin desbordamiento y con controles de al menos 44 px.
- `manage.py check`, `makemigrations --check --dry-run` con ajustes aislados y `git diff --check`: sin problemas.
- La migración de búsqueda todavía no se aplicó ni verificó en Supabase/Render desde esta tarea.

## Verificación de noticias guardadas

- Suite completa: **39 pruebas aprobadas**. Las ocho pruebas nuevas verifican sesión, POST, CSRF, aislamiento entre usuarios, guardados repetidos, redirecciones, conservación de URL, retención, paginación y mensajes vacíos.
- `manage.py check --settings=config.test_settings` y `git diff --check`: sin problemas.
- Microsoft Edge con datos sintéticos en SQLite fuera del repositorio: ingreso, guardar, quitar, Mis guardadas vacía, categorías vacías y regreso con filtros y página comprobados. Capturas de Mis guardadas revisadas a 375 y 1440 px, sin desbordamiento horizontal y con botones de al menos 44 px. Se reutilizaron las fuentes y estilos existentes.
- `makemigrations --check --dry-run --settings=config.test_settings`: sin cambios pendientes de modelo; migración nueva aplicada en las bases SQLite de prueba.
- La prueba histórica de migración restaura ahora el esquema más reciente al terminar, para no dejar la tabla nueva ausente en otras pruebas.
- La migración `0008_savedarticle` y las funciones nuevas todavía requieren aplicar y verificar en el despliegue remoto con PostgreSQL.

## Verificación del bloque anterior

- Suite completa: **31 pruebas aprobadas**, sin `.env`, Docker ni `collectstatic`; conserva las 24 anteriores y añade siete regresiones de paginación con escenarios de 0, 10, 11 y 23 artículos, independencia, enlaces, filtros, límites, orden y ausencia de duplicados.
- `manage.py check --settings=config.test_settings`: sin problemas.
- `makemigrations --check --dry-run --settings=config.test_settings`: sin cambios pendientes de modelo.
- `pip check`: sin dependencias incompatibles; no se agregaron ni actualizaron dependencias.
- Cron y zona horaria verificados: diez horarios diarios acordados, ejecución manual y control de activación conservados, limpieza antes de la ingesta.
- Navegador Microsoft Edge: las cinco páginas devolvieron HTTP 200 a 375, 768, 1024 y 1440 px; sin desbordamiento horizontal, campos sin etiqueta ni controles de formulario menores de 44 px. Se inspeccionaron capturas de escritorio y móvil, títulos extensos, errores de ingreso/registro/filtros y estados vacíos con datos sintéticos externos al repositorio.
- Recorridos comprobados en navegador: ingreso válido e inválido, `next`, registro válido e inválido, preferencias, confirmación de guardado y salida por POST; paginación con filtros, reinicio, recarga e historial. No cambió la autenticación.
- Texto inspeccionado con contraste mínimo de 5,94:1; foco visible, acceso al contenido por teclado y casillas operables con espacio. Movimiento reducido elimina transiciones. Fuentes locales cargadas y respaldo sin desbordamiento al bloquear su descarga.
- Reflujo equivalente al 200 % comprobado mediante viewport de 720 × 500 CSS px y escala de dispositivo 2, para las cinco páginas. Es emulación en Edge, no una prueba en dispositivos físicos ni una certificación de accesibilidad.
- `collectstatic` comprobado con el almacenamiento de manifiesto y compresión de WhiteNoise, usando un directorio temporal: CSS y ambas fuentes obtuvieron nombres versionados y archivos gzip, sin tocar configuración ni estáticos del repositorio.
- Configuración de producción y pruebas, URLs, formularios, modelos, ingesta, workflow y migración anterior conservados respecto del inicio de este bloque; el cambio funcional de backend se limita a `news_feed`. Se compararon los textos de enlaces y botones existentes sin faltantes.
- SOURCES y `.env.example` no requirieron cambios: no se modificaron feeds, permisos ni variables. README y PROJECT registran la identidad y el contrato de paginación; la arquitectura histórica permanece intacta.
- Diff revisado sin errores de espacios, secretos, noticias reales ni artefactos de ejecución incorporados; fuentes y licencias son assets deliberados del sitio.
- Las migraciones se probaron únicamente con bases SQLite de prueba. El despliegue y la activación remota están pendientes.
