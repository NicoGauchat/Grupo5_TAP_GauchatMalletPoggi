# Estado del proyecto

**Última actualización:** 2026-10-11
**Objetivo actual:** continuar desde la base Django y PostgreSQL ya operativa.

## Último paso completado

Se creó el proyecto Django, la aplicación `news` y la base local PostgreSQL mediante Docker Compose. Se aplicaron las migraciones del esquema y de las cinco categorías iniciales. Los modelos están disponibles en la administración de Django. También se implementaron registro, ingreso, salida y edición de preferencias.

## Próximo paso

Implementar la ingesta RSS con una primera selección de feeds, respetando la política de cada fuente y evitando duplicados exactos.

## Completado

- Arquitectura anterior preservada en `ARCHITECTURE-LEGACY.md`.
- Dependencias fijadas: Django 5.2 LTS, psycopg 3 y python-dotenv.
- Configuración local de PostgreSQL 17 en un contenedor, puerto 5433 y volumen persistente.
- Migraciones `news.0001_initial` y `news.0002_initial_categories` aplicadas en PostgreSQL.
- Modelos `Category`, `Source`, `Feed`, `Article` y `UserPreference`, con sus relaciones y restricciones iniciales.
- Administración Django para gestionar los cinco modelos.
- Registro, ingreso, salida y preferencias por usuario con formularios integrados de Django.
- Cinco categorías iniciales cargadas por una migración de datos.
- Variables de entorno documentadas en `.env.example`; archivo `.env` local ignorado por Git.
- Instrucciones de instalación y ejecución local agregadas al README.
- Política de imágenes y uso de resúmenes aclarada en `SOURCES.md`.

## Pendiente

- Implementar la ingesta periódica, política por fuente y deduplicación de RSS.
- Construir la interfaz del feed y sus filtros.
- Elegir proveedor de alojamiento y PostgreSQL que conserve datos bajo un plan permitido.
- Configurar automatización de la ingesta y limpieza de noticias con más de 60 días.

## Bloqueos

Ninguno conocido. Durante el arranque de Docker Desktop se observó un socket temporal inaccesible y una respuesta HTTP 500. La revisión automática bloqueó eliminar el socket desde este entorno; no se insistió en esa operación. Tras iniciar Docker Desktop manualmente, el motor funcionó y la imagen de PostgreSQL se descargó correctamente.

## Última verificación

- `python manage.py check`: sin problemas, incluidas las rutas y páginas de autenticación.
- `python manage.py makemigrations --check --dry-run`: sin cambios de esquema pendientes.
- `docker compose config --quiet`: configuración válida.
- `docker compose ps`: PostgreSQL activo en `127.0.0.1:5433`.
- `python manage.py showmigrations news`: ambas migraciones aplicadas.
- Consulta de categorías: están presentes los cinco slugs iniciales.
- `git diff --check`: sin errores de espacios.
- `git check-ignore .env`: confirma que el archivo de credenciales local no se versiona.
