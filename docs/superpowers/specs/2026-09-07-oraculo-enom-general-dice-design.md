# El Oráculo de ENOM — Diseño de tiradas generales

## Objetivo

Convertir la aplicación de escritorio en un tirador de dados general capaz de ejecutar tiradas simples y combinadas, sin perder la claridad de la interfaz principal. El rediseño incorpora títulos editables, sumas verdaderamente opcionales, filtros independientes por tipo de dado y un esquema SQLite preparado para evolucionar después de `1.0.0`.

## Alcance

Este diseño cubre:

- aclarar y condicionar el campo de cantidad personalizada;
- incorporar un título opcional de hasta 150 caracteres;
- no persistir totales ni subtotales cuando `Mostrar suma` está desactivado;
- ejecutar hasta 10 tipos diferentes de dados en una misma tirada;
- admitir dados de 2 a 1.000 caras y hasta 1.000 dados totales;
- configurar un filtro independiente para cada tipo de dado;
- mostrar, copiar, repetir, buscar y persistir tiradas combinadas;
- editar títulos desde el historial;
- sustituir el esquema experimental de SQLite por el esquema definitivo previo a `1.0.0`.

No cubre todavía la publicación de `1.0.0`, firma digital, SBOM, avisos de terceros ni migración a Web o Android. Esas tareas se realizarán cuando las funciones de escritorio estén aprobadas.

## Principios de interfaz

La ventana principal conserva el flujo rápido para una tirada de un solo tipo. La configuración combinada vive en una ventana independiente, visualmente coherente con el tema Fantasía/RPG pero deliberadamente más densa y funcional, como una sección de opciones avanzadas.

La composición visual aprobada se conserva en `docs/assets/combined-roll-dialog-mockup.png`. Es una referencia de jerarquía, distribución y contenido; los controles finales deben usar widgets nativos de PySide6 y respetar el comportamiento definido en este documento.

Las tiradas simples y combinadas compartirán el mismo modelo de dominio, persistencia, representación de resultados e historial. Una tirada simple será una tirada con un único componente, evitando dos caminos de negocio diferentes.

## Interfaz principal

### Cantidad personalizada

La cuadrícula de opciones se reorganizará así:

| Fila | Columna 1 | Columna 2 | Columna 3 | Columna 4 |
|---|---|---|---|---|
| Cantidad | `Cantidad` | selector `1–10`/`Personalizada` | `Cantidad personalizada` | campo numérico |
| Opciones | `Aplicar filtro` | comparador | umbral | `Mostrar suma` |

El campo personalizado estará deshabilitado mientras el selector contenga una cantidad entre 1 y 10. Al elegir `Personalizada`, se habilitará y conservará el último valor introducido. Repetir una tirada simple de más de 10 dados seleccionará y habilitará automáticamente la opción personalizada.

### Título

Antes del botón principal aparecerán:

- la etiqueta `Título de la tirada`;
- un campo de texto de hasta 150 caracteres;
- un botón pequeño `×` con nombre accesible `Limpiar título`.

El título será opcional y vacío de manera predeterminada. Se conservará entre tiradas simples y combinadas hasta que el usuario lo modifique o limpie. El botón de limpieza estará deshabilitado cuando el campo esté vacío y no solicitará confirmación.

### Acceso a la tirada combinada

La ventana principal ofrecerá el botón `Configurar tirada combinada`. Este abrirá el constructor avanzado sin sustituir los controles de tirada simple.

### Repetición

Existirá un único botón de repetición en la ventana principal:

- mostrará `Repetir tirada` después de una tirada simple;
- mostrará `Repetir tirada combinada` después de una combinada;
- ejecutará inmediatamente una nueva tirada con la última configuración completa;
- recuperará el título, componentes, suma y filtros del registro repetido.

## Ventana de tirada combinada

### Componentes

La ventana permitirá crear hasta 10 componentes con cantidades de caras diferentes. Cada componente tendrá:

- cantidad de dados entre 1 y 1.000;
- cantidad de caras entre 2 y 1.000;
- filtro opcional;
- comparador `>`, `>=`, `<`, `<=` o `=`;
- umbral entero cuando el filtro esté activado;
- acción para eliminar el componente.

La suma de las cantidades de todos los componentes no podrá superar 1.000 dados. Los dados habituales `d4`, `d6`, `d8`, `d10`, `d12`, `d16`, `d20`, `d50` y `d100` estarán disponibles mediante selección rápida, y cualquier cantidad de caras válida podrá cargarse manualmente.

Si se agrega un tipo de dado ya presente, las cantidades se combinarán en un único componente. Por ello, el límite de 10 se aplica a cantidades de caras distintas.

### Opciones generales

La ventana tendrá su propio campo de título, sincronizado con el título vigente de la ventana principal al ejecutar la tirada, y una casilla `Mostrar suma`. El título conservará el límite de 150 caracteres y ofrecerá un botón de limpieza.

No habrá un filtro global: cada componente administrará el suyo para que umbrales diferentes puedan responder a reglas distintas del juego.

### Acciones

La ventana mostrará:

- una vista previa canónica, como `2d6 + 1d8 + 3d20`;
- el total de dados configurados;
- `Limpiar configuración`, que quitará componentes y restablecerá suma y filtros;
- `Tirar combinación`, habilitado solo cuando la configuración sea válida;
- `Cancelar`, que cerrará sin ejecutar ni alterar la última tirada.

Después de una ejecución válida, la ventana se cerrará y los resultados aparecerán en la ventana principal. La configuración combinada permanecerá en memoria mientras continúe abierta la aplicación. No se restaurará al reiniciar. Limpiar el constructor no eliminará la última tirada ni deshabilitará su repetición.

## Modelo de dominio

### Solicitud

Una solicitud contendrá:

- título normalizado;
- uno a diez componentes ordenados;
- indicador `show_sum`.

Cada componente contendrá `count`, `sides`, `comparator` y `threshold`. Un filtro será válido únicamente cuando comparador y umbral estén presentes conjuntamente.

El título conservará el contenido escrito, salvo espacios exteriores, y no podrá superar 150 caracteres. Los componentes tendrán cantidades de caras únicas y orden estable. El modelo será inmutable después de validar la solicitud.

### Resultado

Cada resultado contendrá la solicitud original, fecha y resultados por componente. Las coincidencias se derivarán aplicando el filtro del componente correspondiente.

Si `show_sum` está activo, se calcularán subtotales por componente y una suma global. Si está inactivo, subtotales y total serán `None`; no se mostrarán ni persistirán. Los valores individuales siempre se conservarán porque constituyen el resultado esencial de la tirada.

## Presentación de resultados

Los resultados se agruparán por componente y respetarán su orden:

```text
d6 — 2 tiradas
4, 6
Subtotal: 10
Filtro >= 5: 1 de 2

d20 — 3 tiradas
3, 15, 19
Subtotal: 37
Filtro > 12: 2 de 3

Suma total: 47
```

Los valores coincidentes conservarán el resaltado visual actual. Los subtotales y la suma global aparecerán solamente cuando `show_sum` esté activo. Un componente sin filtro no mostrará resumen de coincidencias.

La tirada simple utilizará la misma presentación con un solo grupo, manteniendo el aspecto compacto actual cuando sea posible.

## Copiado

El texto copiado incluirá, en este orden:

1. título, solo cuando no esté vacío;
2. una línea de notación y valores por componente;
3. subtotal después de cada componente, solo si se solicitó suma;
4. resumen del filtro después del componente correspondiente;
5. suma global, solo en combinaciones con más de un componente y `show_sum` activo.

Una tirada simple conservará el formato actual `Suma: N` en lugar de mostrar simultáneamente un subtotal y una suma global equivalentes.

Ejemplo:

```text
Ataque combinado de Arhat
2d6: 4, 6
Subtotal d6: 10
Filtro d6 >= 5: 1 de 2
3d20: 3, 15, 19
Subtotal d20: 37
Filtro d20 > 12: 2 de 3
Suma total: 47
```

## Historial

El historial reciente y completo mostrarán primero el título cuando exista y siempre incluirán la notación canónica. Para combinaciones se utilizará `2d6 + 1d8 + 3d20`.

La búsqueda del historial admitirá texto libre sobre el título. El filtro por caras devolverá una tirada cuando cualquiera de sus componentes use esa cantidad de caras. Los filtros por fecha conservarán su semántica inclusiva actual.

El usuario podrá editar el título desde el historial mediante una acción explícita. La edición validará el límite de 150 caracteres, aceptará un valor vacío, actualizará solo el título y refrescará tanto el diálogo como el panel de historial reciente. Copiar y repetir usarán el título actualizado.

Eliminar una tirada eliminará todos sus componentes de manera atómica. Los errores de lectura o escritura conservarán el estado visible y mostrarán un mensaje accionable, como ocurre en la versión actual.

## Persistencia SQLite

### Tabla `rolls`

Contendrá:

- `id INTEGER PRIMARY KEY`;
- `created_at TEXT NOT NULL`;
- `title TEXT NOT NULL DEFAULT ''` con máximo de 150 caracteres;
- `show_sum INTEGER NOT NULL` limitado a `0` o `1`;
- `total INTEGER NULL`.

`total` será no nulo solamente cuando `show_sum = 1`.

### Tabla `roll_components`

Contendrá:

- `id INTEGER PRIMARY KEY`;
- `roll_id INTEGER NOT NULL` con clave foránea y borrado en cascada;
- `position INTEGER NOT NULL`;
- `count INTEGER NOT NULL`;
- `sides INTEGER NOT NULL`;
- `values_json TEXT NOT NULL`;
- `subtotal INTEGER NULL`;
- `comparator TEXT NULL`;
- `threshold INTEGER NULL`.

Los componentes de una tirada tendrán posiciones y cantidades de caras únicas. `subtotal` será no nulo únicamente cuando la tirada solicite suma. Comparador y umbral serán ambos nulos o ambos no nulos. La cantidad de coincidencias se derivará de los valores y no se duplicará en la base.

SQLite activará claves foráneas en cada conexión. Se crearán índices para fecha, título, relación de componentes y cantidad de caras.

## Estrategia para la base experimental

El historial producido hasta ahora pertenece exclusivamente a pruebas y no necesita conservarse. La transición previa a `1.0.0` no implementará una conversión de registros experimentales: antes de probar la nueva compilación se retirará o eliminará manualmente `datos/historial.db`, y la aplicación creará el esquema definitivo desde cero.

El nuevo esquema quedará versionado mediante `PRAGMA user_version`. Desde la publicación de `1.0.0`, cualquier modificación posterior deberá usar migraciones transaccionales y preservar historiales reales.

La aplicación no borrará silenciosamente una base con esquema incompatible. Mostrará una indicación para moverla o eliminarla, evitando pérdida accidental de datos.

## Errores y validación

La interfaz impedirá ejecutar configuraciones con:

- cero componentes;
- más de 10 tipos de dado;
- tipos repetidos sin combinar;
- menos de 1 o más de 1.000 dados totales;
- menos de 2 o más de 1.000 caras;
- filtros incompletos;
- títulos de más de 150 caracteres;
- valores almacenados que no coincidan con cantidad o rango.

Las escrituras de cabecera y componentes se realizarán en una única transacción. Cualquier fallo provocará rollback completo y un mensaje visible; nunca se mostrará como guardada una tirada parcialmente persistida.

## Estrategia de pruebas

Las pruebas automatizadas cubrirán:

- construcción e inmutabilidad de solicitudes simples y combinadas;
- combinación de tipos repetidos y orden canónico;
- límites de caras, componentes y cantidad total;
- filtros independientes y coincidencias por componente;
- total y subtotales presentes o ausentes según `show_sum`;
- formato copiable con y sin título, suma y filtros;
- creación y reconocimiento del esquema versionado;
- escrituras atómicas, cascadas y rollback;
- búsqueda por título, caras y fechas;
- edición del título y actualización inmediata de vistas;
- habilitación de cantidad personalizada;
- constructor combinado, limpieza y persistencia solo en memoria;
- resultados agrupados;
- repetición inmediata simple y combinada;
- compatibilidad del empaquetado portable sin una base precreada.

Después de aprobar la suite se construirá un candidato portable en Windows y se repetirá la lista manual de aceptación con tiradas simples, combinadas, reinicio, historial, copia, edición y errores de validación.

## Criterios de aceptación

El cambio estará listo para revisión manual cuando:

- la ventana principal conserve su sencillez y aclare la cantidad personalizada;
- sea posible titular, limpiar, copiar, repetir y editar una tirada;
- una combinación de hasta 10 tipos y 1.000 dados se ejecute correctamente;
- cada componente admita su propio filtro;
- resultados, subtotales y suma sean inequívocos;
- una tirada sin suma no persista total ni subtotales;
- el historial represente y restaure tiradas simples y combinadas;
- SQLite rechace o revierta escrituras parciales;
- todas las pruebas automatizadas y manuales acordadas pasen.
