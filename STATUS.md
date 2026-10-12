# Estado del proyecto

**Última actualización:** 2026-10-12
**Objetivo actual:** preparar la activación de la ingesta periódica en una base pública persistente.

## Último paso completado

Se agregaron filtros combinables por fuente e idioma en `/noticias/`, con validación, selección en la URL, limpieza de filtros y mensajes sin resultados. Se implementó `purge_old_articles` para eliminar noticias de más de 60 días, con vista previa y conservación de fuentes y preferencias. La ingesta y el feed comparten la misma ventana temporal.

Se creó un workflow de GitHub Actions para limpieza e ingesta cada hora, con ejecución manual, SSL y control de concurrencia. El usuario eligió GitHub Actions con una base pública todavía por configurar: el workflow queda deshabilitado hasta establecer `NEWS_INGESTION_ENABLED=true` y cargar sus secretos. La automatización está implementada, pero no activa.

## Próximo paso

Configurar PostgreSQL público persistente en un plan gratuito permitido para activar y verificar el workflow de ingesta.

## Completado

- Monolito Django con PostgreSQL local en Docker Compose.
- Registro, ingreso, salida y preferencias por usuario.
- Feed personalizado con hasta diez noticias por categoría, fuente, fecha, idioma y enlace original.
- Filtros combinables por fuente e idioma, con estados vacíos y validación.
- Modelos, administración y migraciones para categorías, fuentes, feeds, artículos y preferencias.
- Cinco categorías iniciales y tres feeds RSS precargados: Clarín, EL PAÍS y MIT News.
- Ingesta RSS/Atom con límites de tamaño y espera, deduplicación y solicitudes condicionales.
- Clasificación por etiquetas aprobadas y reclasificación con `--refresh`.
- Restricciones por feed: los tres iniciales no guardan resúmenes ni imágenes.
- Limpieza de noticias de más de 60 días con `--dry-run`; el feed también excluye las antiguas.
- Workflow horario y manual de mantenimiento, listo para configurar la base pública.
- Pruebas automatizadas de filtros, acceso, categorías y conservación.
- README, PROJECT y `.env.example` actualizados con comandos, activación y SSL.

## Pendiente

- Configurar la base pública y activar/verificar la automatización en GitHub.
- Elegir alojamiento público para Django con un plan gratuito permitido.
- Ampliar fuentes y cobertura de categorías tras revisar actividad y condiciones.

## Bloqueos

- La ejecución real del workflow requiere una base pública y secretos aún no configurados.
- En este entorno no hay `.env` ni Docker disponible: no se ejecutó la limpieza contra la base real ni se verificó una conexión PostgreSQL.

## Última verificación

- 14 pruebas aprobadas con `python manage.py test --settings=config.test_settings`, usando SQLite en memoria y Python 3.12.14 disponible en el entorno. El workflow configura Python 3.13 conforme al requisito del proyecto.
- Se verificaron filtros individuales y combinados, errores, reinicio, aislamiento por categorías, feeds inactivos, noticias antiguas y filtrado antes del límite de diez.
- Se verificaron borrado estricto después de 60 días, conservación en el límite exacto, vista previa, idempotencia, relaciones y respaldo por fecha de captura.
- `python manage.py check --settings=config.test_settings`: sin problemas.
- `python manage.py makemigrations --check --dry-run --settings=config.test_settings`: sin cambios de esquema.
- Workflow validado con actionlint, sin errores de sintaxis ni expresiones.
- La validación del workflow aceptó configuración de prueba válida y rechazó secretos faltantes, host local y conexión sin SSL, sin imprimir valores.
- No se modificó `SOURCES.md`: los feeds, sus estados y políticas de reutilización permanecen iguales.
