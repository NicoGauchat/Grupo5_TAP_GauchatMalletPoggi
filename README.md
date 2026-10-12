# Sitio Noticias

Aplicación web universitaria para reunir noticias de fuentes seleccionadas, organizarlas por categoría y permitir que cada usuario configure sus temas de interés. Prioriza RSS, atribuye siempre al medio original y muestra varias fuentes.

## Ya implementado

- Registro e inicio de sesión con usuarios de Django.
- Preferencias individuales para las cinco categorías iniciales.
- Página de noticias para usuarios autenticados, separada por sus categorías, con fuente, fecha y enlace original.
- Modelos y administración de categorías, fuentes, feeds y artículos.
- Ingesta manual de tres feeds RSS preseleccionados, clasificación por etiquetas aprobadas y deduplicación exacta.
- Filtros combinables por fuente e idioma en la página personalizada.
- Limpieza de noticias de más de 60 días, con vista previa.
- Workflow de GitHub Actions para limpieza e ingesta cada hora; pendiente de activar con una base pública persistente.

## Funcionalidades previstas

- Configurar PostgreSQL público y activar la recolección periódica.
- Ampliar la cobertura de las cinco categorías iniciales. Deportes queda para una etapa posterior.
- Incorporar posteriormente agrupamiento de coberturas y GDELT como complemento.

## Stack acordado

- Python y Django para la aplicación web, autenticación, interfaz del servidor e ingesta.
- PostgreSQL para usuarios, preferencias, fuentes y noticias.
- Plantillas HTML de Django, CSS y JavaScript mínimo para la interfaz.
- GitHub Actions para ejecutar periódicamente el comando de ingesta.

## Arquitectura resumida

```text
Feeds RSS → comando de ingesta Django → normalización y deduplicación → PostgreSQL
                                                                      ↑
Navegador → páginas Django con autenticación y preferencias ──────────┘
```

El proveedor para alojar Django y PostgreSQL aún no está decidido. Se elegirá después de comprobar persistencia y límites del plan gratuito. No se utilizarán servicios pagos.

## Estado

Ya existe el proyecto Django, la base PostgreSQL, el registro de usuarios, la ingesta manual de Clarín Tecnología, EL PAÍS Tecnología y MIT News sobre IA, y la página de noticias personalizada. Los artículos importados pueden consultarse desde `/admin/` y cada usuario registrado ve los de sus categorías en `/noticias/`.

El próximo paso vigente se mantiene en [STATUS.md](./STATUS.md).

## Desarrollo local en Windows

Requisitos: Python 3.13 y Docker Desktop con el motor iniciado. La base de datos corre en un contenedor PostgreSQL 17 y escucha sólo en `127.0.0.1:5433`, para evitar conflicto con una instalación local en el puerto 5432.

En PowerShell, desde la raíz del repositorio:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Editar `.env` y completar `DJANGO_SECRET_KEY` y `POSTGRES_PASSWORD` con valores distintos y aleatorios. Se pueden generar con estos comandos y copiarlos al archivo local:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

El archivo `.env` está ignorado por Git. No compartirlo ni subirlo al repositorio.

```powershell
docker compose up -d db
python manage.py migrate
python manage.py ingest_feeds
python manage.py createsuperuser
python manage.py runserver
```

Abrir `http://127.0.0.1:8000/` para crear una cuenta y elegir categorías, o `/admin/` para gestionar fuentes y modelos. `createsuperuser` solicita usuario y contraseña para la administración. Para detener sólo la base de datos, ejecutar `docker compose down`. El volumen conserva los datos entre reinicios.

Después de ingresar, abrir `http://127.0.0.1:8000/noticias/`. La página muestra hasta diez titulares recientes por categoría elegida, con fuente, fecha, idioma y enlace al artículo original. La noticia destacada de cada categoría es la más reciente; aún no se calcula relevancia. Si se cambia la selección en «Mis categorías», las noticias visibles cambian al guardar. Los selectores «Fuente» e «Idioma» se combinan al pulsar «Aplicar filtros» y mantienen la selección en la URL, por ejemplo `/noticias/?source=1&language=es`. «Limpiar filtros» muestra todas las fuentes e idiomas de las categorías elegidas. Las opciones provienen de artículos recientes de feeds activos en esas categorías. Los filtros inválidos muestran un error y ningún resultado; las combinaciones sin coincidencias permiten limpiar los filtros. Las noticias de más de 60 días no aparecen, aunque todavía no haya corrido la limpieza.

`ingest_feeds` procesa los feeds activos y puede ejecutarse manualmente de nuevo. Para procesar sólo uno: `python manage.py ingest_feeds --feed-id 1`, sustituyendo `1` por el ID mostrado en la administración. El comando informa cuántas noticias creó, encontró duplicadas u omitió. Los tres feeds iniciales guardan título, fuente, fecha, enlace e idioma; **no** guardan resúmenes, imágenes ni el texto completo. Las entradas de más de 60 días se omiten.

La clasificación usa la lista editable de [news/category_aliases.py](./news/category_aliases.py). Cada alias debe ser el nombre de una etiqueta realmente observada en un feed y se compara completo, ignorando mayúsculas, tildes y espacios extra. Una noticia puede recibir varias categorías. Si la entrada no trae etiquetas, se usan las categorías de respaldo configuradas en el feed desde `/admin/`; si trae etiquetas no aprobadas, queda sin categoría. Después de modificar la lista, ejecutar `python manage.py ingest_feeds --refresh` para volver a descargar y reclasificar las noticias existentes. La revisión inicial de etiquetas está registrada en [SOURCES.md](./SOURCES.md).

## Limpieza de noticias antiguas

```powershell
python manage.py purge_old_articles --dry-run
python manage.py purge_old_articles
```

El primer comando cuenta sin borrar; el segundo elimina de la base configurada. Se toma la fecha de publicación: se conserva una noticia de exactamente 60 días y se elimina cuando supera esa edad. Para registros sin fecha de publicación se usa la captura. Se limpian también noticias de feeds desactivados. Se conservan fuentes, feeds, categorías y preferencias; se eliminan las asociaciones de los artículos borrados.

## Ingesta periódica con GitHub Actions

[.github/workflows/ingest-feeds.yml](./.github/workflows/ingest-feeds.yml) ejecuta la limpieza y después la ingesta cada hora, al minuto 17 UTC, y permite una ejecución manual desde Actions. Usa Python 3.13, permisos de lectura y una única ejecución de mantenimiento a la vez. La limpieza ocurre antes de consultar los feeds para que un fallo de RSS no impida aplicar la conservación.

**El workflow está preparado, pero no está activo.** Primero hay que elegir PostgreSQL público, persistente y permitido en un plan gratuito. GitHub no puede acceder al PostgreSQL local en `127.0.0.1`. No se crea una base temporal para la ingesta ni se expone el puerto local.

Para activarlo:

1. Subir el workflow a la rama predeterminada.
2. Configurar la base pública y aplicar `python manage.py migrate` contra ella usando su configuración local protegida. La aplicación web y la ingesta deben usar esa misma base.
3. En **Settings → Secrets and variables → Actions**, agregar los secretos `DJANGO_SECRET_KEY`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_HOST`.
4. Agregar la variable `POSTGRES_PORT` si difiere de `5432`. El workflow usa `POSTGRES_SSLMODE=require` por defecto; puede configurarse como `verify-ca` o `verify-full` con los certificados necesarios según el proveedor. Para Docker local, `.env.example` conserva `prefer`.
5. Establecer la variable `NEWS_INGESTION_ENABLED` en `true` y ejecutar manualmente «Ingesta y limpieza de noticias» para comprobar la conexión. Para pausar, cambiar esa variable a `false`.

El workflow comprueba los secretos sin imprimir sus valores y exige migraciones aplicadas; no modifica automáticamente el esquema público. Si falla un feed, continúa con los demás y finalmente marca la ejecución como fallida. Los resultados están en Actions. GitHub puede retrasar horarios y desactiva la programación en repositorios públicos tras 60 días sin actividad. Revisar la cuota gratuita de Actions antes de activarlo. Referencias: [horarios](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) y [secretos](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).

## Verificación

Con el entorno virtual activado:

```powershell
python manage.py test --settings=config.test_settings
python manage.py check --settings=config.test_settings
python manage.py makemigrations --check --dry-run --settings=config.test_settings
```

`config.test_settings` usa SQLite en memoria y una clave exclusiva para pruebas: permite verificar sin `.env`, Docker ni credenciales reales. Cubre filtros, autenticación, categorías, límites de resultados y conservación. Para comprobar PostgreSQL, usar `python manage.py test` con la configuración normal y una cuenta con permiso para crear la base de pruebas. La configuración de pruebas no debe usarse para ejecutar o desplegar la aplicación.

## Documentación

- [PROJECT.md](./PROJECT.md): alcance, arquitectura y decisiones vigentes.
- [ARCHITECTURE-LEGACY.md](./ARCHITECTURE-LEGACY.md): copia de referencia de la arquitectura anterior de TypeScript, Next.js y Supabase.
- [STATUS.md](./STATUS.md): estado operativo y único próximo paso.
- [SOURCES.md](./SOURCES.md): feeds investigados y políticas por fuente.
- [AGENTS.md](./AGENTS.md): reglas de trabajo y actualización documental.
- [.env.example](./.env.example): variables previstas, sin credenciales reales.
