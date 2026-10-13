# Sitio Noticias

Aplicación web universitaria para reunir noticias de fuentes seleccionadas, organizarlas por categoría y permitir que cada usuario configure sus temas de interés. Prioriza RSS, atribuye siempre al medio original y muestra varias fuentes.

## Ya implementado

- Registro e inicio de sesión con usuarios de Django.
- Preferencias individuales para ocho categorías, incluidas Argentina y Mercados y finanzas.
- Página de noticias para usuarios autenticados, separada por sus categorías, con fuente, fecha y enlace original.
- Modelos y administración de categorías, fuentes, feeds y artículos.
- Ingesta manual de once feeds RSS preseleccionados, clasificación por etiquetas aprobadas y deduplicación exacta.
- Filtros combinables por fuente e idioma en la página personalizada.
- Limpieza de noticias de más de 14 días, con vista previa.
- Preparación de despliegue gratuito de Django en Render y PostgreSQL administrado en Supabase.
- Workflow de GitHub Actions para limpieza e ingesta cuatro veces por día; pendiente de activar.

## Funcionalidades previstas

- Crear el proyecto de Supabase, desplegar Django en Render y activar la recolección periódica.
- Ampliar la cobertura de las ocho categorías. Deportes queda para una etapa posterior.
- Incorporar posteriormente agrupamiento de coberturas y GDELT como complemento.

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

Ya existe el proyecto Django, la base PostgreSQL, el registro de usuarios, la ingesta manual de once feeds de Clarín, EL PAÍS, MIT News, Los Andes y Cinco Días, y la página de noticias personalizada. Los artículos importados pueden consultarse desde `/admin/` y cada usuario registrado ve los de sus categorías en `/noticias/`.

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

Después de ingresar, abrir `http://127.0.0.1:8000/noticias/`. La página usa hasta 1680 px de ancho y presenta las categorías elegidas en hasta cuatro columnas; pasa a dos o una columna en pantallas más chicas. Las columnas se ordenan por cantidad de noticias, de mayor a menor, y el encabezado indica el total filtrado de cada categoría. En cada una se muestran hasta diez titulares recientes con fuente, fecha, idioma y enlace al artículo original. El primero se destaca por ser el más reciente; aún no se calcula relevancia. Los selectores «Fuente» e «Idioma» se combinan al pulsar «Aplicar filtros» y mantienen la selección en la URL, por ejemplo `/noticias/?source=1&language=es`. «Limpiar filtros» muestra todas las fuentes e idiomas disponibles en las categorías elegidas. Los filtros inválidos muestran un error y ningún resultado; las combinaciones sin coincidencias permiten limpiarlos. Las noticias de más de 14 días no aparecen, aunque todavía no haya corrido la limpieza.

`ingest_feeds` procesa los feeds activos y puede ejecutarse manualmente de nuevo. Para procesar sólo uno: `python manage.py ingest_feeds --feed-id 1`, sustituyendo `1` por el ID mostrado en la administración. El comando informa cuántas noticias creó, encontró duplicadas u omitió. Los once feeds activos guardan título, fuente, fecha, enlace e idioma; **no** guardan resúmenes, imágenes ni el texto completo. Las entradas de más de 14 días se omiten. La ejecución periódica queda pendiente de activar con una base pública.

La clasificación usa la lista editable de [news/category_aliases.py](./news/category_aliases.py). Cada alias debe ser el nombre de una etiqueta realmente observada en un feed y se compara completo, ignorando mayúsculas, tildes y espacios extra. Una noticia puede recibir varias categorías. Si la entrada no trae etiquetas, se usan las categorías de respaldo configuradas en el feed desde `/admin/`; si trae etiquetas no aprobadas, queda sin categoría. Después de modificar la lista, ejecutar `python manage.py ingest_feeds --refresh` para volver a descargar y reclasificar las noticias existentes. La revisión inicial de etiquetas está registrada en [SOURCES.md](./SOURCES.md).

«Argentina» combina noticias de política nacional de Clarín y Los Andes con economía argentina de Los Andes. «Mercados y finanzas» muestra noticias sobre bolsa, inversiones y finanzas de Cinco Días y artículos pertinentes de EL PAÍS. Son titulares y enlaces periodísticos; no hay cotizaciones bursátiles en tiempo real. Las dos categorías se pueden elegir en «Mis categorías» y aparecen como columnas en `/noticias/`.

## Limpieza de noticias antiguas

```powershell
python manage.py purge_old_articles --dry-run
python manage.py purge_old_articles
```

El primer comando cuenta sin borrar; el segundo elimina de la base configurada. Se toma la fecha de publicación: se conserva una noticia de exactamente 14 días y se elimina cuando supera esa edad. Para registros sin fecha de publicación se usa la captura. Se limpian también noticias de feeds desactivados. Se conservan fuentes, feeds, categorías y preferencias; se eliminan las asociaciones de los artículos borrados.

## Ingesta periódica con GitHub Actions

[.github/workflows/ingest-feeds.yml](./.github/workflows/ingest-feeds.yml) ejecuta la limpieza y después la ingesta cada seis horas, al minuto 17 UTC (cuatro veces por día), y permite una ejecución manual desde Actions. Usa Python 3.13, permisos de lectura y una única ejecución de mantenimiento a la vez. La limpieza ocurre antes de consultar los feeds para que un fallo de RSS no impida aplicar la conservación.

**El workflow está preparado, pero no está activo.** GitHub Actions y Render usarán el mismo proyecto PostgreSQL de Supabase. GitHub no puede acceder al PostgreSQL local en `127.0.0.1`. No se crea una base temporal para la ingesta ni se expone el puerto local.

Para activarlo:

1. Crear el proyecto de Supabase en **East US (North Virginia)** para usar una región cercana a Render Virginia.
2. En Connect → Session pooler, copiar host, nombre de base, usuario y contraseña. La configuración esperada es puerto `5432` y SSL `require`; el pooler compartido admite IPv4, necesario para estos servicios.
3. Subir `render.yaml` a `main` y crear un Blueprint desde el panel de Render. Al aplicarlo, completar las variables de conexión a Supabase cuando Render las solicite. El build instala las dependencias, recoge archivos estáticos y aplica migraciones; no crea una segunda base.
4. En Settings → Secrets and variables → Actions, agregar los secretos `DJANGO_SECRET_KEY`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_HOST`. Usar los mismos valores de conexión de Supabase; `DJANGO_SECRET_KEY` puede generarse con el comando indicado arriba.
5. En Variables → Actions, establecer `POSTGRES_PORT=5432`, `POSTGRES_SSLMODE=require` y `NEWS_INGESTION_ENABLED=true`. Ejecutar manualmente «Ingesta y limpieza de noticias» para comprobar la conexión. Para pausar, cambiar `NEWS_INGESTION_ENABLED` a `false`.
6. El plan gratuito de Render no incluye Shell. Para crear la cuenta administradora, configurar temporalmente el `.env` local con las credenciales de Supabase y ejecutar `python manage.py createsuperuser`; después, restaurar la configuración local. Gestionar feeds desde `/admin/`.

El workflow comprueba los secretos sin imprimir sus valores y exige migraciones aplicadas; no modifica automáticamente el esquema público. Si falla un feed, continúa con los demás y finalmente marca la ejecución como fallida. Los resultados están en Actions. GitHub puede retrasar horarios y desactiva la programación en repositorios públicos tras 60 días sin actividad. Revisar la cuota gratuita de Actions antes de activarlo. Referencias: [horarios](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) y [secretos](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).

## Despliegue web en Render

`render.yaml` describe un servicio web gratuito, vinculado a la rama `main`, con Django, Gunicorn y WhiteNoise. Render genera `DJANGO_SECRET_KEY`; el resto de las credenciales de Supabase se solicitan al crear el Blueprint. Los cambios desplegados sirven archivos estáticos mediante WhiteNoise. Las migraciones se ejecutan durante el build, y las noticias continúan en PostgreSQL aunque el servicio se reinicie.

El plan gratuito de Render duerme el servicio tras 15 minutos sin solicitudes y puede tardar cerca de un minuto en despertar. Tiene 750 horas de instancia por espacio de trabajo al mes y un sistema de archivos efímero; por eso no guardamos noticias en el disco de Render. Supabase Free ofrece 500 MB de base de datos y puede pausar proyectos con poca actividad durante siete días. La ingesta cuatro veces al día ayudará a mantener actividad, pero hay que revisar el estado y el uso desde ambos paneles. Render indica que Free es para pruebas y proyectos personales, no para aplicaciones con requisitos de disponibilidad; además, los excesos de cuota pueden generar cargos si se agrega un medio de pago. Para mantener este despliegue sin costo, no agregar recursos pagos ni un medio de pago y revisar las cuotas. Referencias: [límites gratuitos y condiciones de Render](https://render.com/docs/free), [preguntas frecuentes de facturación de Render](https://render.com/docs/faq), [despliegue Django en Render](https://render.com/docs/deploy-django), [conexiones PostgreSQL de Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres) y [pausa de proyectos Supabase](https://supabase.com/docs/guides/platform/free-project-pausing).

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
