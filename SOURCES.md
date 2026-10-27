# Fuentes de noticias

## Criterios y leyenda

Este registro separa disponibilidad técnica de permiso de reutilización. Un feed accesible no autoriza a copiar el artículo completo ni necesariamente sus imágenes.

El relevamiento general se realizó el **29 de septiembre de 2026**. Los feeds activados y sus etiquetas se comprobaron el **11 de octubre de 2026**; la actividad y capacidad se revisaron nuevamente el **13 de octubre de 2026**, según el snapshot agregado más abajo. La frecuencia depende de cada medio y puede variar.

Campos:

- `T`: título.
- `R`: resumen o descripción.
- `F`: fecha de publicación.
- `E`: enlace original.
- `I`: imagen o referencia de imagen.

## Feeds activos

### Revisión y ampliación de bajadas (27/10/2026, posterior al pedido de agrupamiento)

El usuario pidió utilizar la misma descripción guardada en resúmenes y agrupamiento y decidió avanzar donde no se encontrara una prohibición expresa, sin confundir silencio con una licencia otorgada. Se habilita mediante control manual una lista cerrada de feeds ya existentes: elDiario.es, NASA Technology y Los Andes Política/Economía/Sociedad. No se agregan medios, feeds, imágenes, proveedores ni scraping. Se mantienen 600 caracteres limpios como máximo, descartando campos largos completos; para elDiario.es se conserva exclusivamente la excepción de primera entradilla ya revisada. La ingesta forzada actualiza bajadas existentes desde el feed original, y la ingesta normal mantiene los controles. La revocación de `show_summary` excluye el campo de las llamadas siguientes; no se reactivan feeds pausados.

- **NASA:** revisados su [RSS](https://www.nasa.gov/technology/feed/) y sus [directrices, sección Artificial Intelligence Applications](https://www.nasa.gov/nasa-brand-center/images-and-media/). La muestra en memoria contiene diez bajadas de 100–396 caracteres limpios, sin guardar textos o XML reales en el repositorio. Se excluyen señales de copyright/agencias de terceros y se conserva el enlace a las directrices en la fuente. La síntesis de salida se atribuye a la IA, reserva espacio y agrega de forma determinista: «Síntesis generada por IA con material de NASA; NASA no la revisó ni responde por su exactitud.» Se rechazan textos que no dejan espacio o atribuyen el resultado «según NASA»/«according to NASA». No se implica aprobación ni aval. El agrupamiento recibe bajadas en sus solicitudes existentes; no genera titulares fusionados.
- **Los Andes:** su [directorio RSS](https://www.losandes.com.ar/contenidos/rss.html) ofrece incluir/publicar sus noticias en sitios o agregadores; los [términos](https://www.losandes.com.ar/terminos) conservan copyright general y no establecen una prohibición específica de IA en lo consultado. Por decisión expresa del usuario se habilitan las bajadas breves de los tres RSS existentes para el proyecto educativo, conservando titular, autor recibido, medio y enlace. Esta es una decisión de uso del proyecto, no una autorización expresa de transformación concedida por el medio. Se descartan señales de copyright/agencias de terceros; no se extraen páginas ni se recortan cuerpos largos.
- **MIT News:** [términos oficiales](https://news.mit.edu/terms-of-use) permiten sindicación con titular, subtítulo, autor y enlace originales, además de una nota y enlace específicos de republicación. Sus cincuenta entradas inspeccionadas en memoria tenían bajadas breves y autor. La activación de descripciones queda pendiente de implementar/verificar esa presentación de atribución antes de ampliarla a producción.
- **Clarín:** sus [condiciones RSS](https://www.clarin.com/filer/RSS/terminos_condiciones.html) autorizan títulos/enlaces y restringen modificaciones/reutilizaciones del servicio; no es simplemente ausencia de la palabra IA. No se habilitan bajadas.
- **Perfil:** se conserva la restricción de títulos/enlaces previamente documentada. Sus páginas oficiales de RSS y términos no se pudieron volver a abrir con el navegador de investigación; no se amplía su permiso por esa falta de acceso.
- **EL PAÍS:** el [aviso legal vigente, propiedad intelectual](https://elpais.com/info/aviso-legal/) contiene oposición expresa a cualquier utilización de sus contenidos con tecnologías de IA. Se corrige la evaluación anterior: no se habilitan descripciones y se excluyen sus artículos de las cuatro etapas IA (también titulares), aunque los permisos operativos antiguos sigan activos. La activación revisada `--source all` retira `allow_ai_grouping`, `allow_ai_briefing` y `show_summary` de sus feeds, preservando ingesta, enlaces y clasificación por reglas. No se borra material histórico ni se afirma que las decisiones de uso anteriores equivalían a una licencia del medio.

Los apartados siguientes registran el historial anterior a esta revisión y sus permisos previos, que quedan reemplazados en los puntos indicados arriba.

### Descripciones autorizadas para agrupamiento (27/10/2026)

Por pedido del usuario se permite usar también la bajada RSS guardada para identificar el mismo acontecimiento en propuesta y auditoría, tanto de noticias nuevas como de sus referencias. Se requieren feed activo, `allow_ai_grouping` y `show_summary`; se conserva la independencia de `allow_ai_briefing`. No se habilitan feeds ni se amplía el material que la ingesta puede guardar. Actualmente sólo elDiario.es tiene descripciones activadas. Se reutiliza `permitted_summary`: limpieza de HTML, máximo de 600 caracteres sin recortar campos largos y controles específicos de autor/licencia/señales de terceros para elDiario.es. El título sigue funcionando sin descripción. No se descargan artículos ni se envían URLs, usuarios o preferencias. Gemini y el respaldo Groq reciben los mismos datos autorizados en sus llamadas existentes; no se añade un proveedor.

Se reconsultaron el [aviso legal de elDiario.es, apartado 3](https://www.eldiario.es/aviso-legal-eldiario-es/) y [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.es): se conserva el uso educativo no comercial, la atribución y el filtro conservador de contenido ajeno ya documentado. Esta extensión de entrada del agrupador reutiliza la decisión de entradillas revisada el 26/10; los apartados históricos que indican «sólo titulares» describen el contrato anterior. No se habilitan descripciones de Clarín, EL PAÍS, MIT, NASA, Los Andes o Perfil por analogía.

### Activación revisada de elDiario.es (26/10/2026)

El usuario pidió proceder con la activación. Se habilita explícitamente el RSS existente [elDiario.es Internacional](https://www.eldiario.es/rss/internacional/) para síntesis y entradilla. Su [aviso legal, apartado 3](https://www.eldiario.es/aviso-legal-eldiario-es/) y la [licencia CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.es) permiten adaptación no comercial con crédito, licencia e indicación del cambio. Se conserva autor público, medio, titular original, enlace y vínculo a la licencia; la síntesis se rotula IA. La excepción no se aplica a contenido de terceros: se excluyen entradas sin autor o con señales identificadas de agencias/Guardian en autoría, derechos o texto. Ese filtro conservador no demuestra por sí solo la titularidad de cada entrada; ante una revocación o detección de material ajeno se deben retirar sus permisos.

La consulta aislada del RSS, sólo en memoria, encontró 26 entradas con textos de 1846–13767 caracteres; por ello no se almacenan sus campos completos. Su primera entradilla no vacía tenía entre 80 y 373 caracteres en esa muestra. Se incorpora sólo ese primer párrafo, siempre hasta 600 caracteres y con autor/licencia esperados, saltando párrafos vacíos de imagen; si el primer párrafo textual supera el límite, se descarta sin buscar uno más conveniente. Catorce entradas pasaron los controles de autoría/señales de terceros y seis estaban dentro de las últimas 24 horas en la comprobación local. No se guardaron XML, artículos ni ejemplos reales en el repositorio. Es una excepción específica al descarte general de campos largos, permitida por la licencia revisada, no una habilitación para recortar material de otros medios.

La activación remota **40426423602** terminó correctamente: revisó 26 noticias existentes y dejó seis entradillas autorizadas disponibles dentro de 24 horas. La generación posterior conservó las diez referencias anteriores y utilizó cero entradillas: las noticias elegidas pertenecían a otros feeds. Se acredita disponibilidad de contenido permitido, no que todos los resúmenes actuales ya se basen en descripciones.

La activación usa un comando explícito y un control manual de Actions, sin nueva migración. Sólo modifica el feed ya activo y con licencia configurada; otros catorce feeds de la ampliación siguen sin síntesis y todas las demás fuentes mantienen descripciones deshabilitadas. MIT publica condiciones específicas de atribución, NASA agrega condiciones para salidas IA y Clarín limita títulos/enlaces; no se habilitan por analogía. ElDiario.es sigue sin fotografías y no se modifica agrupamiento ni clasificación. La ingesta puede actualizar las entradillas ya existentes o retirarlas cuando se revoque `show_summary`, sin reemplazar contenido del feed original desde otra fuente. Los apartados posteriores conservan el historial previo a esta activación.

### Descripciones RSS como base de la síntesis (26/10/2026)

El usuario pidió que la síntesis tenga más contenido que una reformulación del título. Se preparó el uso de `Article.summary`, exclusivamente cuando la fuente tiene habilitados los dos controles existentes: `show_summary` y `allow_ai_briefing`. Se usa sólo la bajada RSS guardada, limpia y de hasta 600 caracteres; un campo mayor se descarta entero para no guardar/enviar artículos completos. No se activa ningún feed ni se descargan páginas. La selección vigente se incluye en las comparaciones sólo mientras cumpla ventana de 24 horas, categoría y permisos; ampliar la longitud no amplía material disponible ni permite inventar contexto.

Se volvieron a consultar las [condiciones RSS de Clarín](https://www.clarin.com/filer/RSS/terminos_condiciones.html), [RSS de EL PAÍS](https://elpais.com/info/rss/), [RSS de Los Andes](https://www.losandes.com.ar/contenidos/rss.html), [términos de MIT News](https://news.mit.edu/terms-of-use) y [aviso legal de elDiario.es](https://www.eldiario.es/aviso-legal-eldiario-es/). No se encontró una autorización común para ampliar automáticamente todos los feeds a descripciones. Clarín limita su permiso a titulares/enlaces; EL PAÍS no resuelve en su directorio la transformación de bajadas. MIT exige atribución específica para republicar historias y elDiario.es declara CC BY-NC con excepciones de contenido ajeno. Antes de activar hay que resolver el uso y atribución de cada fuente y volver a ingerir sus RSS; los controles actuales siguen deshabilitados para descripciones. Las secciones siguientes conservan el contrato de titulares utilizado mientras no se active ese permiso. El soporte técnico no acredita que existan descripciones en producción ni que se haya autorizado leer artículos completos.

### Síntesis IA por categoría (26/10/2026)

La nueva presentación redacta mediante Gemini una síntesis de la noticia más importante de cada categoría que tenga titulares habilitados, con un único artículo de referencia y enlace directo al medio. Se seleccionan candidatos de las últimas 24 horas con `allow_ai_briefing=True`; los quince feeds agregados en `0018` siguen deshabilitados para síntesis y no se amplía su permiso por tener categorías o permitir agrupamiento. Una categoría sin material autorizado muestra ese estado, sin reutilizar contenido de otro feed ni generar un resumen de relleno.

Se transmiten exclusivamente ID, titular, medio, fecha, idioma y nombres/slugs de sus categorías públicas (unión de reglas y clasificación IA); no se envían cuerpos, resúmenes RSS, URLs, preferencias o datos personales. Cada síntesis usa una referencia de su propia categoría, conserva el titular original junto al enlace y muestra autoría/licencia cuando corresponden. El proveedor no puede inventar el destino del enlace. La caducidad o revocación de la referencia retira sólo esa síntesis. No se extraen contenidos de las páginas de noticias ni se modifican feeds, imágenes, licencias o permisos de uso.

El desplegable «Ver fuentes» de cada síntesis también permite abrir otras coberturas del mismo grupo verificado, de feeds activos con `allow_ai_grouping=True` y publicadas dentro de las últimas 24 horas. Se ofrece una opción por medio, manteniendo titular, enlace y autoría/licencia aplicables. Se distingue la referencia usada como «Base de la síntesis» de las alternativas: esas coberturas no se envían a Gemini ni se usan para reescribir el resumen. Por ello un feed con síntesis deshabilitada puede figurar como enlace de cobertura, sin extender su permiso `allow_ai_briefing`. Compartir categoría no habilita la asociación y los grupos pendientes no agregan fuentes. No se modifican políticas ni permisos de los feeds.

La comparación controlada entre Gemini 3.1 Flash-Lite y Gemini 3.5 Flash-Lite mantiene el mismo proveedor y los mismos campos autorizados. No amplía permisos de síntesis, agrupamiento, imágenes o resúmenes RSS ni incorpora otro destino para los titulares. La selección del modelo es explícita; no hay conmutación para eludir cuotas.

Por autorización expresa del usuario, resumen y agrupamiento pueden enviar los mismos titulares/metadatos permitidos a Groq como respaldo de Gemini cuando existe `GROQ_API_KEY`. OpenRouter quedó excluido por decisión posterior del usuario y no recibe solicitudes. No se envían cuerpos, resúmenes RSS, usuarios ni preferencias, ni se amplían feeds o permisos. Se conservan referencia y licencia del medio independientemente de quién produzca la respuesta. Groq mantiene su política de datos publicada. Se validan IDs y hechos antes de guardar, sin sustituirlos por resultados ficticios.

### Ampliación vigente del 25/10/2026

Por pedido del usuario, se prioriza cobertura argentina y se agregan fuentes de Estados Unidos y Europa. **Agência Brasil queda fuera**: no se incorpora su fuente, feeds ni equivalencias a la migración. `0018` agrega quince RSS a los once originales: **26 feeds activos precargados de ocho medios**. Los medios nuevos son Perfil (Argentina), NASA (Estados Unidos) y elDiario.es (España); además se amplían canales de Clarín, Los Andes y EL PAÍS. Las tres categorías nuevas son Salud, Medioambiente y Deportes.

Los quince RSS se comprobaron el 25/10/2026 con el lector de la aplicación: HTTP 200, RSS 2.0 válido, menos de 2 MB y publicaciones dentro de los últimos 14 días. La siguiente muestra registra cantidad recibida y entradas elegibles por fecha, incluidas las que ya existían por otro canal; no es una garantía de disponibilidad futura. Los datos se inspeccionaron en memoria y se importaron únicamente a PostgreSQL temporal de QA, fuera del repositorio.

| Medio / canal | URL | Idioma | Entradas / elegibles en 14 días | Categoría base |
|---|---|---|---|---|
| Clarín Deportes | https://www.clarin.com/rss/deportes/ | es | 10 / 10 | Deportes |
| Clarín Buena Vida | https://www.clarin.com/rss/buena-vida/ | es | 10 / 10 | Salud |
| Los Andes Sociedad | https://www.losandes.com.ar/rss/pages/sociedad.xml | es | 20 / 20 | Argentina |
| Perfil Política | https://www.perfil.com/feed/politica | es | 70 / 70 | Política argentina y Argentina |
| Perfil Salud | https://www.perfil.com/feed/salud | es | 70 / 18 | Salud |
| Perfil Deportes | https://www.perfil.com/feed/deportes | es | 70 / 70 | Deportes |
| Perfil Ciencia | https://www.perfil.com/feed/ciencia | es | 70 / 26 | Ciencia |
| Perfil Economía | https://www.perfil.com/feed/economia | es | 70 / 70 | Economía |
| Perfil Tecnología | https://www.perfil.com/feed/tecnologia | es | 70 / 9 | Tecnología |
| EL PAÍS Salud | https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/salud-y-bienestar/portada | es | 32 / 16 | Salud |
| EL PAÍS Clima y medio ambiente | https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/clima-y-medio-ambiente/portada | es | 20 / 11 | Medioambiente |
| EL PAÍS Deportes | https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/deportes/portada | es | 31 / 26 | Deportes |
| EL PAÍS Ciencia | https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/ciencia/portada | es | 40 / 17 | Ciencia |
| elDiario.es Internacional | https://www.eldiario.es/rss/internacional/ | es | 24 / 24 | Geopolítica |
| NASA Technology | https://www.nasa.gov/technology/feed/ | en | 10 / 7 | Tecnología; Ciencia/Medioambiente según etiquetas |

En la primera ingesta aislada de estos canales se crearon 396 artículos, se detectaron ocho duplicados y se omitieron 213 entradas fuera de la ventana; no se guardaron cuerpos ni XML. Tres noticias de Salud de EL PAÍS y otras de Perfil ya estaban en otros canales y conservaron su origen inicial. La categoría de respaldo se usa cuando no hay etiquetas; EL PAÍS usa equivalencias exactas de Salud, Salud pública, Salud mental, Medicina, Enfermedades, Medio ambiente, Cambio climático, Biodiversidad, Contaminación y Deportes, observadas en los RSS. NASA limita `Technology`, `Technology Research`, `Science & Research` y `Earth Science` a su canal. Los Andes Sociedad aplica su etiqueta de sección sólo en su URL.

El feed Internacional de elDiario.es tiene principalmente etiquetas de países/personas, sin categoría temática constante. Se incorpora como sección editorial curada de Geopolítica, sin convertir nombres de países o políticos en equivalencias globales. Como en Clarín Mundo, puede incluir sucesos internacionales que no sean geopolítica estricta. Los canales de salud/bienestar y sociedad también requieren medir ruido temático antes de refinar la selección; no se filtran por notoriedad de marcas ni se excluyen medios completos por ello.

### Permisos de la ampliación

- **Perfil:** su [directorio y condiciones RSS](https://www.perfil.com/canales-rss) conceden exhibición de titulares y enlaces en sitios propios, conservándolos y atribuyendo al medio. Se revisaron también sus [términos generales](https://www.perfil.com/terminos-privacidad). Se usan los canales publicados en ese directorio, sin cuerpos ni fotografías.
- **Clarín:** se reutilizan el [directorio RSS](https://www.clarin.com/rss.html) y sus [condiciones específicas](https://www.clarin.com/filer/RSS/terminos_condiciones.html), que permiten titulares/enlaces sin alteración. Los dos canales nuevos no heredan permiso para imágenes ni síntesis.
- **Los Andes:** se conserva la política de [RSS](https://www.losandes.com.ar/contenidos/rss.html) y [términos](https://www.losandes.com.ar/terminos) ya documentada: titular original con atribución y enlace; se agrega Sociedad sin habilitar imágenes ni resúmenes.
- **EL PAÍS:** los cuatro canales se ofrecen como titulares en su [directorio oficial](https://elpais.com/info/rss/). Se conserva el alcance de titulares y enlaces en agregador; la presencia de Media RSS no habilita fotografías.
- **NASA:** se revisaron su [directorio RSS](https://www.nasa.gov/rss-feeds/) y [directrices de uso y atribución](https://www.nasa.gov/nasa-brand-center/images-and-media/). Se usa el feed Technology con reconocimiento de NASA, sin presentar aval ni reutilizar marcas/fotografías o material de terceros. El supuesto feed `https://science.nasa.gov/feed/` devolvió HTML y se descartó; no se intenta scraping.
- **elDiario.es:** su [aviso legal, apartado 3](https://www.eldiario.es/aviso-legal-eldiario-es/) declara uso bajo [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). Se usa para este proyecto educativo no comercial, con titular original, medio, autor público recibido en RSS y vínculo a la licencia. La ingesta guarda `Article.byline` y `Source.license_url`; las referencias y guardadas conservan esa atribución. No se copian cuerpos ni imágenes y no se extiende la licencia al contenido de terceros.

Los quince feeds nuevos tienen `show_images=False`, `show_summary=False` y `allow_ai_briefing=False`. `allow_ai_grouping=True` permite analizar únicamente los titulares/metadatos para agrupar y estimar importancia, conservando originales; esa operación no se interpreta como autorización para entrenar modelos, republicar artículos o generar resúmenes de esos nuevos canales. La síntesis diaria continúa limitada a los feeds previamente habilitados. No se habilita facturación ni se cambia el proveedor; se mantienen las condiciones de Gemini ya documentadas. Cada fuente puede revocar permisos mediante los controles existentes.

La ampliación no incorpora ScienceDaily: aunque tiene RSS recientes, sus [términos RSS sobre almacenamiento](https://www.sciencedaily.com/terms.htm) requieren autorización previa para ingresar materiales en una base de datos; es incompatible con la persistencia de este proyecto. Chequeado `/feed/` y Tiempo Argentino `/feed/` resultaron antiguos; Chequeado ofrece un feed actualizado con `?post_type=nota`, pero falta resolver su política general de republicación. No se activan esas candidatas. BBC Mundo, DW y France 24 permanecen pendientes de condiciones aplicables al uso, aunque sus RSS respondieron; Infobae, Página/12 y Ámbito conservan las restricciones anteriores. No se elige una fuente sólo porque responda HTTP 200.

Las categorías nuevas utilizan tres SVG originales del proyecto (`salud.svg`, `medioambiente.svg`, `deportes.svg`), sin imágenes de terceros ni licencias externas. Son ilustrativos; su uso como respaldo conserva la etiqueta «Imagen ilustrativa».

### Once feeds originales (antecedente)

### Agrupamiento de coberturas (25/10/2026)

El usuario aprobó reunir titulares del mismo acontecimiento y presentar todas sus fuentes dentro del uso educativo vigente. La migración `0016` habilita `allow_ai_grouping` únicamente en los once feeds existentes enumerados en `0015`; las fuentes nuevas conservan el control desactivado. Es un permiso operativo del proyecto, independiente de imágenes y síntesis, no una licencia adicional concedida por los medios. No se activan fuentes nuevas ni se modifican sus URL o resúmenes RSS.

Para agrupar se transmiten a Gemini exclusivamente ID, título, medio, idioma, fecha y referencia al grupo existente. No se transmiten cuerpos, resúmenes RSS, URLs ni datos de usuarios. Se preservan todos los títulos y enlaces originales, sin producir un titular fusionado. El desplegable enumera medios distintos y todas sus coberturas vigentes con atribución y enlaces, incluso cuando sólo una coincide con los filtros de la categoría. Una cobertura se excluye del grupo visible al desactivar el feed, revocar `allow_ai_grouping` o superar 14 días; revocar agrupamiento no oculta su artículo individual. Las restricciones históricas de cada fuente siguen registradas debajo.

| Fuente y feed | Tema principal | Resultado del 11/10/2026 | Clasificación | Política inicial |
|---|---|---|---|---|
| [Clarín Tecnología](https://www.clarin.com/rss/tecnologia/) | Tecnología | HTTP 200; 10 entradas | Respaldo del feed, sin etiquetas | Título, fecha, fuente y enlace; sin resumen ni imagen |
| [EL PAÍS Tecnología](https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada) | Tecnología | HTTP 200; 21 entradas | Etiquetas aprobadas; respaldo sólo sin etiquetas | Título, fecha, fuente y enlace; sin resumen ni imagen |
| [MIT News — Artificial Intelligence](https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml) | IA | HTTP 200; 50 entradas | Etiquetas aprobadas | Título, fecha, fuente y enlace; sin resumen ni imagen |
| [Clarín Política](https://www.clarin.com/rss/politica/) | Política argentina | HTTP 200; 10 entradas | Respaldo del feed, sin etiquetas | Título, fecha, fuente y enlace; sin resumen ni imagen |
| [Clarín Mundo](https://www.clarin.com/rss/mundo/) | Geopolítica | HTTP 200; 10 entradas | Respaldo del feed, sin etiquetas | Título, fecha, fuente y enlace; sin resumen ni imagen |
| [Clarín Economía](https://www.clarin.com/rss/economia/) | Economía | HTTP 200; 10 entradas | Respaldo del feed, sin etiquetas | Título, fecha, fuente y enlace; sin resumen ni imagen |
| [EL PAÍS Internacional](https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada) | Geopolítica | HTTP 200; 24 entradas | Etiquetas aprobadas; respaldo sólo sin etiquetas | Título, fecha, fuente y enlace; sin resumen ni imagen |
| [EL PAÍS Economía](https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada) | Economía | HTTP 200; 36 entradas | Etiquetas aprobadas; respaldo sólo sin etiquetas | Título, fecha, fuente y enlace; sin resumen ni imagen |
| [Los Andes Política](https://www.losandes.com.ar/rss/pages/politica.xml) | Política argentina y Argentina | HTTP 200; 20 entradas recientes | Etiqueta de sección `Pol�tica`, acotada a este feed | Título, fecha, fuente y enlace; sin resumen ni imagen |
| [Los Andes Economía](https://www.losandes.com.ar/rss/pages/economia.xml) | Economía y Argentina | HTTP 200; 20 entradas recientes | Etiqueta de sección `Econom�a`, acotada a este feed | Título, fecha, fuente y enlace; sin resumen ni imagen |
| [Cinco Días Mercados](https://feeds.elpais.com/mrss-s/list/ep/site/cincodias.elpais.com/section/mercados-financieros) | Mercados y finanzas | HTTP 200; 25 entradas recientes | `Mercados financieros` y otras etiquetas aprobadas | Título, fecha, fuente y enlace; sin resumen ni imagen |

El feed adicional de [EL PAÍS Ciencia](https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/ciencia/portada) continúa pendiente de revisión. El enlace de Clarín para mundo es `/rss/mundo/`, según su directorio oficial; el enlace `/rss/internacional/` anotado en el relevamiento anterior no se usa.

### Condiciones comprobadas para la primera ingesta

- [Clarín publica sus feeds RSS](https://www.clarin.com/filer/RSS/rss.html) para lectores e integración en sitios y aplicaciones. Sus [condiciones específicas](https://www.clarin.com/filer/RSS/terminos_condiciones.html) permiten exhibir títulos y enlaces sin alterar el contenido, con acceso al sitio original. `show_summary` queda desactivado.
- [EL PAÍS describe su RSS](https://elpais.com/info/rss/) como un servicio gratuito de titulares para lectores y agregadores, incluidos servicios web. Se guardan título, metadatos y enlace; el resumen y las imágenes quedan desactivados.
- [MIT News ofrece RSS para sindicación](https://news.mit.edu/terms-of-use) y exige atribución y enlace para la republicación de historias. Esta aplicación sólo conserva titular, fuente, fecha y enlace, sin republicar el artículo ni usar imágenes o resúmenes.
- [Los Andes ofrece sus canales RSS](https://www.losandes.com.ar/contenidos/rss.html) para incluir noticias en un blog o sitio web. Se usa sólo el titular con atribución y enlace original; no se copia el artículo, el resumen ni la imagen. Sus [términos generales](https://www.losandes.com.ar/terminos) reservan el derecho de autor del material editorial.
- [Cinco Días ofrece RSS](https://cincodias.elpais.com/info/rss/) gratuito para lectores y agregadores web. El canal Mercados procede de su directorio oficial. Se muestra sólo titular, fuente, fecha y enlace, sin resumen ni imagen.

Registro histórico: la primera ingesta de los tres feeds iniciales guardó 70 noticias recientes; 11 entradas de MIT News se omitieron por superar la ventana de 60 días usada entonces. La conservación vigente es de 14 días. Los ocho feeds añadidos después respondieron HTTP 200, con XML válido y publicaciones recientes. Los once feeds activos están configurados con `show_summary=False`.

### Presentación generada por IA: criterio anterior al 25/10/2026

La presentación de actualidad usa únicamente título, fuente, fecha de publicación e idioma de noticias RSS dentro de las últimas 24 horas; no envía ni muestra los campos `R` o `I`, ni descarga artículos. Cada punto enlaza las noticias que lo respaldan y diferencia esta síntesis del resumen editorial del feed. Esto no amplía el permiso para reutilizar resúmenes RSS ni imágenes. El campo `Feed.allow_ai_briefing` comienza desactivado en todos los feeds y es independiente de `show_summary`; sólo se debe activar después de verificar que el titular permite procesar títulos con IA y publicar una síntesis derivada. Las condiciones verificadas para Clarín se limitan a exhibir títulos y enlaces sin alterar contenido; MIT define condiciones específicas para republicar historias; Los Andes reserva derechos editoriales; EL PAÍS y Cinco Días describen sus RSS como servicios de titulares para lectores/agregadores. Esos textos no conceden de forma expresa permiso para republicar una síntesis generada por IA. La función requiere revisión de las condiciones aplicables antes de desplegarse públicamente y, si una fuente no permite ese uso, mantener sus titulares fuera del resumen. Referencias: [condiciones RSS de Clarín](https://www.clarin.com/filer/RSS/terminos_condiciones.html), [RSS de EL PAÍS](https://elpais.com/info/rss/), [términos de MIT News](https://news.mit.edu/terms-of-use), [términos de Los Andes](https://www.losandes.com.ar/terminos), [RSS de Cinco Días](https://cincodias.elpais.com/info/rss/) y [condiciones de Cinco Días](https://cincodias.elpais.com/info/condiciones/).

### Etiquetas para clasificar las noticias

La revisión de las entradas del 11/10/2026 encontró lo siguiente:

| Feed | Etiquetas por entrada | Correspondencias aprobadas |
|---|---|---|
| Clarín Tecnología | Ninguna en las 10 entradas | Respaldo: categoría `tecnologia` del feed |
| EL PAÍS Tecnología | 18 de 21 entradas con etiquetas; entre ellas hay temas, personas, marcas y asuntos ajenos a tecnología | `Tecnología` → `tecnologia`; `Inteligencia artificial` → `inteligencia-artificial`; `Ciencia` → `ciencia`. Las 3 entradas sin etiquetas usan el respaldo `tecnologia` |
| MIT News — Artificial Intelligence | 50 de 50 entradas con etiquetas | `Artificial intelligence` → `inteligencia-artificial`; `Computer science and technology` → `tecnologia` |
| Clarín Política, Mundo y Economía | Ninguna en las 10 entradas de cada feed | Respaldo por sección: `politica-argentina`, `geopolitica` y `economia` respectivamente |
| EL PAÍS Internacional | Etiquetas temáticas por entrada | `Guerra`, `Conflictos`, `Conflictos armados`, `Conflictos internacionales`, `Ataques militares` y `OTAN` → `geopolitica` |
| EL PAÍS Economía | Etiquetas temáticas por entrada | `Economía`, `Econom�a`, `Empresas`, `Banca`, `Mercados` y `Empleo` → `economia` |
| Los Andes Política | `Pol�tica` en las 20 entradas | Sólo en este feed: `politica-argentina` y `argentina` |
| Los Andes Economía | `Econom�a` en las 20 entradas | Sólo en este feed: `economia` y `argentina` |
| Cinco Días Mercados | 25 entradas con etiquetas financieras; 25 con `Mercados financieros` o `Bolsa` | `Mercados financieros`, `Bolsa`, `Finanzas`, `Renta variable` y `Renta fija` → `mercados-finanzas` |

Diagnóstico del **13/10/2026**: las etiquetas secundarias de IA generan ruido en los canales económicos. RSS inspeccionados en memoria con el lector existente, ambos válidos: Cinco Días Mercados contiene 25 entradas y aporta 3 a IA; EL PAÍS Economía contiene 39 entradas y aporta 2 a IA y 2 a tecnología. La página publicada confirma noticias principalmente financieras dentro de IA. El usuario descartó restringir canales completos: podrían contener noticias cuyo tema central sí fuera IA. No se cambiaron alias, feeds ni políticas. Queda pendiente evaluar título y etiquetas por noticia; no se almacenaron noticias, XML ni enlaces de artículos en el repositorio.

La lista efectiva está en `news/category_aliases.py`. Una entrada etiquetada sin correspondencia aprobada permanece sin categoría, incluso si el feed está dedicado a un tema. Antes de sumar alias nuevos, revisar muestras del feed: una etiqueta puede ser el nombre de una persona, organización o lugar. `politica-argentina` usa el respaldo de Clarín Política y el alias de sección limitado a Los Andes Política; no clasifica como argentina cualquier noticia mundial con la etiqueta genérica `Política`. Algunas etiquetas llegan con el carácter `�`; se aceptan exactamente como se observaron, además de su escritura correcta por si el medio corrige la codificación.

`argentina` reúne los feeds Clarín Política, Los Andes Política y Los Andes Economía. El feed de Clarín Economía no se agrega porque su muestra contenía muchas cotizaciones de otros países. `mercados-finanzas` es información periodística sobre bolsa e instrumentos financieros, no un servicio de precios en tiempo real.

**Límite de precisión:** los feeds de Clarín no traen etiquetas por noticia. Mundo puede incluir sucesos internacionales no geopolíticos, y Economía incluyó varias cotizaciones diarias de divisas en la muestra. Se incluyen como secciones editoriales curadas, pero habrá que revisar un criterio de selección más fino si generan ruido para los usuarios. Las etiquetas de EL PAÍS seleccionan sólo una parte de las noticias de esas secciones.

## Actividad y capacidad comprobadas el 13/10/2026

Se reutiliza el snapshot de la revisión de frecuencia, obtenido a las **04:00:55 UTC del 13/10/2026**. Los once feeds activos se descargaron e interpretaron correctamente al primer intento con el lector de la aplicación. Se inspeccionaron en memoria; no se almacenaron noticias, XML ni enlaces de artículos en el repositorio.

La mediana se calcula entre fechas de publicación válidas **distintas**. Varias noticias pueden compartir una fecha; el conteo de fechas distintas no equivale a entradas con fecha inválida. La ventana es la diferencia entre la publicación más antigua y la más reciente de la muestra, no una frecuencia de actualización del RSS.

| Feed | Entradas | Fechas distintas | Mediana entre publicaciones (min) | Ventana de la muestra (h) | Publicación más reciente (UTC) |
|---|---|---|---|---|---|
| Cinco Días Mercados | 25 | 22 | 229.6 | 112.50 | 2026-10-13T03:30:01Z |
| Clarín Economía | 10 | 9 | 68.0 | 15.26 | 2026-10-13T02:00:34Z |
| Clarín Mundo | 10 | 10 | 33.5 | 5.71 | 2026-10-12T22:20:32Z |
| Clarín Política | 10 | 10 | 68.3 | 12.00 | 2026-10-13T01:34:13Z |
| Clarín Tecnología | 10 | 10 | 1440.2 | 176.52 | 2026-10-12T17:17:55Z |
| EL PAÍS Economía | 40 | 28 | 160.6 | 491.96 | 2026-10-13T03:45:01Z |
| EL PAÍS Internacional | 23 | 21 | 141.1 | 185.18 | 2026-10-12T18:52:33Z |
| EL PAÍS Tecnología | 21 | 21 | 995.3 | 657.11 | 2026-10-12T03:30:01Z |
| Los Andes Economía | 20 | 20 | 95.7 | 80.73 | 2026-10-13T02:59:43Z |
| Los Andes Política | 20 | 19 | 98.5 | 74.73 | 2026-10-13T03:21:00Z |
| MIT News Artificial Intelligence | 50 | 48 | 1395.0 | 2105.42 | 2026-10-08T21:25:00Z |

Clarín Mundo fue el más frecuente según la mediana de esta muestra: 33,5 minutos y diez entradas que abarcan 5,71 horas. Una consulta cada seis horas podría llegar después de que desaparezcan entradas. La decisión acordada es consultar todos los feeds activos cada dos horas durante el día; no se afirma que todos los servidores RSS cambien cada dos horas.

Horarios previstos, todos los días en Argentina: **06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00 y 00:00**. La última consulta cierra la jornada y se retoma a las 06:00. Las ráfagas, esa pausa nocturna y los posibles retrasos de Actions pueden causar pérdidas: esta configuración no garantiza recuperar todas las noticias.

Esta comprobación no cambia fuentes, permisos ni equivalencias; la revisión de etiquetas sigue fechada el 11/10/2026. No se agregan feeds de ciencia ni otras candidatas, y sigue pendiente evaluar el ruido temático ya registrado.

## Registrada pero desactivada

| Fuente y feed | Idioma / región | Resultado verificado | Campos | Estado y restricción |
|---|---|---|---|---|
| [RTVE Ciencia y tecnología](https://www.rtve.es/rss/temas_ciencia-tecnologia.xml) | Español / España | HTTP 200; RSS 2.0; 180 elementos | T/R/F/E; I ocasional en HTML | Desactivada: la publicación más reciente observada era del 12/06/2022. Sus condiciones de redistribución también son restrictivas |
| [DW Español](https://rss.dw.com/rdf/rss-sp-all) | Español / Alemania-global | En el relevamiento previo: HTTP 200; RDF/RSS 1.0; 20 elementos | T/R/F/E | Desactivada: confirmar condiciones de sindicación antes de incorporarla |
| [NASA Technology](https://www.nasa.gov/technology/feed/) | Inglés / Estados Unidos | En el relevamiento previo: HTTP 200; RSS 2.0; 10 elementos | T/R/F/E/I | Desactivada: revisar excepciones de material de terceros y atribución |
| [Ars Technica](https://feeds.arstechnica.com/arstechnica/index) | Inglés / Estados Unidos | En el relevamiento previo: HTTP 200; RSS 2.0; 20 elementos | T/R/F/E/I | Desactivada: verificar condiciones antes de mostrar titulares |
| [TechCrunch](https://techcrunch.com/feed/) | Inglés / Estados Unidos | En el relevamiento previo: HTTP 200; RSS 2.0; 20 elementos | T/R/F/E | Desactivada: verificar condiciones antes de mostrar titulares |

## Candidatas argentinas

Estas fuentes fueron localizadas y probadas durante el relevamiento del 29 de septiembre de 2026, pero permanecen sin activar. Antes de activar una se debe repetir la prueba de frescura y confirmar que se permite usar sus titulares en esta aplicación. Las imágenes y los resúmenes quedan fuera de la primera entrega.

| Fuente | Feed | Campos observados | Motivo para evaluarla |
|---|---|---|---|
| Infobae | [General](https://www.infobae.com/arc/outboundfeeds/rss/) | T/R/F/E/I | Cobertura argentina y regional; RSS 2.0 con 100 elementos en la prueba |
| La Nación | [General](https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml) | T/R/F/E/I | Medio argentino relevante; RSS 2.0 con 94 elementos en la prueba |
| Página/12 | [Portada](https://www.pagina12.com.ar/arc/outboundfeeds/rss/portada) | T/R/F/E; I variable | Diversidad editorial argentina |
| Perfil | [General](https://www.perfil.com/feed) | T/R/F/E; I variable | Actualidad política y económica |
| Ámbito | [Portada](https://www.ambito.com/rss/pages/home.xml) | T/R/F/E; I variable | Especialización económica |
| El Cronista | [Noticias](https://www.cronista.com/files/rss/news.xml) | T/R/F/E; I variable | Economía y negocios |
| TN | [General](https://tn.com.ar/rss.xml) | T/R/F/E; I variable | Alta frecuencia de actualidad argentina |
| Chequeado | [General](https://chequeado.com/feed/) | T/R/F/E; I variable | Verificación de datos; el feed observado estaba atrasado respecto de la portada |

La revisión del 11/10/2026 encontró restricciones expresas sobre la reutilización de contenido en los [términos de Página/12](https://www.pagina12.com.ar/terminos-y-condiciones/), los [términos de Infobae](https://www.infobae.com/terminos-y-condiciones/) y las [condiciones publicadas por Ámbito](https://www.ambito.com/contenidos/privacidad.html). Sus feeds no se activan sin una autorización o una condición específica y clara para el uso previsto. La [página RSS de Página/12](https://www.pagina12.com.ar/rss/) confirma la existencia de sus canales, pero no resuelve la restricción de reutilización.

## Candidatas internacionales y regionales

La selección busca evitar que la cobertura quede limitada a Argentina y Estados Unidos. Todas requieren una nueva validación de frescura y términos antes de activarse.

| Región | Fuente | Feed | Aporte esperado |
|---|---|---|---|
| Europa / español | BBC Mundo | [General](https://feeds.bbci.co.uk/mundo/rss.xml) | Cobertura global en español; revisar licencia para uso institucional |
| Europa / español | France 24 | [General](https://www.france24.com/es/rss) | Geopolítica desde una perspectiva europea/francesa |
| Europa / español | RFI | [General](https://www.rfi.fr/es/rss) | Internacional, Europa, África y francofonía en español |
| Europa / español | Euronews | [General](https://es.euronews.com/rss?format=xml) | Noticias europeas multilingües |
| Europa / inglés | The Guardian | [Mundo](https://www.theguardian.com/world/rss) | Internacional, ciencia y ambiente |
| Medio Oriente / inglés | Al Jazeera | [General](https://www.aljazeera.com/xml/rss/all.xml) | Cobertura de Medio Oriente y Sur Global |
| Asia / inglés | Channel NewsAsia | [Asia](https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511) | Sudeste asiático |
| Asia / inglés | The Hindu | [Internacional](https://www.thehindu.com/news/international/feeder/default.rss) | Perspectiva india y del sur de Asia |
| Asia / inglés | The Japan Times | [General](https://www.japantimes.co.jp/feed/) | Japón y Asia oriental |
| África / inglés | Africanews | [General](https://www.africanews.com/feed/rss) | Cobertura panafricana |
| África / inglés | Mail & Guardian | [General](https://mg.co.za/feed/) | África austral |
| África / inglés | Daily Maverick | [General](https://www.dailymaverick.co.za/feed/) | Política y análisis sudafricano |
| Global / español | The Conversation | [Español](https://theconversation.com/es/articles.atom) | Divulgación académica y científica; formato Atom |

## GDELT como complemento futuro

Endpoint previsto: `https://api.gdeltproject.org/api/v2/doc/doc`, usando `mode=artlist`, `format=json`, hasta 250 resultados y consultas desde el backend.

La prueba del 29 de septiembre de 2026 devolvió URL, título, fecha de detección, dominio, idioma, país de la fuente e imagen social; no devolvió resumen ni identificó artículos del mismo acontecimiento. Consultas consecutivas también produjeron HTTP 429 con la indicación de separar solicitudes al menos cinco segundos.

Cuando se implemente:

- espaciar consultas y aplicar reintentos con espera progresiva;
- cachear resultados durante al menos 15 minutos;
- filtrar dominios y normalizar con el mismo modelo de los RSS;
- conservar la última respuesta útil si el servicio limita solicitudes;
- no reutilizar automáticamente `socialimage`;
- atribuir GDELT y enlazar siempre al medio original.

GDELT amplía cobertura, pero no reemplaza los feeds seleccionados ni resuelve el agrupamiento de historias.

## Decisión vigente para la presentación educativa (25/10/2026)

### Evaluación de fotografías para una portada diaria

La aplicación ya guarda URL y crédito de imágenes recibidas en RSS y muestra una por tarjeta de noticia sólo cuando `Feed.show_images` está activo. En la muestra local anterior, 204 de 210 noticias de los once feeds originales tenían URL; esto mide disponibilidad técnica, no cobertura diaria garantizada ni licencia. Los quince feeds agregados en `0018` conservan imágenes desactivadas. Una imagen por categoría vinculada al acontecimiento más importante podría salir de una cobertura del mismo grupo publicada ese día, siempre que su feed permita mostrarla y exista crédito; ante ausencia se mantendría la imagen temática con la indicación «Imagen ilustrativa». Seleccionar una foto de otro hecho o una foto de stock y presentarla como documentación del acontecimiento sería engañoso.

La [especificación Media RSS](https://www.rssboard.org/media-rss) permite publicar URL, miniatura, crédito y derechos por objeto, pero esos campos no sustituyen las condiciones del editor. La [licencia RSS de Clarín](https://www.clarin.com/filer/RSS/terminos_condiciones.html) concede expresamente títulos y enlaces, sin una concesión equivalente para fotografías; el [directorio RSS de EL PAÍS](https://elpais.com/info/rss/) tampoco acredita por sí solo ese uso. [MIT News](https://news.mit.edu/terms-of-use) permite determinadas imágenes para entidades no comerciales bajo CC BY-NC-ND con crédito y recorte limitado. Las fotos de [Pexels](https://www.pexels.com/legal-pages/license/) siguen sirviendo como ilustraciones temáticas, pero no prueban un suceso. Su [API](https://www.pexels.com/api/documentation/) añade llave, límites y atribución propia, por lo que no se propone para esta selección factual. Esta investigación no cambia ningún permiso de feed ni amplía la decisión educativa anterior; antes de dar más protagonismo a fotografías de un medio debe confirmarse el uso concreto y la atribución aplicable.

Las URL remotas pueden desaparecer, impedir hotlink o transferir archivos mucho mayores que el tamaño CSS; la muestra de tamaños de más abajo llega a 3,57 MB. El lector ya usa respaldo visual si falla una imagen. Una futura optimización debería preferir miniaturas o variantes ofrecidas por el mismo editor cuando su uso esté permitido y conservar crédito y enlace; no se aprobó descarga, proxy, caché de archivos ni scraping del portal.

Por decisión expresa del usuario, la migración `0015` habilita `show_images` y `allow_ai_briefing` en los once feeds actuales para una presentación escolar no comercial, sin publicación en este bloque. Se usarán fotografías recibidas en el RSS y se sintetizarán titulares con Gemini conservando créditos y enlaces. Esta es una decisión de uso del proyecto, no una licencia concedida por los medios; el análisis de condiciones que sigue permanece como antecedente. No se cambia `show_summary` y fuentes nuevas conservan ambos controles desactivados por defecto.

Se completaron imágenes mediante una descarga forzada de los RSS: la base local conserva 204 noticias con URL de imagen sobre 210; las seis restantes utilizan respaldo temático. El crédito procede de Media RSS cuando existe y de la fuente como respaldo. Una noticia compartida conserva la imagen de su feed original; no se copian archivos ni se extraen cuerpos de artículos. Las imágenes remotas pueden fallar o desaparecer; el navegador reemplaza esas fotografías por el recurso temático identificado como ilustrativo.

Se verificó una síntesis real con `gemini-3.1-flash-lite`: tres puntos basados en 56 titulares de las últimas 24 horas, asociados a sus fuentes. Sólo se transmitieron titulares, fuente, idioma, fecha e ID, sin datos de usuario, cuerpos ni resúmenes RSS. Los intentos tienen timeout y códigos seguros; la clave permanece fuera del repositorio. La síntesis es común y no altera la clasificación existente.

El collage inicial reutiliza las fotografías Pexels de Argentina, geopolítica y tecnología listadas más abajo. El blanco y negro y las transiciones se aplican únicamente a estos recursos ilustrativos locales, no a las fotografías RSS.

Revisión de peso del 25/10/2026, una fotografía remota por fuente, leída sólo en memoria: Clarín 1200×630 / 130.379 bytes JPEG; EL PAÍS 4500×3000 / 871.197 bytes JPEG; Cinco Días 5000×3357 / 1.065.569 bytes JPEG; Los Andes 1200×675 / 1.417.805 bytes PNG; MIT 3600×2400 / 3.568.470 bytes JPEG. No es un promedio ni representa todos los artículos. El tamaño declarado por MIT en su RSS (390×260 en la entrada revisada) no coincide con el archivo real; no se debe asumir que una referencia es una miniatura por esos metadatos. Las ocho fotografías temáticas locales suman 461.172 bytes. No se alteraron URLs ni se agregó descarga o caché de fotografías: queda evaluar variantes oficiales o miniaturas locales para reducir la transferencia.

## Política anterior de imágenes (24/10/2026)

Las tablas anteriores conservan el relevamiento y la política de la primera entrega. El permiso nuevo `Feed.show_images` es independiente de `show_summary` y `allow_ai_briefing`, y comienza desactivado. La revisión para este bloque habilita únicamente MIT News en la migración `0014`; no amplía la autorización de otras fuentes.

- **MIT News:** sus [condiciones para imágenes web](https://news.mit.edu/terms-of-use) permiten uso no comercial bajo CC BY-NC-ND, con crédito y recorte de tamaño. Para este proyecto universitario no comercial se muestran las imágenes recibidas en su RSS, con el crédito proporcionado (MIT News como respaldo) y enlace a las condiciones. No se aplican filtros, alteraciones ni copias al almacenamiento del sitio. La restricción adicional de impresión no se interpreta como autorización para otros usos.
- **Clarín:** las [condiciones RSS](https://www.clarin.com/filer/RSS/terminos_condiciones.html) no ofrecen una autorización clara para reutilizar fotografías; permanecen deshabilitadas.
- **EL PAÍS y Cinco Días:** los directorios RSS describen el servicio de titulares y agregadores, sin resolver una licencia específica de fotografías. No se habilitan por la sola presencia de Media RSS y créditos.
- **Los Andes:** sus [términos generales](https://www.losandes.com.ar/terminos) reservan los derechos editoriales; no se habilitan fotografías sin una autorización aplicable.

La aplicación sólo persiste URL y crédito de imágenes permitidas. Al actualizar una noticia existente se conserva la imagen del feed original; no se reemplaza por la de un origen secundario. Revocar el permiso deja de mostrar inmediatamente sus fotografías y la próxima consulta del feed limpia esos metadatos. Las noticias que ya no estén en el RSS utilizan el respaldo. No se extrae HTML de artículos ni se recuperan imágenes mediante scraping.

La comprobación técnica del 24/10/2026 encontró referencias de imagen en los once feeds: Clarín 10/10 en cada canal; EL PAÍS Tecnología 17/21, Internacional 24/24 y Economía 37/37; MIT 50/50; Los Andes Política 17/20 y Economía 19/20; Cinco Días 25/25. Son referencias observadas en memoria, no permisos ni garantía de disponibilidad futura. En ese bloque muchos artículos usaban respaldo temático porque sólo MIT estaba habilitado.

### Fotografías temáticas locales

Se eligió [Pexels](https://www.pexels.com/license/), cuya licencia permite descarga, uso web gratuito y modificación sin atribución obligatoria. Se registran igualmente autores y enlaces. No se presenta a las personas o marcas fotografiadas como aval del sitio, no se revenden archivos ni se crea un banco de imágenes. Los recursos se recortaron a 960 × 600 y convirtieron a WebP; se sirven localmente, sin API ni consultas al proveedor al navegar. El total es inferior a 500 KB.

| Categoría / archivo | Autor | Fotografía original |
|---|---|---|
| Argentina / `argentina.webp` | Mauro Rodriguez | [Obelisco de Buenos Aires](https://www.pexels.com/photo/buenos-aires-27954172/) |
| Política argentina / `politica-argentina.webp` | Rafael Rodrigues | [Congreso y bandera argentina](https://www.pexels.com/photo/argentinian-congress-building-with-national-flag-36699718/) |
| Geopolítica / `geopolitica.webp` | Ali Levlog | [Globo terráqueo](https://www.pexels.com/photo/a-globe-on-a-white-background-14181516/) |
| Tecnología / `tecnologia.webp` | ClickerHappy | [Circuito electrónico](https://www.pexels.com/photo/shallow-focus-photography-of-black-circuit-board-1448561/) |
| Inteligencia artificial / `inteligencia-artificial.webp` | Sharath G. | [Microcircuito](https://www.pexels.com/photo/close-up-of-computer-circuit-on-table-13089944/) |
| Ciencia / `ciencia.webp` | Edward Jenner | [Investigación en laboratorio](https://www.pexels.com/photo/two-scientists-working-inside-the-laboratory-4031693/) |
| Economía / `economia.webp` | Diego F. Parra | [Contenedores en puerto](https://www.pexels.com/photo/aerial-view-of-containers-and-machinery-in-a-port-24244232/) |
| Mercados y finanzas / `mercados-finanzas.webp` | George Morina | [Pantalla de mercados](https://www.pexels.com/photo/stock-exchange-charts-4960438/) |

Las fotografías temáticas identifican categorías. Cuando reemplazan una imagen de noticia ausente, fallida o no autorizada, se rotulan «Imagen ilustrativa». Se usa la categoría visitada y no se atribuye esa foto al artículo o al medio. Las categorías nuevas sin un recurso seleccionado usan el globo terráqueo como respaldo neutral.

Los resúmenes RSS permanecen deshabilitados. Los controles de imágenes y síntesis de titulares para esta presentación educativa se describen en la decisión vigente del 25/10/2026.
