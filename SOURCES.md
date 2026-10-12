# Fuentes de noticias

## Criterios y leyenda

Este registro separa disponibilidad técnica de permiso de reutilización. Un feed accesible no autoriza a copiar el artículo completo ni necesariamente sus imágenes.

El relevamiento general se realizó el **29 de septiembre de 2026**. Los feeds activados se volvieron a comprobar el **11 de octubre de 2026**. La frecuencia depende de cada medio y puede variar.

Campos:

- `T`: título.
- `R`: resumen o descripción.
- `F`: fecha de publicación.
- `E`: enlace original.
- `I`: imagen o referencia de imagen.

## Feeds activos

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

La primera ingesta de los tres feeds iniciales guardó 70 noticias recientes; 11 entradas de MIT News se omitieron por superar los 60 días. Los ocho feeds añadidos después respondieron HTTP 200, con XML válido y publicaciones recientes. Los once feeds activos están configurados con `show_summary=False`.

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

La lista efectiva está en `news/category_aliases.py`. Una entrada etiquetada sin correspondencia aprobada permanece sin categoría, incluso si el feed está dedicado a un tema. Antes de sumar alias nuevos, revisar muestras del feed: una etiqueta puede ser el nombre de una persona, organización o lugar. `politica-argentina` usa el respaldo de Clarín Política y el alias de sección limitado a Los Andes Política; no clasifica como argentina cualquier noticia mundial con la etiqueta genérica `Política`. Algunas etiquetas llegan con el carácter `�`; se aceptan exactamente como se observaron, además de su escritura correcta por si el medio corrige la codificación.

`argentina` reúne los feeds Clarín Política, Los Andes Política y Los Andes Economía. El feed de Clarín Economía no se agrega porque su muestra contenía muchas cotizaciones de otros países. `mercados-finanzas` es información periodística sobre bolsa e instrumentos financieros, no un servicio de precios en tiempo real.

**Límite de precisión:** los feeds de Clarín no traen etiquetas por noticia. Mundo puede incluir sucesos internacionales no geopolíticos, y Economía incluyó varias cotizaciones diarias de divisas en la muestra. Se incluyen como secciones editoriales curadas, pero habrá que revisar un criterio de selección más fino si generan ruido para los usuarios. Las etiquetas de EL PAÍS seleccionan sólo una parte de las noticias de esas secciones.

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
| Brasil / portugués | Agência Brasil | [Últimas noticias](https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml) | Cobertura pública brasileña y regional |
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

## Política común de imágenes

La primera entrega no consulta, descarga, guarda ni muestra imágenes de los feeds. El campo `I` de las tablas sólo registra lo observado durante el relevamiento histórico. Si se incorpora el uso de imágenes en una entrega posterior, se revisarán antes las condiciones de cada fuente y se documentará una política de almacenamiento y atribución.

El campo `show_summary` de cada feed comienza desactivado. Sólo se habilita tras confirmar que la política de esa fuente permite reutilizar el resumen.
