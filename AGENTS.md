# Reglas de trabajo

Este archivo aplica a todo el repositorio.

## Antes de trabajar

1. Leer siempre `STATUS.md` para conocer el estado y el único próximo paso.
2. Consultar `PROJECT.md` cuando la tarea afecte alcance, arquitectura, datos, almacenamiento o decisiones ya tomadas.
3. Consultar `SOURCES.md` cuando la tarea afecte feeds, atribución, resúmenes o imágenes.

Antes de agregar una dependencia, servicio, algoritmo o solución arquitectónica no trivial, revisar su documentación oficial y entre uno y tres proyectos activos que hayan resuelto un problema comparable. Evaluar licencia, mantenimiento e incidencias conocidas y dejar un resumen de la decisión en la documentación correspondiente. Esta investigación no es necesaria para cambios pequeños ni para decisiones ya documentadas.

## Límites

- No ampliar el alcance sin una decisión explícita.
- No incorporar servicios pagos ni gratuitos que prohíban el uso previsto.
- No guardar secretos, credenciales ni datos reales en el repositorio.
- No almacenar artículos completos ni hacer scraping no autorizado.
- No asumir que un feed permite reutilizar resúmenes o imágenes; aplicar la política de cada fuente.

## Definición de terminado

La documentación es parte de cada tarea. Antes de dar una unidad de trabajo por terminada:

1. Verificar el cambio con controles proporcionales a su riesgo.
2. Actualizar siempre `STATUS.md`, dejando exactamente un próximo paso.
3. Actualizar `PROJECT.md` si cambió arquitectura, alcance, datos, almacenamiento o una decisión.
4. Actualizar `SOURCES.md` si cambió un feed, su estado o su política de uso.
5. Actualizar `README.md` si cambiaron requisitos, instalación, comandos o funciones visibles.
6. Actualizar `.env.example` si cambió una variable de entorno.
7. Si ningún otro documento requiere cambios, registrarlo expresamente en `STATUS.md`.

No crear ADR, skills locales, plantillas o documentación adicional salvo que el crecimiento real del proyecto lo justifique.
