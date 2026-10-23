# Definición del proyecto

## Objetivo

Construir una aplicación web universitaria que reúna noticias recientes de fuentes seleccionadas y diversas, las normalice y permita consultarlas por categorías, fuente e idioma. La aplicación atribuye cada contenido y dirige al usuario al artículo original.

El código debe ser sencillo de comprender y defender en un coloquio. El equipo desarrollará con Python y Django, con apoyo académico disponible para Python.

El proyecto debe poder desarrollarse y demostrarse sin servicios pagos. Antes de elegir un proveedor para publicar la aplicación, se comprobará que su plan gratuito permita conservar la base de datos y el uso previsto.

## Alcance

### Primera entrega

- Ingesta periódica de una selección pequeña de feeds RSS activos.
- Usuarios con registro e inicio de sesión mediante el sistema integrado de Django.
- Preferencias individuales de categorías asociadas a cada usuario.
- Modelo común para fuentes y noticias en PostgreSQL.
- Deduplicación exacta por GUID, URL canónica y respaldo mediante hash.
- Categorización básica en tecnología, inteligencia artificial, ciencia, economía, geopolítica, política argentina, Argentina y mercados y finanzas. Deportes queda fuera de esta entrega.
- Feed filtrable por categorías preferidas, fuente e idioma.
- Búsqueda en títulos con índice GIN, stop words, stemming por idioma y orden por relevancia.
- Guardar noticias por usuario y consultarlas o quitarlas desde Mis guardadas.
- Mostrar títulos, resúmenes y enlaces entregados por los feeds, respetando la política de cada fuente y con atribución visible.
- Presentar noticias de varias fuentes; la aplicación no afirma que una fuente o noticia sea infalible.
- Sin imágenes en la primera entrega.

### Entrega posterior

- Agrupamiento de artículos que cubren el mismo acontecimiento.
- Embeddings multilingües y `pgvector`, si la evaluación demuestra que mejoran el agrupamiento.
- Clustering dentro de una ventana temporal y validación de umbrales.
- GDELT DOC 2.0 como complemento para descubrir cobertura adicional.
- Evaluar categorías adicionales, incluidos deportes.

## Fuera de alcance inicial

- Almacenar o republicar artículos completos.
- Scraping de páginas sin autorización.
- Generar o reescribir titulares y resúmenes; se muestra lo que el feed proporciona cuando su uso está permitido.
- Traducción automática de contenido ajeno.
- Recomendaciones complejas, entrenamiento de modelos propios o clustering semántico en la primera entrega.
- Imágenes, miniaturas y almacenamiento de archivos.
- Servicios pagos o planes gratuitos que no permitan el uso previsto.

## Arquitectura acordada

```text
Feeds RSS configurados
        ↓
GitHub Actions ejecuta periódicamente un comando de Django
        ↓
Python obtiene, valida y normaliza los elementos
        ↓
Deduplicación y categorización básica
        ↓
PostgreSQL guarda fuentes y metadatos de noticias
        ↑
Django autentica usuarios, aplica sus preferencias y presenta el feed
        ↑
Navegador: plantillas HTML, CSS y JavaScript mínimo
```

La aplicación es un monolito Django renderizado en el servidor: páginas, formularios, sesiones, consultas y administración están en el mismo proyecto. `render.yaml` prepara el despliegue de Django en Render y su conexión a PostgreSQL administrado por Supabase; la publicación sigue pendiente de validación. La ingesta es un comando reutilizable, ejecutable manualmente y con diez consultas diarias previstas mediante GitHub Actions.

El workflow `.github/workflows/ingest-feeds.yml` está programado todos los días a las 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00 y 00:00 en `America/Argentina/Buenos_Aires`. Usa `cron: '0 0,6,8,10,12,14,16,18,20,22 * * *'` con `timezone` explícito. Medianoche cierra la jornada y la siguiente consulta es a las 06:00. La ejecución manual puede usarse fuera de esa franja. Comprueba migraciones, ejecuta `purge_old_articles` y después `ingest_feeds`, con PostgreSQL público compartido con la aplicación, SSL y credenciales en secretos de Actions. El job no se activó en esta tarea: requiere credenciales y `NEWS_INGESTION_ENABLED=true`; no usa una base efímera. Los horarios son previstos y GitHub puede retrasar u omitir ejecuciones bajo carga.

Las consultas cada dos horas reducen el riesgo de perder entradas durante el día, especialmente en feeds de diez elementos. La pausa de seis horas durante la noche puede perder publicaciones que ya no estén en el RSS al reanudar; no se promete captura exhaustiva. La evidencia agregada del 13/10/2026 está en `SOURCES.md` y mide publicaciones observadas, no el horario real de actualización del servidor RSS.

El registro y el inicio de sesión usan la autenticación integrada de Django. No se incorporará un proveedor externo de autenticación ni una API independiente en la primera entrega. Las noticias y fuentes serán datos compartidos; cada usuario podrá gestionar únicamente sus propias preferencias y noticias guardadas.

Para una primera publicación se eligieron Render Free para Django y Supabase Free para PostgreSQL. La aplicación se despliega desde `main`; los secretos se configuran en el panel, nunca en Git. Se utilizará el pooler compartido de Supabase en modo Session por el acceso IPv4, con SSL obligatorio. En desarrollo se mantiene PostgreSQL 17 en Docker Compose, con volumen persistente y acceso por `127.0.0.1:5433`.

GDELT seguirá el mismo modelo normalizado cuando se incorpore, pero no será la fuente principal. La aplicación debe continuar funcionando si GDELT no responde o limita consultas.

## Tecnologías

| Área | Decisión | Motivo |
|---|---|---|
| Lenguaje | Python | Un lenguaje para la web y la ingesta, con acompañamiento académico disponible |
| Aplicación web | Django | Incluye autenticación, sesiones, formularios, modelos, administración y plantillas del servidor |
| Interfaz | Plantillas Django, HTML, CSS y JavaScript mínimo | Evita mantener una aplicación frontend separada para las funciones iniciales |
| Base de datos | PostgreSQL | Base relacional para usuarios, preferencias, fuentes y noticias |
| Ingesta | Comando de administración Django | Comparte configuración y modelos de la aplicación; fácil de ejecutar y explicar |
| Automatización | GitHub Actions | Diez consultas previstas por día dentro de la franja acordada, sin servidor de tareas |
| Alojamiento web | Render Free | Despliega el monolito Django desde `main`; duerme tras 15 minutos sin tráfico y tiene filesystem efímero |
| PostgreSQL alojado | Supabase Free | Base persistente compartida por Render y GitHub Actions; límite inicial de 500 MB |
| Servidor WSGI | Gunicorn | Ejecuta Django en producción con el servidor WSGI convencional |
| Archivos estáticos | WhiteNoise | Sirve CSS y otros archivos de la aplicación sin agregar un servicio de almacenamiento |

Las nuevas dependencias y los servicios de alojamiento se revisaron con documentación oficial y proyectos comparables; la decisión está registrada más abajo.

### Esquema inicial implementado

- `Category`: nombre y slug únicos para clasificar noticias y preferencias.
- `Source`: medio u organización de origen; puede tener varios feeds.
- `Feed`: URL única, idioma, categorías, estado de activación, permiso de mostrar el resumen RSS, permiso independiente para la presentación LLM y encabezados `ETag`/`Last-Modified`. Ambos permisos de resumen empiezan desactivados.
- `Article`: enlace original, URL canónica opcional, GUID, huella para deduplicación, título, resumen permitido, idioma, fechas, feed y categorías. Hay restricciones de unicidad para enlace original, URL canónica no vacía y GUID no vacío dentro del feed. La huella tiene índice y se calcula durante la ingesta.
- `ArticleOrigin`: noticia, feed, GUID opcional y categorías aportadas por ese feed. Un par noticia/feed único y un GUID no vacío único dentro de su feed. Se elimina junto con la noticia.
- `UserPreference`: relación uno a uno con el usuario integrado de Django y sus categorías preferidas.
- `SavedArticle`: usuario, noticia y fecha de guardado; el par usuario/noticia es único. Se elimina junto con el usuario o la noticia mediante cascada. La migración `0008_savedarticle` crea esta tabla sin modificar noticias existentes.
- `NewsBriefing` y `NewsBriefingItem`: presentación común de una ventana móvil de 24 horas y sus puntos con enlaces a las noticias que los respaldan. Se conservan hasta 14 días.

Guardar y quitar usan formularios POST con CSRF y requieren sesión. Cada usuario consulta y modifica sólo sus guardadas. Se pueden guardar noticias recientes de feeds activos; Mis guardadas conserva las ya guardadas aunque cambien las preferencias o se desactive el feed. La lista se ordena por fecha de guardado, de diez en diez, y oculta noticias de más de 14 días desde la publicación; la limpieza elimina también sus guardados. Guardar no crea una copia del artículo ni extiende su conservación. Los botones conservan la URL de regreso con filtros y página, y rechazan destinos externos. La interfaz distingue ausencia de categorías, filtros inválidos, filtros sin resultados y categorías sin noticias disponibles. Se reutilizan modelos, vistas y plantillas de Django, sin nuevas dependencias ni servicios.

La migración inicial está en `news/migrations/0001_initial.py`. Una segunda migración incorpora cinco categorías. La tercera agrega los encabezados HTTP para consultas condicionales y la cuarta carga los feeds de Clarín Tecnología, EL PAÍS Tecnología y MIT News sobre IA. La quinta agrega `politica-argentina` y cinco feeds de Clarín y EL PAÍS para política argentina, economía y geopolítica. La sexta incorpora `argentina` y `mercados-finanzas`, agrega los feeds de Los Andes Política y Economía y Cinco Días Mercados, y vincula Clarín Política con Argentina. La séptima migración añade `ArticleOrigin` y copia el feed, GUID y categorías de cada noticia existente a su origen inicial, sin modificar metadatos ni atribución. La activación se controla desde la administración. No se guardan artículos completos ni imágenes.

La ingesta es un comando de Django (`python manage.py ingest_feeds`) que consulta únicamente feeds activos. Descarga hasta 2 MB por feed con un tiempo de espera de 15 segundos, interpreta RSS/Atom, exige título, URL HTTP(S) y fecha de publicación y conserva idioma. Clasifica cada noticia con las etiquetas de su entrada RSS que coinciden con la lista revisada de `news/category_aliases.py`. Normaliza tildes, mayúsculas y espacios, pero exige coincidencia exacta del nombre; no infiere temas por palabras del titular. Cuando la entrada no incluye etiquetas, usa las categorías configuradas en su feed como respaldo. Si incluye etiquetas pero ninguna está aprobada, deja la noticia sin categoría. Esto permite usar feeds generales con el respaldo vacío y excluir etiquetas no revisadas. Omite noticias publicadas hace más de 14 días. Sólo guarda un resumen cuando `show_summary` está habilitado y el texto limpio tiene hasta 600 caracteres; en los once feeds activos ese permiso está desactivado. El comando acepta `--refresh` para volver a descargar y reclasificar artículos ya guardados, aunque el servidor haya indicado que el feed no cambió. Cada consulta reemplaza las categorías del origen procesado y recalcula la unión de los orígenes de la noticia, sin duplicados ni categoría principal. Retirar una equivalencia de un feed no elimina aportes de los otros. No modifica las categorías de un origen que no fue descargado.

La ampliación del 11/10/2026 incorpora feeds de sección de Clarín y EL PAÍS. Los de Clarín no proporcionan etiquetas por entrada y usan la categoría editorial del feed como respaldo; esto puede dejar pasar contenido fuera del tema estricto, especialmente en Mundo y Economía. Los de EL PAÍS sí aportan etiquetas y sólo entran a las nuevas categorías cuando alguna coincide con la lista aprobada. `politica-argentina` no acepta el alias genérico `Política` de cualquier fuente. Esta selección prioriza condiciones RSS claras; `SOURCES.md` documenta las otras fuentes revisadas y sus restricciones. No se incorporaron dependencias ni servicios nuevos.

La categoría `argentina` reúne, por decisión del usuario, política nacional y economía argentina. Incluye Clarín Política y los feeds de Política y Economía de Los Andes; no incluye Clarín Economía porque el canal observado mezcla cotizaciones de divisas de otros países. Los Andes etiqueta cada entrada con el nombre genérico de su sección. `news/category_aliases.py` aplica estas dos equivalencias sólo a las URL de esos feeds, de modo que `Política` de otro medio no se convierta en política argentina. `mercados-finanzas` reúne el feed Mercados de Cinco Días y las entradas de otros feeds con etiquetas financieras aprobadas, como `Bolsa` o `Finanzas`. Una noticia puede figurar en más de una categoría. No se interpretan los titulares para decidir su tema, ni se muestran precios bursátiles en tiempo real. Los tres feeds nuevos ofrecen RSS públicos para lectores y sitios web; `SOURCES.md` registra los enlaces y las condiciones. La solución conserva la lista local y la lectura de `entries[i].tags` ya documentada, sin dependencia ni servicio nuevo.

Para evitar duplicados exactos, busca primero el GUID del origen dentro del feed, conservando el respaldo del GUID original de la noticia, y luego la URL original y una URL normalizada. La normalización elimina fragmentos y parámetros de seguimiento conocidos, pero conserva intacto el enlace que recibirá el usuario. Una huella SHA-256 de esa URL sirve de respaldo para registros antiguos sin URL normalizada; no agrupa artículos diferentes sobre un mismo hecho. Las restricciones de unicidad en PostgreSQL refuerzan este control. Los encabezados `ETag` y `Last-Modified` permiten responder a HTTP 304 sin volver a procesar un feed sin cambios.

Cuando una URL canónica ya existe, se conserva la noticia original y se registra el aporte del otro feed. El feed original, su enlace, título y fechas mantienen la atribución y los filtros existentes. Cada origen conserva el último GUID conocido; una respuesta sin GUID no lo borra. La actualización del origen y la unión de categorías son atómicas y bloquean la noticia existente con `select_for_update`; el bloqueo efectivo requiere PostgreSQL y queda pendiente de comprobar allí. Las noticias creadas desde la administración sin origen reciben uno inicial al volver a procesarse para preservar sus categorías previas.

La solución por origen permite retirar clasificaciones con `--refresh`; acumular categorías directamente en la noticia no permite distinguir cuál debe retirarse. Se reutiliza la separación entre feed y entrada estudiada en django-planet y django-feed-reader, citados abajo, y se adapta al defecto reproducido de categorías entre feeds. Se revisaron las referencias oficiales de Django sobre [migraciones de datos](https://docs.djangoproject.com/en/5.2/topics/migrations/#data-migrations), [restricciones de unicidad](https://docs.djangoproject.com/en/5.2/ref/models/constraints/#uniqueconstraint) y [transacciones](https://docs.djangoproject.com/en/5.2/topics/db/transactions/). No se incorpora dependencia ni servicio nuevo.

El registro usa `UserCreationForm`, el ingreso y la salida usan las vistas incluidas en Django y la página de preferencias usa un `ModelForm`. Cada usuario sólo modifica el registro `UserPreference` asociado a su cuenta. El cierre de sesión se envía por POST con protección CSRF. Esta implementación sigue la [documentación oficial de autenticación de Django](https://docs.djangoproject.com/en/5.2/topics/auth/default/) y no añade servicios ni dependencias.

La página `/noticias/` requiere inicio de sesión y consulta las categorías de `UserPreference` del usuario actual. Ordena las columnas por el total de artículos recientes de feeds activos que coinciden con los filtros, de mayor a menor; en empate conserva el orden alfabético. Cada sección pagina de diez en diez mediante `Paginator` de Django y ordena por fecha e ID descendentes cuando no hay búsqueda; al buscar ordena primero por relevancia. El encabezado conserva el total filtrado, no el tamaño de la página. Cada titular enlaza directamente al medio y muestra fuente, fecha e idioma; sólo muestra un resumen si se guardó conforme a la política del feed. «Más reciente» o «Más relevante», según corresponda, se reserva para la primera noticia de la primera página. No se agrupan coberturas. Los estados vacíos conservan sus accesos a preferencias o limpieza de filtros. El acceso inicial de una cuenta autenticada y el destino tras ingresar conducen a esta página.

El pulido visual local del 13/10/2026 conserva la estructura editorial y los colores: sombras suaves en columnas y filtros, radios de 14 px para superficies y 8 px para controles, navegación activa y mejor jerarquía de titulares. Se reutiliza UI/UX Pro Max ya instalada fuera del repositorio, con licencia MIT según su [repositorio oficial](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill); se comparó su orientación a sistemas visuales con [Impeccable](https://github.com/pbakaus/impeccable), centrado en crítica y refinamiento. La elección aprovecha la guía local de accesibilidad y espaciado; sus sugerencias de nuevas paletas, fuentes y landing pages no reemplazan la identidad ni la estructura acordadas. No se instalaron bibliotecas, servicios ni skills en el proyecto. La demostración local usa una base SQLite temporal con contenido sintético externo al repositorio y no modifica PostgreSQL remoto; no sustituye la validación de búsqueda en PostgreSQL. La publicación queda pendiente de revisión del usuario. El experimento se amplía con motion CSS: entradas finitas escalonadas, hover para mouse, acento coral, microinteracciones y progreso decorativo de lectura mediante scroll timeline con detección de soporte. Todo el contenido permanece disponible sin JavaScript y `prefers-reduced-motion` elimina las animaciones y los desplazamientos interactivos. No cambia la arquitectura ni requiere bibliotecas de animación.

### Búsqueda en títulos

El parámetro `q` admite hasta 200 caracteres y se combina con las categorías elegidas, fuente e idioma antes de paginar. `SearchQuery` usa texto simple y exige todas las palabras significativas; no interpreta operadores ingresados por el usuario. Una búsqueda vacía conserva el orden cronológico. Una consulta formada sólo por stop words no devuelve todas las noticias: queda sin coincidencias.

`news/search.py` selecciona las configuraciones nativas `spanish`, `english` y `portuguese` según `Article.language`, incluyendo códigos regionales con guion o guion bajo y sin distinguir mayúsculas. Aplican sus stop words y stemming a título y consulta. Los códigos desconocidos o vacíos usan `simple`, sin stemming ni stop words propias de un idioma. No se buscan resúmenes ni artículos completos. El stemming no reconoce todas las variantes: PostgreSQL español distingue «robot» de «robots»; tampoco se agregan sinónimos, corrección ortográfica ni traducción.

La migración `0009_article_article_title_search_gin` crea un índice funcional GIN sobre el vector del título, con la misma expresión por idioma que usa la consulta. No agrega columnas ni necesita reindexación manual después de la ingesta: PostgreSQL mantiene el índice cuando cambian título o idioma. Las consultas usan valores parametrizados. `SearchRank` con `cover_density=True` valora proximidad y frecuencia; `normalization=2` divide por longitud del documento. Se ordena por relevancia, fecha de publicación e ID descendentes dentro de cada categoría. La puntuación no representa calidad ni veracidad editorial.

Se revisaron la [búsqueda de Django 5.2](https://docs.djangoproject.com/en/5.2/ref/contrib/postgres/search/), los [índices de PostgreSQL 17](https://www.postgresql.org/docs/17/textsearch-tables.html) y sus [diccionarios](https://www.postgresql.org/docs/17/textsearch-dictionaries.html). Como proyecto comparable se examinó [Wagtail](https://docs.wagtail.org/en/stable/topics/search/backends.html) y su backend actual en [django-modelsearch](https://github.com/wagtail/django-modelsearch/blob/main/modelsearch/backends/database/postgres/postgres.py), que usa las mismas expresiones para indexación y ranking. Wagtail y django-modelsearch tienen mantenimiento activo y licencia BSD de tres cláusulas; [Django](https://github.com/django/django/blob/main/LICENSE) también usa BSD, y [PostgreSQL](https://www.postgresql.org/about/licence/) una licencia permisiva. No se instala ni se copia código de esos proyectos: se reutilizan Django y PostgreSQL existentes, evitando un motor externo. Se consultó la incidencia [Wagtail #14625](https://github.com/wagtail/wagtail/issues/14625), sin confirmar, sobre números con signo: no se promete búsqueda literal de puntuación ni de todos los números. GIN acelera coincidencias, pero no el cálculo del ranking; el planificador puede preferir otro plan con pocos registros. Se comprobó su uso natural mediante `EXPLAIN` en una consulta selectiva sobre 2001 noticias sintéticas.

La migración crea y elimina el índice sólo en PostgreSQL, conservando el estado del modelo en SQLite para las pruebas generales. La búsqueda no tiene una implementación alternativa en SQLite: informa que no está disponible en ese entorno. `config.postgres_test_settings` reutiliza los ajustes aislados de prueba con la conexión PostgreSQL habitual y permite verificar stop words, stemming, ranking, índice y migración en una base de prueba separada.

La paginación añade un parámetro GET `page_<slug>` por categoría, sin cambiar rutas ni crear una API. Cada enlace modifica sólo su página y conserva fuente, idioma y páginas restantes; utiliza el fragmento `#category-<slug>` para volver al encabezado. Los números ausentes, no enteros o menores que uno se normalizan a la primera página; los superiores al máximo usan la última. Los formularios GET de filtros no transportan páginas, por lo que aplicar o limpiar reinicia todas las secciones. Se conserva `section.articles` como lista y se añaden el objeto de página y enlaces al contexto. La solución utiliza el [paginador integrado de Django 5.2](https://docs.djangoproject.com/en/5.2/ref/paginator/), sin dependencias ni migraciones adicionales.

### Identidad visual implementada el 13/10/2026

Se eligió una dirección editorial contemporánea: fondo blanco azulado `#F5F7FC`, superficies blancas, texto `#182033`, azul `#2448D8` y coral `#F26A55` para detalles gráficos. La expresión se concentra en marca y encabezados; los listados mantienen una lectura tranquila, con separadores en lugar de cajas por artículo. Las noticias conservan hasta cuatro columnas desde 1280 px, dos desde 768 px y una en móvil, con ancho máximo de 1680 px. Inicio tiene una composición asimétrica; ingreso y registro separan un panel azul de marca y el formulario desde 1024 px, convirtiendo la marca en cabecera compacta en móvil. Las preferencias presentan opciones nativas en dos columnas desde 768 px.

Las fuentes variables normales [Archivo](https://github.com/google/fonts/tree/main/ofl/archivo) y [Source Sans 3](https://github.com/google/fonts/tree/main/ofl/sourcesans3) se descargaron del catálogo oficial de Google Fonts y se alojan localmente con sus licencias SIL OFL. Archivo aporta marca y encabezados; Source Sans 3, lectura y controles. Se usa `font-display: swap`, alternativas del sistema y precarga local. No se importa CSS remoto ni se agrega una dependencia de frontend. WhiteNoise conserva su compilación habitual de estáticos con manifiesto y compresión.

La implementación aplica frontend-design e Impeccable para composición, Emil Design Engineering para interacciones breves y [Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines) para semántica, foco y adaptación. Como referencia de interacción se revisó la [documentación de vistas de Feedly](https://docs.feedly.com/article/276-how-do-i-change-the-views-of-my-feeds-and-source): se adapta el principio de densidad de lectura, sin copiar código, añadir modos ni adoptar su interfaz. La selección previa de skills y dirección se reutilizó; no se cambió el stack. Se conservaron textos, campos, ayudas, errores, protección CSRF y recorridos; sólo la paginación cambia el comportamiento de la vista de noticias. La administración de Django queda fuera del rediseño.

### Revisión de las herramientas incorporadas

Para concretar GitHub Actions, ya elegido, se revisaron su [documentación de horarios](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule), [secretos](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets) y [concurrencia](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency), y las acciones oficiales [checkout](https://github.com/actions/checkout) y [setup-python](https://github.com/actions/setup-python), ambas MIT. Se mantienen las etiquetas v7 de ambas acciones; mantienen actualizaciones, aunque checkout limita contribuciones y prioriza seguridad y fallos importantes. Estas versiones requieren un runner actualizado, proporcionado por `ubuntu-latest`. Los horarios usan la rama predeterminada, pueden retrasarse y desactivarse tras 60 días sin actividad en repositorios públicos. Se conserva el disparo manual y se documenta la activación. No se incorpora una dependencia de aplicación ni otro servicio de tareas. La conexión pública usa `POSTGRES_SSLMODE`, según la [documentación de libpq](https://www.postgresql.org/docs/17/libpq-ssl.html).

Para desplegar Django se revisaron la [guía oficial de Render](https://render.com/docs/deploy-django), la [referencia de Blueprints](https://render.com/docs/blueprint-spec), la configuración de [versiones de Python](https://render.com/docs/python-version) y las [limitaciones Free](https://render.com/docs/free). El servicio se define en `render.yaml`, usa Python 3.13, región Virginia, rama `main`, plan `free`, `migrate`, `collectstatic` y Gunicorn. El plan duerme tras 15 minutos sin tráfico, tarda cerca de un minuto en despertar, comparte un cupo de 750 horas mensuales y su filesystem es efímero; por eso sólo PostgreSQL conserva datos. Render indica que Free sirve para pruebas y proyectos personales, no producción con requisitos de disponibilidad.

Supabase Free se utilizará sólo como PostgreSQL. Su cuota vigente es 500 MB por proyecto y los proyectos con baja actividad pueden pausarse tras siete días; la ingesta y el uso normal ayudarán a mantener actividad, pero hay que verificarlo en el panel. La base se creará en East US (North Virginia), cercana a la región Virginia de Render. Render y Actions usarán el pooler compartido de Supabase en modo Session (puerto 5432), recomendado para conexiones persistentes desde redes IPv4, con `POSTGRES_SSLMODE=require`. Se debe crear el proyecto antes de aplicar el Blueprint, cargar las credenciales sin versionarlas y no crear un PostgreSQL adicional de Render. La [lista de regiones de Supabase](https://supabase.com/docs/guides/platform/regions) explica las ubicaciones disponibles.

Para ejecutar Django en Render se agregaron [Gunicorn](https://gunicorn.org/) y [WhiteNoise](https://whitenoise.readthedocs.io/en/latest/). Gunicorn es un servidor WSGI de producción, con licencia MIT y releases activos; se fija la versión [26.2.0 publicada en PyPI](https://pypi.org/project/gunicorn/26.2.0/). Es compatible con servidores POSIX, no con Windows, así que `requirements.txt` lo omite en las máquinas Windows del grupo y lo instala en Render. WhiteNoise, también MIT, tiene versión 6.12.0, soporte documentado para Django 5.2 y sirve archivos estáticos comprimidos dentro del propio servicio; no sirve archivos subidos por usuarios, que el alcance actual no contempla. El backend de manifiesto requiere que el build ejecute `collectstatic`. La guía de Render recomienda esta integración para proyectos Django pequeños. Como referencias comparables se revisaron el [ejemplo oficial de Django de Render](https://github.com/render-examples/django) (MIT) y [Cookiecutter Django](https://github.com/cookiecutter/cookiecutter-django) (MIT, repositorio activo, despliegue de producción configurable con WhiteNoise). Sus licencias permiten el uso previsto y sus mantenedores publican cambios. Se mantiene el modelo WSGI síncrono, suficiente para la aplicación actual. Los límites relevantes son el sueño y el filesystem efímero de Render Free, la pausa por inactividad de Supabase Free y las cuotas compartidas; no se destina este despliegue a disponibilidad de producción.

La página personalizada combina fuente e idioma mediante un formulario GET validado (`NewsFilterForm`), con selección en la URL. Las opciones se obtienen de artículos recientes de feeds activos asociados a las categorías del usuario antes de aplicar los filtros. Se filtra antes de paginar de diez en diez por categoría. Un valor inválido produce un error visible y ningún resultado. No se modifican preferencias ni esquema; la consulta excluye noticias antiguas aunque la limpieza todavía no corra.

Se eligió [Django 5.2 LTS](https://docs.djangoproject.com/en/5.2/releases/5.2/) porque soporta Python 3.13, trae autenticación y administración, y usa licencia BSD. Su [soporte de PostgreSQL](https://docs.djangoproject.com/en/5.2/ref/databases/) recomienda psycopg 3. Se fijaron versiones en `requirements.txt` para reproducir el entorno local.

[psycopg 3](https://www.psycopg.org/psycopg3/docs/basic/install.html) conecta Django con PostgreSQL y mantiene licencia LGPL 3. Su repositorio [tiene actividad](https://github.com/psycopg/psycopg); se revisó un [fallo reportado en Windows para una versión anterior](https://github.com/psycopg/psycopg/issues/1088), por lo que se instaló y comprobó la versión fijada en el entorno local. [python-dotenv](https://github.com/theskumar/python-dotenv), con licencia BSD 3 y mantenimiento activo, permite leer el archivo local `.env`. Como puede [no avisar cuando falta ese archivo](https://github.com/theskumar/python-dotenv/issues/631), Django exige explícitamente `DJANGO_SECRET_KEY` al iniciar.

La imagen oficial [PostgreSQL 17](https://hub.docker.com/_/postgres) se usa sólo para desarrollo; el volumen de [Docker Compose](https://docs.docker.com/reference/compose-file/volumes/) conserva los datos locales. PostgreSQL tiene [licencia permisiva](https://www.postgresql.org/about/licence/) y [Docker Desktop permite uso educativo gratuito](https://docs.docker.com/subscription-billing/desktop-license/). La contraseña se pasa desde `.env`, que Git ignora. Para la publicación, la base de Supabase sustituye a la base Render Free: esta última expira a los 30 días y duplicaría servicios.

Como referencia de proyectos comparables activos se revisaron [django-planet](https://github.com/matagus/django-planet) y [django-feed-reader](https://github.com/xurble/django-feed-reader), que usan modelos y comandos de Django para agregación de feeds. Esta base sigue ese patrón sencillo, sin introducir una cola de tareas ni otro servicio de aplicación.

Para leer RSS se incorporó [feedparser 6.0.14](https://feedparser.readthedocs.io/en/stable/), compatible con Python 3.13, con [licencia BSD-2-Clause](https://github.com/kurtmckee/feedparser/blob/main/pyproject.toml) y una [versión publicada en julio de 2026](https://feedparser.readthedocs.io/en/latest/changelog/). Permite tratar de forma uniforme RSS y Atom. Su historial registra fallos de análisis corregidos en versiones recientes; además, un XML mal formado puede producir `bozo=1`, por lo que el comando rechaza ese resultado. La descarga se hace con la biblioteca estándar de Python para controlar tamaño, tiempo de espera y solicitudes condicionales. Se mantuvieron como referencias comparables django-planet y django-feed-reader; no se agregó un framework de tareas.

Para la categorización se revisó la [referencia oficial de `entries[i].tags`](https://feedparser.readthedocs.io/en/stable/reference-entry-tags.html): tanto RSS como Atom exponen el nombre de categoría en `term`, y un elemento puede traer varias etiquetas. Se comparó con los lectores activos [django-planet](https://github.com/matagus/django-planet) y [django-feed-reader](https://github.com/xurble/django-feed-reader), que separan lectura de feeds y almacenamiento de entradas. La solución conserva esa separación y agrega un diccionario local de equivalencias exactas, fácil de inspeccionar y modificar, sin dependencia ni servicio nuevos. Su límite deliberado es que una etiqueta desconocida no clasifica el artículo hasta que el equipo la revise y la incorpore; se evita así asignar temas por coincidencias parciales o por nombres de personas y empresas que los feeds también publican como etiquetas.

## Clasificación LLM y presentación de actualidad (entrega 3)

La clasificación por etiquetas y categorías de respaldo sigue vigente. Se agregó una clasificación LLM separada por noticia para cumplir el requisito original y poder comparar ambos resultados. El modelo es [`gemini-3.1-flash-lite`](https://ai.google.dev/gemini-api/docs/models): ofrece entrada y salida de texto gratuitas dentro de las cuotas del proyecto según la [tabla de precios](https://ai.google.dev/gemini-api/docs/pricing). Las cuotas efectivas se consultan en AI Studio y la facturación no se habilitará. El nivel gratuito [puede usar solicitudes y respuestas para mejorar los productos de Google](https://ai.google.dev/gemini-api/terms); por eso sólo se envían títulos, fuente, idioma, fecha e identificador interno temporal, sin texto completo, resumen RSS, etiquetas no persistidas, datos de usuario ni secretos. La clasificación usa salida JSON estructurada, limita las categorías a ocho slugs y valida de nuevo en Python.

La integración propuesta usa el [SDK oficial `google-genai`](https://github.com/googleapis/python-genai), que tiene licencia Apache-2.0, admite Python 3.13 y mantiene versiones recientes; se fijará una versión al implementarlo. Su API puede cambiar entre versiones mayores, por lo que se mantendrá una interfaz propia pequeña y una versión fijada. Como referencias comparables se revisaron [rss-digest](https://github.com/bkubinszky/rss-digest), activo y con licencia MIT, que procesa RSS con Gemini desde GitHub Actions, guarda la clave en secretos y limita las llamadas por lotes, y [news-intelligence-agent](https://github.com/jiamucheng6-rgb/news-intelligence-agent), que combina reglas, clasificación LLM y resúmenes estructurados pero se declara prototipo sin persistencia, caché ni gestión de reintentos. Se adoptan los patrones de ejecución por lotes y persistencia propia; no se copian sus componentes ni se agregan frameworks de agentes.

Diseño previsto:

1. La ingesta RSS persiste sus metadatos y reglas como hoy. Una etapa posterior procesa noticias recientes aún no clasificadas por LLM, incluidas las anteriores que siguen dentro de los 14 días. Guarda las categorías LLM y el modelo utilizado por separado de las categorías por origen. La consulta de noticias considera la unión de ambos conjuntos sin sobrescribir el aporte de cada feed.
2. Cada solicitud clasifica un lote acotado de titulares. El esquema obliga a devolver el ID recibido y una lista de slugs permitidos; la aplicación comprueba IDs, duplicados y slugs antes de guardar. Un resultado vacío es válido. Un error de cuota o red deja noticias pendientes para la siguiente ejecución, sin detener la ingesta por reglas. Las entradas RSS se tratan como datos, no como instrucciones.
3. Después de una ingesta, `generate_news_briefing` consulta artículos de feeds activos que tienen activado `allow_ai_briefing` y `published_at` dentro de las 24 horas anteriores a su ejecución. Envía título, medio, fecha e idioma a Gemini; no incluye cuerpo ni resumen RSS. El modelo agrupa coberturas del mismo suceso y evalúa impacto, urgencia, novedad y alcance público en escala 1–5. La cobertura por varios medios independientes sólo sirve como corroboración secundaria. La aplicación conserva como máximo tres sucesos que superen el umbral de 4, en orden de importancia; si ninguno lo supera, no rellena el panel. Cada punto referencia noticias del lote para mantener enlaces y atribución. La aplicación valida que el modelo no invente IDs y sólo guarda una respuesta completa. El permiso empieza desactivado porque mostrar titulares en un agregador no acredita que se autorice una síntesis derivada por IA; las condiciones por fuente deben revisarse antes de activar el campo desde `/admin/`. El resumen es común, se actualiza una vez por ejecución, conserva una ventana/fecha visible y los registros duran hasta 14 días. Si no hay titulares autorizados, se guarda el estado vacío sin llamar a Gemini; ante error o cuota se mantiene la última presentación válida sólo mientras sus fuentes sigan habilitadas y todas las noticias citadas estén dentro de las últimas 24 horas. La portada arma el saludo según la hora de Buenos Aires. Abrir la página no llama al modelo.
4. La clave queda únicamente en un secreto de GitHub Actions o en el entorno local. Se limitarán longitud, cantidad de noticias por lote y solicitudes por ejecución. Antes de habilitar el flujo remoto se revisarán manualmente ejemplos de las ocho categorías, incluidos los falsos positivos financieros observados en IA.

Las imágenes por categoría de la entrega 3 se tomarán de un banco propio o de una fuente externa con licencia y atribución verificadas. Se buscará una forma de rotarlas una vez al día sin generación de imágenes. La elección del banco y su política de almacenamiento quedan pendientes de investigación. El agrupamiento general de noticias para ocultar duplicados, la ordenación por importancia del feed y la vista de categoría ampliada se abordarán después; la selección de hasta tres sucesos del resumen no cambia el feed ni sus columnas.

Implementado el 23/10/2026 para la clasificación: `Article` guarda `llm_categories`, fecha y modelo sin alterar las categorías por origen. `UserPreference.classification_mode` permite que cada persona consulte reglas, IA o la unión; el valor inicial es la unión. `classify_news_ai` procesa como máximo cien noticias recientes pendientes en lotes de diez, priorizando `published_at` descendente para que el modo «Sólo IA» incorpore primero las últimas noticias; valida el lote completo y conserva las noticias sin clasificar ante fallos. El workflow lo ejecuta después de la ingesta sólo si el usuario configuró `GEMINI_API_KEY` como secreto. Se usa `google-genai==2.33.0` (Apache-2.0); una actualización mayor requiere revisar el cliente y el formato de respuesta. La presentación LLM se describe a continuación.

La presentación LLM usa el mismo modelo `gemini-3.1-flash-lite` y el SDK `google-genai==2.33.0`. `.github/workflows/ingest-feeds.yml` llama a `generate_news_briefing` después de una ingesta exitosa cuando existe `GEMINI_API_KEY`; la API sólo se ejecuta desde Actions y no al entrar a la página. `NewsBriefing` conserva la hora de generación y el inicio de la ventana móvil; sus puntos guardan texto y relaciones a noticias válidas en esa ventana. El comando admite hasta 250 titulares por llamada, agrupa coberturas del mismo hecho y muestra como máximo tres sucesos con importancia alta (4 o 5 sobre 5), usando impacto, urgencia, novedad y alcance. La repercusión en varios medios sirve como corroboración, no como único criterio. La aplicación valida todos los IDs y conserva sólo puntos que superan el umbral. Los feeds no entran en la síntesis hasta que `allow_ai_briefing` se active tras revisar su permiso. Si no hay sucesos destacados, no rellena el panel; si se supera el límite o falla la API, conserva la última presentación válida, siempre que sus fuentes sigan dentro de la ventana. No hubo llamada a Gemini durante el desarrollo. La cuota gratuita efectiva depende del proyecto y puede agotarse; sin facturación activada, la app muestra la última respuesta válida y deja registro en el log de Actions.

## Datos y conservación

Se guardarán únicamente metadatos necesarios:

- usuario y sus preferencias de categorías;
- fuente y feed de origen;
- GUID externo y URL canónica;
- título y resumen permitido;
- puntos de la presentación LLM, fecha de generación y asociaciones a titulares fuente;
- fecha de publicación y fecha de captura;
- idioma y categorías;
- metadatos técnicos mínimos para diagnóstico.

Política inicial:

- Noticias normalizadas: 14 días.
- No almacenar artículos completos ni imágenes.
- PostgreSQL almacena metadatos y enlaces, no contenido editorial completo.

Las políticas de resumen se definen por fuente. La existencia de un RSS no implica permiso para reutilizar todos sus campos.

La ventana de 14 días se define una sola vez en `news/retention.py` para ingesta, consulta y limpieza. `purge_old_articles` elimina noticias cuya publicación es estrictamente anterior al corte; si falta esa fecha, utiliza la captura. Incluye `--dry-run` para contar sin borrar. Limpia también feeds inactivos y preserva fuentes, categorías y preferencias; el ORM elimina las asociaciones de los artículos borrados. La tarea programada limpia antes de importar para cumplir la política aunque después falle un RSS.

## Decisiones vigentes

1. RSS es la fuente principal del MVP.
2. La aplicación se implementa con Python y Django, con plantillas del servidor.
3. PostgreSQL almacena usuarios, preferencias, fuentes y metadatos de noticias.
4. Django administra el registro, el inicio de sesión y las sesiones de usuario.
5. La primera entrega no incluye imágenes ni almacenamiento de archivos.
6. La categorización básica forma parte de la primera entrega; deportes queda para más adelante.
7. Se muestran los datos proporcionados por los feeds cuando la política de la fuente lo permite.
8. La primera entrega elimina duplicados exactos; el agrupamiento de coberturas queda para después.
9. GDELT se integra después como radar de cobertura y nunca como dependencia única.
10. No se incorporan servicios pagos.
11. Render Free aloja el sitio y Supabase Free almacena PostgreSQL; no se crea otra base administrada en Render.
12. La ingesta está programada cada dos horas de 06:00 a medianoche en horario argentino, con diez consultas previstas por día y conservación de noticias durante 14 días.
13. La interfaz comparte identidad visual en las cinco páginas del sitio, conserva textos y funciones, y pagina independientemente por categoría de diez en diez.
14. Las decisiones nuevas o modificadas deben quedar registradas en este documento.
