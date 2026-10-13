# Sitio Noticias

Aplicación web universitaria para reunir noticias de fuentes seleccionadas, organizarlas por categoría y permitir que cada usuario configure sus temas de interés. Prioriza RSS, atribuye siempre al medio original y muestra varias fuentes.

## Ya implementado

- Registro e inicio de sesión con usuarios de Django.
- Preferencias individuales para ocho categorías, incluidas Argentina y Mercados y finanzas.
- Página de noticias para usuarios autenticados, separada por sus categorías, con fuente, fecha y enlace original.
- Modelos y administración de categorías, fuentes, feeds y artículos.
- Ingesta manual de once feeds RSS preseleccionados, clasificación por etiquetas aprobadas y deduplicación exacta con categorías conservadas por origen.
- Filtros combinables por fuente e idioma en la página personalizada.
- Paginación independiente de diez noticias por categoría, con estado en la URL.
- Botones para guardar o quitar noticias y una página privada Mis guardadas para cada usuario.
- Identidad editorial compartida en inicio, ingreso, registro, preferencias y noticias; fuentes locales y diseño adaptable.
- Limpieza de noticias de más de 14 días, con vista previa.
- Preparación de despliegue gratuito de Django en Render y PostgreSQL administrado en Supabase.
- Workflow de GitHub Actions para limpieza e ingesta cada dos horas, de 06:00 a medianoche en hora argentina; pendiente de activar.

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

Gunicorn se instala automáticamente en sistemas POSIX como Render; en Windows se omite porque no se usa para ejecutar el servidor local.

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

Después de ingresar, abrir `http://127.0.0.1:8000/noticias/`. La página usa hasta 1680 px de ancho y presenta hasta cuatro columnas desde 1280 px, dos entre 768 y 1279 px y una por debajo de 768 px. Las columnas se ordenan por el total de noticias filtradas, de mayor a menor, con desempate alfabético. Cada sección muestra diez titulares por página, con fuente, fecha, idioma y enlace original; la última puede tener menos. «Más reciente» identifica únicamente el primer artículo de la primera página; aún no se calcula relevancia.

«Anterior», «Página X de Y» y «Siguiente» aparecen cuando una sección tiene más de diez noticias. La paginación es independiente: `/noticias/?source=1&language=es&page_tecnologia=2&page_ciencia=3` mantiene filtros y páginas de las otras categorías. Los enlaces regresan al encabezado de la sección mediante un fragmento. Una página ausente, no entera o menor que uno muestra la primera; una superior al máximo muestra la última. Funciona sin JavaScript y conserva el estado al recargar o usar el historial del navegador.

Los selectores «Fuente» e «Idioma» se combinan al pulsar «Aplicar filtros», antes de paginar, y mantienen la selección en la URL. Aplicar o limpiar filtros reinicia todas las páginas. «Limpiar filtros» muestra todas las fuentes e idiomas disponibles en las categorías elegidas. Los filtros inválidos muestran errores y ningún resultado; las combinaciones sin coincidencias permiten limpiarlos. Las noticias de más de 14 días no aparecen aunque todavía no haya corrido la limpieza.

Inicio, ingreso y registro combinan un panel azul con la marca tipográfica y una zona clara para contenido o formularios. Las preferencias usan casillas nativas con etiquetas completas. La interfaz comparte colores, controles, mensajes y foco visible; mantiene los textos y recorridos anteriores. Archivo y Source Sans 3 se sirven desde `news/static/news/fonts/`, con sus licencias OFL y fuentes de respaldo, sin consultar Google al navegar. No se requieren paquetes ni variables de entorno nuevos.

`ingest_feeds` procesa los feeds activos y puede ejecutarse manualmente de nuevo. Para procesar sólo uno: `python manage.py ingest_feeds --feed-id 1`, sustituyendo `1` por el ID mostrado en la administración. El comando informa cuántas noticias creó, encontró duplicadas u omitió. Los once feeds activos guardan título, fuente, fecha, enlace e idioma; **no** guardan resúmenes, imágenes ni el texto completo. Las entradas de más de 14 días se omiten. La ejecución periódica queda pendiente de activar con una base pública.

La clasificación usa la lista editable de [news/category_aliases.py](./news/category_aliases.py). Cada alias debe ser el nombre de una etiqueta realmente observada en un feed y se compara completo, ignorando mayúsculas, tildes y espacios extra. Una noticia puede recibir varias categorías. Si la entrada no trae etiquetas, se usan las categorías de respaldo configuradas en el feed desde `/admin/`; si trae etiquetas no aprobadas, queda sin categoría. Después de modificar la lista, ejecutar `python manage.py ingest_feeds --refresh` para volver a descargar y reclasificar las noticias existentes. La clasificación se conserva por origen: actualizar un feed reemplaza su aporte y combina el resultado con los demás, sin borrar sus categorías ni duplicar la noticia. La atribución y los filtros siguen usando el feed original. La revisión inicial de etiquetas está registrada en [SOURCES.md](./SOURCES.md).

«Argentina» combina noticias de política nacional de Clarín y Los Andes con economía argentina de Los Andes. «Mercados y finanzas» muestra noticias sobre bolsa, inversiones y finanzas de Cinco Días y artículos pertinentes de EL PAÍS. Son titulares y enlaces periodísticos; no hay cotizaciones bursátiles en tiempo real. Las dos categorías se pueden elegir en «Mis categorías» y aparecen como columnas en `/noticias/`.

## Actualizar una instalación existente

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

**El workflow está preparado, pero todavía no se activó ni se verificó una ejecución remota.** GitHub Actions y Render usarán el mismo proyecto PostgreSQL de Supabase. GitHub no puede acceder al PostgreSQL local en `127.0.0.1`. No se crea una base temporal para la ingesta ni se expone el puerto local.

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

El plan gratuito de Render duerme el servicio tras 15 minutos sin solicitudes y puede tardar cerca de un minuto en despertar. Tiene 750 horas de instancia por espacio de trabajo al mes y un sistema de archivos efímero; por eso no guardamos noticias en el disco de Render. Supabase Free ofrece 500 MB de base de datos y puede pausar proyectos con poca actividad durante siete días. La ingesta programada puede ayudar a mantener actividad, pero hay que revisar el estado y el uso desde ambos paneles. Render indica que Free es para pruebas y proyectos personales, no para aplicaciones con requisitos de disponibilidad; además, los excesos de cuota pueden generar cargos si se agrega un medio de pago. Para mantener este despliegue sin costo, no agregar recursos pagos ni un medio de pago y revisar las cuotas. Referencias: [límites gratuitos y condiciones de Render](https://render.com/docs/free), [preguntas frecuentes de facturación de Render](https://render.com/docs/faq), [despliegue Django en Render](https://render.com/docs/deploy-django), [conexiones PostgreSQL de Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres) y [pausa de proyectos Supabase](https://supabase.com/docs/guides/platform/free-project-pausing).

## Verificación

Con el entorno virtual activado:

```powershell
python manage.py test --settings=config.test_settings
python manage.py check --settings=config.test_settings
python manage.py makemigrations --check --dry-run --settings=config.test_settings
```

`config.test_settings` usa SQLite en memoria y una clave exclusiva para pruebas: permite verificar sin `.env`, Docker, credenciales reales ni `collectstatic`. Sólo en pruebas se desactiva la redirección HTTPS, se usa almacenamiento estático sin manifiesto y se excluye WhiteNoise; producción mantiene su configuración. La suite cubre filtros, protección de acceso, categorías, paginación y enlaces independientes, parámetros inválidos, orden, conservación, orígenes, reclasificación, GUID y migración con datos existentes. Para comprobar PostgreSQL, usar `python manage.py test` con la configuración normal y una cuenta con permiso para crear la base de pruebas. La configuración de pruebas no debe usarse para ejecutar o desplegar la aplicación.

## Documentación

- [PROJECT.md](./PROJECT.md): alcance, arquitectura y decisiones vigentes.
- [ARCHITECTURE-LEGACY.md](./ARCHITECTURE-LEGACY.md): copia de referencia de la arquitectura anterior de TypeScript, Next.js y Supabase.
- [STATUS.md](./STATUS.md): estado operativo y único próximo paso.
- [SOURCES.md](./SOURCES.md): feeds investigados y políticas por fuente.
- [AGENTS.md](./AGENTS.md): reglas de trabajo y actualización documental.
- [.env.example](./.env.example): variables previstas, sin credenciales reales.
