# Estado del proyecto

**Última actualización:** 2026-10-13
**Objetivo actual:** rediseño integral y paginación completados; preparar la validación remota de la entrega 1.

## Último paso completado

Se implementó la identidad editorial en inicio, ingreso, registro, preferencias y noticias: fuentes locales, azul intenso, marca tipográfica y controles compartidos. Inicio e ingreso/registro usan composiciones más expresivas; noticias conserva las categorías en columnas y agrega paginación independiente de diez artículos. Los filtros y las páginas restantes se conservan en los enlaces; aplicar o limpiar reinicia las páginas. Se mantuvieron textos de acciones y recorridos.

Se preservaron las correcciones del bloque anterior: pruebas reproducibles, `ArticleOrigin` y migración de noticias existentes, unión de categorías por origen y diez consultas RSS previstas por día. No se modificaron nuevamente la ingesta, los modelos ni su configuración.

La corrección de Gunicorn 26.2.0 ya está integrada en `main` mediante el commit `6a7b61d`; no queda pendiente integrarla. La autenticación actual de Django se conserva, sin cambios de registro, ingreso, sesiones, preferencias ni permisos.

## Próximo paso

Validar el despliegue en Render con PostgreSQL en Supabase y activar la ingesta programada.

## Completado

- Django, PostgreSQL local con Docker Compose y arquitectura anterior conservada como referencia histórica.
- Registro, ingreso, salida y preferencias individuales, sin cambios en este bloque.
- Ocho categorías y once feeds activos precargados mediante las seis migraciones anteriores, sin cambiar fuentes, permisos ni equivalencias.
- Ingesta RSS/Atom, deduplicación por GUID dentro del feed y URL canónica, y solicitudes condicionales.
- Orígenes por noticia y feed con categorías independientes, unión sin duplicados y conservación del feed original para atribución y filtros.
- `--refresh` reemplaza el aporte del origen consultado sin borrar las categorías aportadas por los demás.
- Migración `0007_article_origins`: conserva los metadatos existentes y copia feed, GUID y categorías al origen inicial.
- Página personalizada con noticias por categoría, filtros de fuente e idioma y conservación de 14 días.
- Paginación real con `page_<slug>`, diez noticias por sección, totales completos y navegación sin JavaScript; «Más reciente» sólo en la primera página.
- Rediseño de las cinco páginas, con fuentes Archivo y Source Sans 3 locales y licencias OFL, cuatro/dos/una columnas de noticias y formularios con campos y validaciones existentes.
- Foco visible, enlace para saltar al contenido, controles de al menos 44 px, movimiento reducido y errores y estados vacíos conservados.
- Workflow preparado todos los días a las 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00 y 00:00 en `America/Argentina/Buenos_Aires`; ejecución manual disponible fuera de la franja.
- Configuración de Render Free, Gunicorn, WhiteNoise y conexión prevista a Supabase Session pooler con SSL.
- README, PROJECT, SOURCES y STATUS sincronizados. La comprobación RSS del 13/10/2026 sólo conserva evidencia agregada, sin noticias ni XML en el repositorio.

## Pendiente y limitaciones

- Aplicar y verificar la nueva migración en PostgreSQL real; el bloqueo de filas se usa en la ingesta, pero SQLite no permite comprobar su comportamiento real en PostgreSQL.
- Verificar el build de Render, conexión a Supabase, aplicación publicada y persistencia; la configuración preparada no acredita un despliegue correcto.
- Configurar o comprobar credenciales en los paneles y `NEWS_INGESTION_ENABLED`, y verificar la primera ejecución manual y programada en Actions. Este bloque no carga secretos ni activa servicios remotos.
- Los horarios de Actions son previstos: puede haber retrasos u omisiones. La pausa de 00:00 a 06:00 y los feeds cortos pueden causar pérdidas de entradas; las consultas cada dos horas no garantizan captura exhaustiva.
- Sigue pendiente evaluar el ruido de Clarín Mundo y Economía y la cobertura de ciencia. No se incorporaron fuentes ni se cambiaron los criterios de clasificación en esta tarea.
- No se guardan artículos completos ni imágenes; los once feeds conservan los resúmenes deshabilitados.

## Bloqueos

No hay bloqueos conocidos para validar el despliegue. La comprobación remota requiere acceso a las cuentas y credenciales configuradas fuera del repositorio.

## Última verificación

- Suite completa: **31 pruebas aprobadas**, sin `.env`, Docker ni `collectstatic`; conserva las 24 anteriores y añade siete regresiones de paginación con escenarios de 0, 10, 11 y 23 artículos, independencia, enlaces, filtros, límites, orden y ausencia de duplicados.
- `manage.py check --settings=config.test_settings`: sin problemas.
- `makemigrations --check --dry-run --settings=config.test_settings`: sin cambios pendientes de modelo.
- `pip check`: sin dependencias incompatibles; no se agregaron ni actualizaron dependencias.
- Cron y zona horaria verificados: diez horarios diarios acordados, ejecución manual y control de activación conservados, limpieza antes de la ingesta.
- Navegador Microsoft Edge: las cinco páginas devolvieron HTTP 200 a 375, 768, 1024 y 1440 px; sin desbordamiento horizontal, campos sin etiqueta ni controles de formulario menores de 44 px. Se inspeccionaron capturas de escritorio y móvil, títulos extensos, errores de ingreso/registro/filtros y estados vacíos con datos sintéticos externos al repositorio.
- Recorridos comprobados en navegador: ingreso válido e inválido, `next`, registro válido e inválido, preferencias, confirmación de guardado y salida por POST; paginación con filtros, reinicio, recarga e historial. No cambió la autenticación.
- Texto inspeccionado con contraste mínimo de 5,94:1; foco visible, acceso al contenido por teclado y casillas operables con espacio. Movimiento reducido elimina transiciones. Fuentes locales cargadas y respaldo sin desbordamiento al bloquear su descarga.
- Reflujo equivalente al 200 % comprobado mediante viewport de 720 × 500 CSS px y escala de dispositivo 2, para las cinco páginas. Es emulación en Edge, no una prueba en dispositivos físicos ni una certificación de accesibilidad.
- `collectstatic` comprobado con el almacenamiento de manifiesto y compresión de WhiteNoise, usando un directorio temporal: CSS y ambas fuentes obtuvieron nombres versionados y archivos gzip, sin tocar configuración ni estáticos del repositorio.
- Configuración de producción y pruebas, URLs, formularios, modelos, ingesta, workflow y migración anterior conservados respecto del inicio de este bloque; el cambio funcional de backend se limita a `news_feed`. Se compararon los textos de enlaces y botones existentes sin faltantes.
- SOURCES y `.env.example` no requirieron cambios: no se modificaron feeds, permisos ni variables. README y PROJECT registran la identidad y el contrato de paginación; la arquitectura histórica permanece intacta.
- Diff revisado sin errores de espacios, secretos, noticias reales ni artefactos de ejecución incorporados; fuentes y licencias son assets deliberados del sitio.
- Las migraciones se probaron únicamente con bases SQLite de prueba. El despliegue y la activación remota están pendientes.
