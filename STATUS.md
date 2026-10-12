# Estado del proyecto

**Última actualización:** 2026-10-11
**Objetivo actual:** incorporar Argentina y Mercados y finanzas a las preferencias.

## Último paso completado

Se agregaron las categorías `argentina` y `mercados-finanzas`. Se activaron Los Andes Política y Economía y Cinco Días Mercados; Clarín Política también alimenta Argentina. Las equivalencias de Los Andes se limitan a sus feeds para no confundir una etiqueta genérica «Política» con política argentina. Todos los canales conservan sólo metadatos y enlaces.

## Próximo paso

Agregar filtros por fuente e idioma al feed personalizado.

## Completado

- Arquitectura Django y PostgreSQL local con Docker Compose; arquitectura anterior preservada.
- Registro, ingreso, salida y edición de preferencias por usuario.
- Feed personalizado por categorías con enlaces a los artículos originales.
- Modelos y administración para categorías, fuentes, feeds, artículos y preferencias.
- Ocho categorías y once feeds RSS activos cargados mediante migraciones.
- Lectura de RSS/Atom con feedparser, límite de tamaño y tiempo de espera.
- Deduplicación por GUID, URL original, URL normalizada y huella de respaldo.
- Solicitudes condicionales con `ETag` y `Last-Modified`.
- Lista de etiquetas aprobadas en `news/category_aliases.py` y reclasificación con `--refresh`.
- Restricción de resumen por feed; los once activos no guardan resúmenes ni imágenes.
- Condiciones y comprobaciones actuales registradas en `SOURCES.md`.
- Comandos y requisitos de desarrollo actualizados en `README.md`.

## Pendiente

- Agregar filtros por fuente e idioma a la interfaz de noticias.
- Automatizar la ingesta periódica.
- Eliminar noticias almacenadas que superen los 60 días.
- Revisar el ruido de Clarín Mundo y Economía y evaluar más fuentes para mercados argentinos.
- Elegir alojamiento y PostgreSQL público con un plan permitido y persistente.

## Bloqueos

Ninguno conocido.

## Última verificación

- Los tres feeds elegidos respondieron HTTP 200 el 11/10/2026 y se interpretaron sin errores XML.
- `python manage.py check`: sin problemas.
- `python manage.py makemigrations --check --dry-run`: sin cambios de esquema pendientes.
- Migraciones `news.0003` y `news.0004` aplicadas correctamente en PostgreSQL.
- Primera ingesta: Clarín 10, EL PAÍS 21 y MIT News 39 noticias; 11 entradas antiguas omitidas.
- Reclasificación: 0 noticias nuevas, 70 duplicadas reconocidas y 11 entradas antiguas omitidas.
- Consulta de PostgreSQL: 70 artículos; tecnología 42, inteligencia artificial 49, ciencia 1 y 3 sin categoría. Un artículo puede pertenecer a más de una categoría.
- `python manage.py check`: sin problemas tras agregar la página.
- La plantilla `news/feed.html` se cargó correctamente.
- Tras el cambio visual, `python manage.py check` siguió sin problemas y la plantilla se cargó. El detector visual se ejecutó en modo limitado porque faltan sus módulos de análisis HTML/CSS; no informó hallazgos con ese alcance reducido.
- La herramienta de navegador rechazó inspeccionar la URL local por su política de acceso; la revisión visual en navegador queda a cargo del usuario al recargar la página.
- Tras ampliar el ancho, `python manage.py check` no informó problemas y la plantilla volvió a cargar. La herramienta de navegador sigue sin permitir inspeccionar la URL local.
- Tras corregir la carga del CSS, la plantilla renderizada incluye `container feed-wide`; la hoja usa una versión en la URL para evitar la copia anterior. La comprobación visual final depende de recargar la pestaña local del usuario.
- Orden observado en PostgreSQL para las cinco categorías: inteligencia artificial 49, tecnología 42, ciencia 1, economía 0 y geopolítica 0. `python manage.py check` y la carga de la plantilla terminaron sin problemas.
- Entre los diez artículos más recientes de tecnología hay Clarín, EL PAÍS y MIT News; en inteligencia artificial hay EL PAÍS y MIT News.
- Los cinco feeds nuevos respondieron HTTP 200 el 11/10/2026, con XML válido y noticias recientes. Se revisaron sus términos RSS y se dejaron desactivadas otras fuentes con restricciones de reutilización.
- `python manage.py check` y `python manage.py makemigrations --check --dry-run` terminaron sin problemas. `news.0005_expand_news_sources` se aplicó en PostgreSQL.
- La ingesta creó 90 artículos de los cinco feeds nuevos: Clarín 30 y EL PAÍS 60. La base contiene 160 artículos de 8 feeds; ninguno tiene resumen. Categorías: economía 39, geopolítica 16 y política argentina 10. Economía y geopolítica incluyen artículos de ambas fuentes; política argentina sólo de Clarín.
- Se actualizaron `PROJECT.md`, `SOURCES.md` y `README.md` por los cambios de alcance, feeds y funciones visibles. `.env.example` no requiere cambios porque no se agregaron variables.
- Los feeds de Los Andes Política (20 entradas), Los Andes Economía (20) y Cinco Días Mercados (25) respondieron HTTP 200 el 11/10/2026, con XML válido y publicaciones recientes. Sus páginas RSS permiten la lectura e inclusión en sitios web; se mantienen los resúmenes e imágenes desactivados.
- `news.0006_argentina_markets` se aplicó en PostgreSQL y se ejecutó `ingest_feeds --refresh`. Hay 235 artículos de 11 feeds y ninguno contiene resumen. Argentina tiene 50 noticias (10 de Clarín y 40 de Los Andes); Política argentina, 30 (10 de Clarín y 20 de Los Andes); Mercados y finanzas, 27 (24 de Cinco Días y 3 de EL PAÍS).
- `python manage.py check` y `python manage.py makemigrations --check --dry-run` terminaron sin problemas tras los cambios. El formulario de preferencias obtiene las categorías del modelo y muestra las dos nuevas sin modificar la interfaz. Se actualizaron `PROJECT.md`, `SOURCES.md` y `README.md`; `.env.example` no cambia porque no hay variables nuevas.
