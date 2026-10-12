# Estado del proyecto

**Última actualización:** 2026-10-11
**Objetivo actual:** completar los filtros del feed personalizado.

## Último paso completado

Se creó `/noticias/`, una página para usuarios autenticados que muestra hasta diez artículos recientes por categoría elegida, con fuente, fecha, idioma y enlace original. La navegación y el ingreso llevan a esta página; al guardar preferencias se vuelve a mostrar el feed actualizado. Hay estados vacíos para cuentas sin categorías y categorías sin artículos.

## Próximo paso

Agregar filtros por fuente e idioma al feed personalizado.

## Completado

- Arquitectura Django y PostgreSQL local con Docker Compose; arquitectura anterior preservada.
- Registro, ingreso, salida y edición de preferencias por usuario.
- Feed personalizado por categorías con enlaces a los artículos originales.
- Modelos y administración para categorías, fuentes, feeds, artículos y preferencias.
- Cinco categorías iniciales y tres feeds RSS activos cargados mediante migraciones.
- Lectura de RSS/Atom con feedparser, límite de tamaño y tiempo de espera.
- Deduplicación por GUID, URL original, URL normalizada y huella de respaldo.
- Solicitudes condicionales con `ETag` y `Last-Modified`.
- Lista de etiquetas aprobadas en `news/category_aliases.py` y reclasificación con `--refresh`.
- Restricción de resumen por feed; los tres activos no guardan resúmenes ni imágenes.
- Condiciones y comprobaciones actuales registradas en `SOURCES.md`.
- Comandos y requisitos de desarrollo actualizados en `README.md`.

## Pendiente

- Agregar filtros por fuente e idioma a la interfaz de noticias.
- Automatizar la ingesta periódica.
- Eliminar noticias almacenadas que superen los 60 días.
- Ampliar la selección de fuentes y categorías tras revisar actividad y condiciones.
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
- Entre los diez artículos más recientes de tecnología hay Clarín, EL PAÍS y MIT News; en inteligencia artificial hay EL PAÍS y MIT News.
- No se modificó `SOURCES.md`: no cambiaron feeds ni sus políticas. No se modificó `.env.example`: la página no añade variables de entorno.
