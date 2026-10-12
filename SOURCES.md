# Fuentes de noticias

## Criterios y leyenda

Este registro separa disponibilidad técnica de permiso de reutilización. Un feed accesible no autoriza a copiar el artículo completo ni necesariamente sus imágenes.

El relevamiento general se realizó el **29 de septiembre de 2026**. Los tres feeds elegidos para la primera ingesta se volvieron a comprobar el **11 de octubre de 2026**. La frecuencia es una estimación basada en las fechas de los elementos observados, no una garantía del medio.

Campos:

- `T`: título.
- `R`: resumen o descripción.
- `F`: fecha de publicación.
- `E`: enlace original.
- `I`: imagen o referencia de imagen.

## Fuentes iniciales activas

| Fuente y feed | Idioma / región | Resultado verificado | Campos | Frecuencia aproximada | Política inicial |
|---|---|---|---|---|---|
| [EL PAÍS Tecnología](https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada) | Español / España | HTTP 200; RSS 2.0; 21 elementos; revalidado 11/10/2026 | T/R/F/E/I | Tecnología cada ~10 h; otros feeds varias veces por día | Activo: sólo título sin modificar, fuente, fecha y enlace original; sin resumen ni imagen |
| [DW Español](https://rss.dw.com/rdf/rss-sp-all) | Español / Alemania-global | HTTP 200; RDF/RSS 1.0; 20 elementos | T/R/F/E | Cada 1–2 h | Para la demo, título, teaser y enlace; confirmar sindicación antes de una publicación estable |
| [Clarín Tecnología](https://www.clarin.com/rss/tecnologia/) | Español / Argentina | HTTP 200; RSS 2.0; 10 elementos; revalidado 11/10/2026 | T/R/F/E/I | Tecnología cada ~11 h; Economía e Internacional cerca de cada hora | Activo: sólo título sin modificar, fuente, fecha y enlace original; sin resumen ni imagen |
| [MIT News — Artificial Intelligence](https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml) | Inglés / Estados Unidos | HTTP 200; RSS 2.0; 50 elementos; revalidado 11/10/2026 | T/R/F/E/I | Cada ~29 h | Activo: sólo título, atribución a MIT News, fecha y enlace original; sin resumen ni imagen |
| [NASA Technology](https://www.nasa.gov/technology/feed/) | Inglés / Estados Unidos | HTTP 200; RSS 2.0; 10 elementos | T/R/F/E/I | Cada ~40 h | Uso educativo/informativo con atribución; revisar excepciones de terceros, personas y logotipos |
| [Ars Technica](https://feeds.arstechnica.com/arstechnica/index) | Inglés / Estados Unidos | HTTP 200; RSS 2.0; 20 elementos | T/R/F/E/I | Cada ~35 min | Titular, extracto provisto y enlace; no copiar texto completo ni imágenes por defecto |
| [TechCrunch](https://techcrunch.com/feed/) | Inglés / Estados Unidos | HTTP 200; RSS 2.0; 20 elementos | T/R/F/E; I no observada | Cada ~12 min | Mostrar sólo lo provisto por el feed, sin modificarlo, con atribución y enlace |

Feeds adicionales ya comprobados para las fuentes iniciales:

- EL PAÍS: [Economía](https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada), [Ciencia](https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/ciencia/portada) e [Internacional](https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada).
- Clarín: [Economía](https://www.clarin.com/rss/economia/) e [Internacional](https://www.clarin.com/rss/internacional/).

### Condiciones comprobadas para la primera ingesta

- [Clarín publica sus feeds RSS](https://www.clarin.com/filer/RSS/rss.html) para lectores e integración en sitios y aplicaciones. Sus [condiciones específicas](https://www.clarin.com/filer/RSS/terminos_condiciones.html) permiten exhibir títulos y enlaces sin alterar el contenido, con acceso al sitio original. `show_summary` queda desactivado.
- [EL PAÍS describe su RSS](https://elpais.com/info/rss/) como un servicio gratuito de titulares para lectores y agregadores, incluidos servicios web. Se guardan título, metadatos y enlace; el resumen y las imágenes quedan desactivados.
- [MIT News ofrece RSS para sindicación](https://news.mit.edu/terms-of-use) y exige atribución y enlace para la republicación de historias. Esta aplicación sólo conserva titular, fuente, fecha y enlace, sin republicar el artículo ni usar imágenes o resúmenes.

La comprobación técnica del 11/10/2026 obtuvo 10, 21 y 50 entradas respectivamente, todas con XML válido. La primera ingesta guardó 70 noticias recientes; 11 entradas de MIT News se omitieron por superar los 60 días. Los tres feeds se activaron con `show_summary=False`. Los feeds restantes continúan sin cargar en la aplicación.

### Etiquetas para clasificar las noticias

La revisión de las entradas del 11/10/2026 encontró lo siguiente:

| Feed | Etiquetas por entrada | Correspondencias aprobadas |
|---|---|---|
| Clarín Tecnología | Ninguna en las 10 entradas | Respaldo: categoría `tecnologia` del feed |
| EL PAÍS Tecnología | 18 de 21 entradas con etiquetas; entre ellas hay temas, personas, marcas y asuntos ajenos a tecnología | `Tecnología` → `tecnologia`; `Inteligencia artificial` → `inteligencia-artificial`; `Ciencia` → `ciencia`. Las 3 entradas sin etiquetas usan el respaldo `tecnologia` |
| MIT News — Artificial Intelligence | 50 de 50 entradas con etiquetas | `Artificial intelligence` → `inteligencia-artificial`; `Computer science and technology` → `tecnologia` |

La lista efectiva está en `news/category_aliases.py`. Una entrada etiquetada sin correspondencia aprobada permanece sin categoría, incluso si el feed está dedicado a un tema. Antes de sumar alias nuevos, revisar muestras del feed: una etiqueta puede ser el nombre de una persona, organización o lugar. Las categorías `economia` y `geopolitica` no tienen alias aprobados todavía porque estos tres feeds no aportan etiquetas pertinentes observadas. Esta selección no modifica las condiciones de reutilización de los contenidos.

## Registrada pero desactivada

| Fuente y feed | Idioma / región | Resultado verificado | Campos | Estado y restricción |
|---|---|---|---|---|
| [RTVE Ciencia y tecnología](https://www.rtve.es/rss/temas_ciencia-tecnologia.xml) | Español / España | HTTP 200; RSS 2.0; 180 elementos | T/R/F/E; I ocasional en HTML | Desactivada: la publicación más reciente observada era del 12/06/2022. Sus condiciones de redistribución también son restrictivas |

## Candidatas argentinas

Estas fuentes fueron localizadas y probadas durante el relevamiento del 29 de septiembre de 2026, pero no forman parte de la primera tanda. Antes de activar una se debe repetir la prueba de frescura y confirmar si se permite reutilizar el resumen. Las imágenes quedan fuera de la primera entrega.

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
