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
- Categorización básica en tecnología, inteligencia artificial, ciencia, economía y geopolítica. Deportes queda fuera de esta entrega.
- Feed filtrable por categorías preferidas, fuente e idioma.
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

La aplicación será un monolito Django renderizado en el servidor: las páginas, formularios, sesiones, consultas y administración se implementan en el mismo proyecto. La ingesta será un comando reutilizable del proyecto, ejecutable manualmente durante el desarrollo y mediante GitHub Actions con la frecuencia definida.

El registro y el inicio de sesión usarán la autenticación integrada de Django. No se incorporará un proveedor externo de autenticación ni una API independiente en la primera entrega. Las noticias y fuentes serán datos compartidos; cada usuario podrá gestionar únicamente sus propias preferencias.

El proveedor de alojamiento y el proveedor de PostgreSQL para una publicación pública quedan pendientes de evaluar. Durante el desarrollo se utilizará PostgreSQL 17 en Docker Compose, con un volumen persistente y acceso local por `127.0.0.1:5433`. No se fija Supabase ni otro servicio hasta verificar que el plan elegido satisface la política de no pagar y conserva los datos requeridos.

GDELT seguirá el mismo modelo normalizado cuando se incorpore, pero no será la fuente principal. La aplicación debe continuar funcionando si GDELT no responde o limita consultas.

## Tecnologías

| Área | Decisión | Motivo |
|---|---|---|
| Lenguaje | Python | Un lenguaje para la web y la ingesta, con acompañamiento académico disponible |
| Aplicación web | Django | Incluye autenticación, sesiones, formularios, modelos, administración y plantillas del servidor |
| Interfaz | Plantillas Django, HTML, CSS y JavaScript mínimo | Evita mantener una aplicación frontend separada para las funciones iniciales |
| Base de datos | PostgreSQL | Base relacional para usuarios, preferencias, fuentes y noticias |
| Ingesta | Comando de administración Django | Comparte configuración y modelos de la aplicación; fácil de ejecutar y explicar |
| Automatización | GitHub Actions | Ejecuta el comando en un horario sin mantener un servidor de tareas |

La elección de cualquier dependencia externa para leer feeds o conectar servicios se documentará después de revisar su documentación oficial, mantenimiento, licencia y proyectos comparables, según las reglas del repositorio.

### Esquema inicial implementado

- `Category`: nombre y slug únicos para clasificar noticias y preferencias.
- `Source`: medio u organización de origen; puede tener varios feeds.
- `Feed`: URL única, idioma, categorías, estado de activación, permiso de mostrar el resumen y encabezados `ETag`/`Last-Modified`. Los feeds empiezan desactivados salvo los tres revisados para la primera ingesta; sus resúmenes permanecen desactivados.
- `Article`: enlace original, URL canónica opcional, GUID, huella para deduplicación, título, resumen permitido, idioma, fechas, feed y categorías. Hay restricciones de unicidad para enlace original, URL canónica no vacía y GUID no vacío dentro del feed. La huella tiene índice y se calcula durante la ingesta.
- `UserPreference`: relación uno a uno con el usuario integrado de Django y sus categorías preferidas.

La migración inicial está en `news/migrations/0001_initial.py`. Una segunda migración incorpora las cinco categorías acordadas. La tercera agrega los encabezados HTTP para consultas condicionales y la cuarta carga los feeds de Clarín Tecnología, EL PAÍS Tecnología y MIT News sobre IA. La activación se controla desde la administración. No se guardan artículos completos ni imágenes.

La ingesta es un comando de Django (`python manage.py ingest_feeds`) que consulta únicamente feeds activos. Descarga hasta 2 MB por feed con un tiempo de espera de 15 segundos, interpreta RSS/Atom, exige título, URL HTTP(S) y fecha de publicación y conserva idioma. Clasifica cada noticia con las etiquetas de su entrada RSS que coinciden con la lista revisada de `news/category_aliases.py`. Normaliza tildes, mayúsculas y espacios, pero exige coincidencia exacta del nombre; no infiere temas por palabras del titular. Cuando la entrada no incluye etiquetas, usa las categorías configuradas en su feed como respaldo. Si incluye etiquetas pero ninguna está aprobada, deja la noticia sin categoría. Esto permite usar feeds generales con el respaldo vacío y excluir etiquetas no revisadas. Omite noticias publicadas hace más de 60 días. Sólo guarda un resumen cuando `show_summary` está habilitado y el texto limpio tiene hasta 600 caracteres; en los tres feeds iniciales ese permiso está desactivado. El comando acepta `--refresh` para volver a descargar y reclasificar artículos ya guardados, aunque el servidor haya indicado que el feed no cambió.

Para evitar duplicados exactos, busca primero el GUID dentro del feed y luego la URL original y una URL normalizada. La normalización elimina fragmentos y parámetros de seguimiento conocidos, pero conserva intacto el enlace que recibirá el usuario. Una huella SHA-256 de esa URL sirve de respaldo para registros antiguos sin URL normalizada; no agrupa artículos diferentes sobre un mismo hecho. Las restricciones de unicidad en PostgreSQL refuerzan este control. Los encabezados `ETag` y `Last-Modified` permiten responder a HTTP 304 sin volver a procesar un feed sin cambios.

El registro usa `UserCreationForm`, el ingreso y la salida usan las vistas incluidas en Django y la página de preferencias usa un `ModelForm`. Cada usuario sólo modifica el registro `UserPreference` asociado a su cuenta. El cierre de sesión se envía por POST con protección CSRF. Esta implementación sigue la [documentación oficial de autenticación de Django](https://docs.djangoproject.com/en/5.2/topics/auth/default/) y no añade servicios ni dependencias.

La página `/noticias/` requiere inicio de sesión y consulta las categorías de `UserPreference` del usuario actual. Presenta hasta diez artículos recientes por categoría, ordenados por fecha de publicación, de feeds activos. Cada titular enlaza directamente al medio y muestra fuente, fecha e idioma; sólo muestra un resumen si la ingesta lo guardó conforme a la política del feed. La primera noticia de cada columna se indica como «Más reciente»: todavía no se calcula relevancia ni se agrupan coberturas. Si no hay categorías elegidas o una categoría no tiene artículos, la página muestra un estado vacío con acceso a las preferencias. El acceso inicial de una cuenta autenticada y el destino tras ingresar conducen a esta página. No se añade una API ni una dependencia de interfaz.

### Revisión de las herramientas incorporadas

Se eligió [Django 5.2 LTS](https://docs.djangoproject.com/en/5.2/releases/5.2/) porque soporta Python 3.13, trae autenticación y administración, y usa licencia BSD. Su [soporte de PostgreSQL](https://docs.djangoproject.com/en/5.2/ref/databases/) recomienda psycopg 3. Se fijaron versiones en `requirements.txt` para reproducir el entorno local.

[psycopg 3](https://www.psycopg.org/psycopg3/docs/basic/install.html) conecta Django con PostgreSQL y mantiene licencia LGPL 3. Su repositorio [tiene actividad](https://github.com/psycopg/psycopg); se revisó un [fallo reportado en Windows para una versión anterior](https://github.com/psycopg/psycopg/issues/1088), por lo que se instaló y comprobó la versión fijada en el entorno local. [python-dotenv](https://github.com/theskumar/python-dotenv), con licencia BSD 3 y mantenimiento activo, permite leer el archivo local `.env`. Como puede [no avisar cuando falta ese archivo](https://github.com/theskumar/python-dotenv/issues/631), Django exige explícitamente `DJANGO_SECRET_KEY` al iniciar.

La imagen oficial [PostgreSQL 17](https://hub.docker.com/_/postgres) se usa sólo para desarrollo; el volumen de [Docker Compose](https://docs.docker.com/reference/compose-file/volumes/) conserva los datos locales. PostgreSQL tiene [licencia permisiva](https://www.postgresql.org/about/licence/) y [Docker Desktop permite uso educativo gratuito](https://docs.docker.com/subscription-billing/desktop-license/). La contraseña se pasa desde `.env`, que Git ignora. Antes de una publicación se revisarán permisos y límites del proveedor elegido.

Como referencia de proyectos comparables activos se revisaron [django-planet](https://github.com/matagus/django-planet) y [django-feed-reader](https://github.com/xurble/django-feed-reader), que usan modelos y comandos de Django para agregación de feeds. Esta base sigue ese patrón sencillo, sin introducir una cola de tareas ni otro servicio de aplicación.

Para leer RSS se incorporó [feedparser 6.0.14](https://feedparser.readthedocs.io/en/stable/), compatible con Python 3.13, con [licencia BSD-2-Clause](https://github.com/kurtmckee/feedparser/blob/main/pyproject.toml) y una [versión publicada en julio de 2026](https://feedparser.readthedocs.io/en/latest/changelog/). Permite tratar de forma uniforme RSS y Atom. Su historial registra fallos de análisis corregidos en versiones recientes; además, un XML mal formado puede producir `bozo=1`, por lo que el comando rechaza ese resultado. La descarga se hace con la biblioteca estándar de Python para controlar tamaño, tiempo de espera y solicitudes condicionales. Se mantuvieron como referencias comparables django-planet y django-feed-reader; no se agregó un framework de tareas.

Para la categorización se revisó la [referencia oficial de `entries[i].tags`](https://feedparser.readthedocs.io/en/stable/reference-entry-tags.html): tanto RSS como Atom exponen el nombre de categoría en `term`, y un elemento puede traer varias etiquetas. Se comparó con los lectores activos [django-planet](https://github.com/matagus/django-planet) y [django-feed-reader](https://github.com/xurble/django-feed-reader), que separan lectura de feeds y almacenamiento de entradas. La solución conserva esa separación y agrega un diccionario local de equivalencias exactas, fácil de inspeccionar y modificar, sin dependencia ni servicio nuevos. Su límite deliberado es que una etiqueta desconocida no clasifica el artículo hasta que el equipo la revise y la incorpore; se evita así asignar temas por coincidencias parciales o por nombres de personas y empresas que los feeds también publican como etiquetas.

## Datos y conservación

Se guardarán únicamente metadatos necesarios:

- usuario y sus preferencias de categorías;
- fuente y feed de origen;
- GUID externo y URL canónica;
- título y resumen permitido;
- fecha de publicación y fecha de captura;
- idioma y categorías;
- metadatos técnicos mínimos para diagnóstico.

Política inicial:

- Noticias normalizadas: 60 días.
- No almacenar artículos completos ni imágenes.
- PostgreSQL almacena metadatos y enlaces, no contenido editorial completo.

Las políticas de resumen se definen por fuente. La existencia de un RSS no implica permiso para reutilizar todos sus campos.

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
11. El proveedor de alojamiento y de base de datos pública se decidirá tras evaluar persistencia y límites gratuitos.
12. Las decisiones nuevas o modificadas deben quedar registradas en este documento.
