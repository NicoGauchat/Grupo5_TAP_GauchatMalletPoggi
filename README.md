# Sitio Noticias

Aplicación web universitaria para reunir noticias de fuentes seleccionadas, normalizarlas y ofrecer un feed filtrable por tema, fuente e idioma. El proyecto prioriza RSS, atribuye siempre al medio original y debe poder funcionar sin servicios pagos.

## Funcionalidades previstas

- Recolectar noticias desde feeds RSS configurables.
- Normalizar título, resumen permitido, fuente, fecha, idioma, enlace e imagen opcional.
- Clasificar por tecnología, inteligencia artificial, ciencia, economía y geopolítica.
- Evitar duplicados exactos por GUID y URL canónica.
- Mostrar tarjetas que enlacen al artículo original.
- Conservar noticias e imágenes sólo durante el período definido en el proyecto.
- Incorporar posteriormente agrupamiento de coberturas y GDELT como complemento.

## Stack acordado

- TypeScript y Next.js para la aplicación web y el backend.
- Supabase Free para PostgreSQL y almacenamiento de miniaturas.
- Sharp para generar miniaturas WebP livianas.
- GitHub Actions para ejecutar la ingesta periódica.

## Arquitectura resumida

```text
Feeds RSS
    ↓
Ingesta y normalización
    ↓
PostgreSQL + Storage
    ↓
Aplicación Next.js
```

GDELT y el agrupamiento semántico pertenecen a una etapa posterior y no son dependencias de la primera entrega.

## Estado

El repositorio se encuentra en la etapa de documentación y preparación. Todavía no existe una aplicación instalable ni comandos de desarrollo. El próximo paso vigente se mantiene en [STATUS.md](./STATUS.md).

## Documentación

- [PROJECT.md](./PROJECT.md): alcance, arquitectura y decisiones del proyecto.
- [STATUS.md](./STATUS.md): estado operativo y único próximo paso.
- [SOURCES.md](./SOURCES.md): feeds investigados y políticas por fuente.
- [AGENTS.md](./AGENTS.md): reglas de trabajo y actualización documental.
- [.env.example](./.env.example): variables previstas, sin credenciales reales.
