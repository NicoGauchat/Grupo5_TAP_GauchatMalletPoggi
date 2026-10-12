# Sitio Noticias

Aplicación web universitaria para reunir noticias de fuentes seleccionadas, organizarlas por categoría y permitir que cada usuario configure sus temas de interés. Prioriza RSS, atribuye siempre al medio original y muestra varias fuentes.

## Ya implementado

- Registro e inicio de sesión con usuarios de Django.
- Preferencias individuales para ocho categorías, incluidas Argentina y Mercados y finanzas.
- Página de noticias para usuarios autenticados, separada por sus categorías, con fuente, fecha y enlace original.
- Modelos y administración de categorías, fuentes, feeds y artículos.
- Ingesta manual de once feeds RSS preseleccionados, clasificación por etiquetas aprobadas y deduplicación exacta.

## Funcionalidades previstas

- Automatizar la recolección periódica de RSS.
- Clasificar por tecnología, inteligencia artificial, ciencia, economía, geopolítica, política argentina, Argentina y mercados y finanzas. Deportes queda para una etapa posterior.
- Filtrar las noticias por fuente e idioma.
- No almacenar artículos completos ni mostrar imágenes en la primera versión.
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

Después de ingresar, abrir `http://127.0.0.1:8000/noticias/`. La página usa hasta 1680 px de ancho para aprovechar pantallas grandes y presenta un mensaje de bienvenida y las categorías elegidas en hasta cuatro columnas; pasa a dos o una columna en pantallas más chicas. Las columnas se ordenan por cantidad de noticias, de mayor a menor, y el encabezado indica el total de cada categoría. En cada una se muestran hasta diez titulares recientes con fuente, fecha, idioma y enlace al artículo original. El primero se destaca por ser el más reciente; aún no se calcula relevancia. Si se cambia la selección en «Mis categorías», las noticias visibles cambian al guardar. Las categorías sin noticias muestran un mensaje y un enlace para editar preferencias. Los filtros por fuente e idioma quedan para el siguiente paso.

`ingest_feeds` procesa los feeds activos y puede ejecutarse manualmente de nuevo. Para procesar sólo uno: `python manage.py ingest_feeds --feed-id 1`, sustituyendo `1` por el ID mostrado en la administración. El comando informa cuántas noticias creó, encontró duplicadas u omitió. Los once feeds activos guardan título, fuente, fecha, enlace e idioma; **no** guardan resúmenes, imágenes ni el texto completo. Las entradas de más de 60 días se omiten. La ejecución periódica y la eliminación de noticias antiguas se incorporarán después.

La clasificación usa la lista editable de [news/category_aliases.py](./news/category_aliases.py). Cada alias debe ser el nombre de una etiqueta realmente observada en un feed y se compara completo, ignorando mayúsculas, tildes y espacios extra. Una noticia puede recibir varias categorías. Si la entrada no trae etiquetas, se usan las categorías de respaldo configuradas en el feed desde `/admin/`; si trae etiquetas no aprobadas, queda sin categoría. Después de modificar la lista, ejecutar `python manage.py ingest_feeds --refresh` para volver a descargar y reclasificar las noticias existentes. La revisión inicial de etiquetas está registrada en [SOURCES.md](./SOURCES.md).

«Argentina» combina noticias de política nacional de Clarín y Los Andes con economía argentina de Los Andes. «Mercados y finanzas» muestra noticias sobre bolsa, inversiones y finanzas de Cinco Días y artículos pertinentes de EL PAÍS. Son titulares y enlaces periodísticos; no hay cotizaciones bursátiles en tiempo real. Las dos categorías se pueden elegir en «Mis categorías» y aparecen como columnas en `/noticias/`.

## Documentación

- [PROJECT.md](./PROJECT.md): alcance, arquitectura y decisiones vigentes.
- [ARCHITECTURE-LEGACY.md](./ARCHITECTURE-LEGACY.md): copia de referencia de la arquitectura anterior de TypeScript, Next.js y Supabase.
- [STATUS.md](./STATUS.md): estado operativo y único próximo paso.
- [SOURCES.md](./SOURCES.md): feeds investigados y políticas por fuente.
- [AGENTS.md](./AGENTS.md): reglas de trabajo y actualización documental.
- [.env.example](./.env.example): variables previstas, sin credenciales reales.
