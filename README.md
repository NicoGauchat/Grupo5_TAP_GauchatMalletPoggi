# Sitio Noticias

Aplicación web universitaria para reunir noticias de fuentes seleccionadas, organizarlas por categoría y permitir que cada usuario configure sus temas de interés. Prioriza RSS, atribuye siempre al medio original y muestra varias fuentes.

## Ya implementado

- Registro e inicio de sesión con usuarios de Django.
- Preferencias individuales para las cinco categorías iniciales.
- Modelos y administración de categorías, fuentes, feeds y artículos.

## Funcionalidades previstas

- Recolectar noticias desde feeds RSS configurables.
- Guardar título, resumen permitido, fuente, fecha, idioma, enlace y categorías.
- Clasificar por tecnología, inteligencia artificial, ciencia, economía y geopolítica. Deportes queda para una etapa posterior.
- Evitar duplicados exactos por GUID y URL canónica.
- Mostrar noticias de distintas fuentes y enlazar al artículo original.
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

Ya existe el proyecto Django, la configuración de PostgreSQL, la migración inicial y las páginas de registro, ingreso y preferencias. La ingesta RSS y el feed de noticias todavía no están implementados. La administración de Django está disponible en `/admin/`.

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
python manage.py createsuperuser
python manage.py runserver
```

Abrir `http://127.0.0.1:8000/` para crear una cuenta y elegir categorías, o `/admin/` para gestionar fuentes y modelos. `createsuperuser` solicita usuario y contraseña para la administración. Para detener sólo la base de datos, ejecutar `docker compose down`. El volumen conserva los datos entre reinicios.

## Documentación

- [PROJECT.md](./PROJECT.md): alcance, arquitectura y decisiones vigentes.
- [ARCHITECTURE-LEGACY.md](./ARCHITECTURE-LEGACY.md): copia de referencia de la arquitectura anterior de TypeScript, Next.js y Supabase.
- [STATUS.md](./STATUS.md): estado operativo y único próximo paso.
- [SOURCES.md](./SOURCES.md): feeds investigados y políticas por fuente.
- [AGENTS.md](./AGENTS.md): reglas de trabajo y actualización documental.
- [.env.example](./.env.example): variables previstas, sin credenciales reales.
