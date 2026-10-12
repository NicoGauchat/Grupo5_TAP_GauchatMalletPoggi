# Estado del proyecto

**Última actualización:** 2026-10-12
**Objetivo actual:** integrar los avances de fuentes y categorías con los filtros y el mantenimiento periódico.

## Último paso completado

Se integraron los cambios de ambas ramas: ocho categorías, once feeds activos, presentación panorámica con columnas ordenadas por cantidad de noticias y filtros por fuente e idioma. Se incorporaron la ventana común de 60 días, el comando de limpieza y el workflow horario de GitHub Actions que faltaban en el commit remoto.

## Próximo paso

Configurar PostgreSQL público persistente en un plan gratuito permitido para activar y verificar el workflow de ingesta.

## Completado

- Django y PostgreSQL local con Docker Compose; arquitectura anterior preservada.
- Registro, ingreso, salida y preferencias individuales.
- Ocho categorías y once feeds RSS activos precargados mediante migraciones.
- Ingesta RSS/Atom, clasificación por etiquetas aprobadas, deduplicación exacta y solicitudes condicionales.
- Página personalizada con hasta diez noticias por categoría, columnas ordenadas por cantidad y filtros combinables por fuente e idioma.
- Limpieza de noticias de más de 60 días con vista previa; ingesta y consulta usan la misma ventana.
- Workflow horario y manual preparado, inactivo hasta configurar base pública y secretos.
- Los once feeds activos no guardan resúmenes, imágenes ni artículos completos.

## Pendiente

- Activar y verificar la automatización con una base PostgreSQL pública y persistente.
- Elegir alojamiento público para Django con un plan gratuito permitido.
- Revisar el ruido de Clarín Mundo y Economía y evaluar más fuentes para mercados argentinos.

## Bloqueos

- La ejecución real del workflow requiere una base pública y secretos de Actions aún no configurados.

## Última verificación

- La rama local y la remota partían de `41d23c7`; la integración preservó ambas líneas de cambios.
- El commit remoto referenciaba `news.retention`, `purge_old_articles`, `config.test_settings` y el workflow sin incluir esos archivos; se incorporaron durante la integración.
- `SOURCES.md` no requirió cambios en esta integración: no cambiaron feeds, estados ni políticas de uso.
- `python manage.py check`: sin problemas.
- `python manage.py makemigrations --check --dry-run`: sin cambios de esquema. La comprobación del historial de la base local emitió una advertencia de conexión agotada porque PostgreSQL no respondió.
- `check` y `makemigrations --check --dry-run` con `config.test_settings`: sin problemas y sin cambios de esquema.
