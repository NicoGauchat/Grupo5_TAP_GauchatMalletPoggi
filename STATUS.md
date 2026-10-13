# Estado del proyecto

**Última actualización:** 2026-10-12
**Objetivo actual:** preparar el despliegue de Django en Render con PostgreSQL en Supabase y activar la ingesta periódica.

## Último paso completado

Se corrigió el pin de Gunicorn a la versión 26.2.0, disponible en PyPI; Render no podía resolver la versión 26.2.2 indicada antes. La corrección está en `codex/fix-gunicorn-version` y requiere integrarse a `main` antes de reintentar el despliegue.

## Próximo paso

Integrar la corrección de Gunicorn a `main`, reintentar el despliegue en Render y atender cualquier nuevo error de build o conexión.

## Completado

- Django y PostgreSQL local con Docker Compose; arquitectura anterior preservada.
- Registro, ingreso, salida y preferencias individuales.
- Ocho categorías y once feeds RSS activos precargados mediante migraciones.
- Ingesta RSS/Atom, clasificación por etiquetas aprobadas, deduplicación exacta y solicitudes condicionales.
- Página personalizada con noticias por categoría, columnas ordenadas por cantidad y filtros por fuente e idioma.
- Conservación inicial de 14 días, compartida por ingesta, consulta y limpieza.
- Configuración de Render Free y conexión prevista a Supabase Session pooler con SSL.
- Workflow manual y programado cuatro veces al día; queda inactivo hasta configurar secretos y `NEWS_INGESTION_ENABLED`.
- No se guardan artículos completos ni imágenes; `SOURCES.md` no cambió porque no se modificaron feeds ni políticas.

## Pendiente

- Provisionar Supabase y Render, ejecutar el primer despliegue y verificar la aplicación publicada.
- Revisar el ruido de Clarín Mundo y Economía y evaluar nuevas fuentes para mercados argentinos.

## Bloqueos

- La activación requiere crear la cuenta/proyecto remoto y cargar credenciales en los paneles; no compartir secretos por chat ni versionarlos.

## Última verificación

- Revisión de documentación oficial de Render, Supabase, Gunicorn y WhiteNoise; licencias MIT y proyectos comparables registrados en `PROJECT.md`.
- Render Free duerme tras 15 minutos sin tráfico y tiene filesystem efímero; Supabase Free ofrece 500 MB y puede pausar proyectos con poca actividad durante siete días.
- La ventana de retención es configurable en `news/retention.py`; feeds, resúmenes e imágenes no cambiaron.
- `.venv` instaló `requirements.txt` en Windows; Gunicorn se omitió por su marcador de plataforma y WhiteNoise se instaló correctamente.
- `manage.py check --settings=config.test_settings`: sin problemas; `makemigrations --check --dry-run`: sin cambios de esquema.
- `collectstatic` real copió 128 archivos y procesó 384 con WhiteNoise; la salida vive en el directorio ignorado `staticfiles/`. `git diff --check`: sin errores.
- No se ejecutó la suite de pruebas. Para esta corrección se confirmó que Gunicorn 26.2.0 está publicado en PyPI y `git diff --check` no detectó errores; falta comprobar el build de Render.
- La cuenta administradora se creará desde el entorno local conectado a Supabase, ya que Render Free no ofrece Shell.
