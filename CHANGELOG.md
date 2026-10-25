# Changelog

Todos los cambios destacados de El Oráculo de ENOM se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el proyecto adopta [Versionado Semántico](https://semver.org/lang/es/).

## [1.0.0] - 2026-10-25

### Added

- Tiradas simples de 1 a 1.000 dados, con entre 2 y 1.000 caras por dado.
- Dados habituales y dados con una cantidad personalizada de caras.
- Tiradas combinadas de hasta 10 tipos de dados, respetando un máximo total de
  1.000 dados.
- Filtros independientes para cada componente de una tirada combinada, con
  subtotales y suma global opcionales para la tirada completa.
- Títulos opcionales para identificar, buscar y editar las tiradas guardadas.
- Historial reciente y completo con acciones para copiar, repetir, retitular y
  eliminar tiradas simples o combinadas.
- Persistencia local mediante SQLite dentro de la carpeta portable.
- Avisos y textos de licencia de los componentes redistribuidos dentro del
  portable.

### Changed

- Interfaz adaptable a pantallas de 1366 × 768 y 1920 × 1080.
- Organización de los controles de cantidad personalizada para mantener
  alineados los campos editables.
- Vista resumida del historial para conservar una altura estable incluso en
  tiradas de 1.000 dados; el detalle mantiene el resultado completo.

### Fixed

- Superposición de los resultados, subtotales y suma global en pantallas de
  poca altura.
- Área interactiva incorrecta de los controles de incremento y decremento en
  determinadas resoluciones.
- Filas del historial que crecían verticalmente y ocultaban otras columnas al
  mostrar tiradas masivas.
