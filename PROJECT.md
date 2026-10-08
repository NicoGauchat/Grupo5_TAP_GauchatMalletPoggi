# Definición del proyecto

## Objetivo

Construir una aplicación web universitaria que reúna noticias recientes de fuentes confiables y diversas, las normalice y permita consultarlas por categoría, fuente e idioma. La aplicación debe atribuir cada contenido y dirigir al usuario al artículo original.

El proyecto debe mantenerse dentro de los planes gratuitos. No se incorporará una dependencia que exija pago para desarrollar, desplegar o ejecutar el MVP.

## Alcance

### Primera entrega

- Ingesta periódica de una selección pequeña de feeds RSS activos.
- Modelo común para fuentes y noticias en PostgreSQL.
- Deduplicación exacta por GUID, URL canónica y respaldo mediante hash.
- Categorización básica en tecnología, IA, ciencia, economía y geopolítica.
- Feed con título, resumen cuando esté permitido, fuente, fecha, idioma y enlace original.
- Filtros básicos por categoría, fuente e idioma.
- Miniaturas opcionales y reemplazo visual cuando no haya una imagen utilizable.

### Entrega posterior

- Agrupamiento de artículos que cubren el mismo acontecimiento.
- Embeddings multilingües y `pgvector`, si la evaluación demuestra que mejoran el agrupamiento.
- Clustering dentro de una ventana temporal y validación de umbrales.
- GDELT DOC 2.0 como complemento para descubrir cobertura adicional.

## Fuera de alcance inicial

- Almacenar o republicar artículos completos.
- Scraping de páginas sin autorización.
- Traducción automática de contenido ajeno.
- Recomendaciones complejas, entrenamiento de modelos propios o clustering semántico en la primera entrega.
- Servicios pagos o planes gratuitos que no permitan el uso previsto en producción.

## Arquitectura acordada

```text
RSS configurados
      ↓
GitHub Actions ejecuta la ingesta
      ↓
TypeScript obtiene, valida y normaliza
      ↓
Deduplicación y categorización básica
      ↓
Supabase PostgreSQL + Supabase Storage
      ↓
Next.js consulta y presenta el feed
```

GDELT seguirá el mismo modelo normalizado cuando se incorpore, pero no será la fuente principal. La aplicación debe continuar funcionando si GDELT no responde o limita consultas.

## Tecnologías

| Área | Decisión | Motivo |
|---|---|---|
| Lenguaje | TypeScript | Compartir tipos y lógica entre frontend, backend e ingesta |
| Aplicación | Next.js | Una sola base de código para interfaz y endpoints |
| Base de datos | Supabase PostgreSQL | PostgreSQL administrado con plan gratuito |
| Archivos | Supabase Storage | Mantener las miniaturas fuera de PostgreSQL |
| Imágenes | Sharp | Redimensionar, quitar metadatos y convertir a WebP |
| Automatización | GitHub Actions | Ejecutar la ingesta programada sin servidor dedicado |

## Datos y conservación

Se guardarán únicamente metadatos necesarios:

- fuente y feed de origen;
- GUID externo y URL canónica;
- título y resumen permitido;
- fecha de publicación y fecha de captura;
- idioma y categorías;
- URL de imagen original y, si corresponde, URL de miniatura temporal;
- metadatos técnicos mínimos para diagnóstico.

Política inicial:

- Noticias normalizadas: 60 días.
- Miniaturas almacenadas: entre 10 y 14 días.
- Formato objetivo de miniatura: WebP, aproximadamente 480 × 270 px, calidad 35–45 y hasta 100 KB cuando sea posible.
- Nunca guardar imágenes dentro de PostgreSQL.
- Si se alcanza el límite de almacenamiento, dejar de generar miniaturas antes de afectar la ingesta.

Las políticas de resumen e imagen se definen por fuente. La existencia de un RSS no implica permiso para republicar cualquier contenido.

## Decisiones vigentes

1. RSS es la fuente principal del MVP.
2. PostgreSQL almacena metadatos y enlaces, no artículos completos.
3. La categorización básica forma parte de la primera entrega.
4. El agrupamiento por embeddings y clustering se deja para una entrega posterior.
5. GDELT se integra después como radar de cobertura y nunca como dependencia única.
6. No se incorporan servicios pagos.
7. Las decisiones nuevas o modificadas deben quedar registradas en este documento.
