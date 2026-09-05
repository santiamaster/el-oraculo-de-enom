# El Oráculo de ENOM — Especificación de diseño

## 1. Objetivo

Crear una aplicación portable para Windows destinada a realizar tiradas de dados virtuales. Debe funcionar sin conexión, conservar un historial persistente y presentar una interfaz sencilla inspirada en la estética fantástica de ENOM.

## 2. Tecnología y distribución

- Lenguaje: Python.
- Interfaz gráfica: PySide6.
- Persistencia: SQLite.
- Empaquetado: PyInstaller.
- Distribución: carpeta portable con un ejecutable y su directorio de datos.
- Nombre visible: **El Oráculo de ENOM**.
- Repositorio principal: `santiamaster/el-oraculo-de-enom` (público).
- Integración continua: GitHub Actions ejecutará las pruebas y generará el portable de Windows.
- Compatibilidad futura: el código evitará dependencias exclusivas de Windows para facilitar versiones posteriores en Linux y macOS.

Estructura prevista:

```text
El Oráculo de ENOM/
├── El Oráculo de ENOM.exe
└── datos/
    └── historial.db
```

Copiar la carpeta completa a otra ubicación conservará el historial. La aplicación no requerirá conexión a Internet ni instalación.

La primera versión distribuida será para Windows. La estructura del código, las rutas y las pruebas deberán permanecer independientes del sistema operativo; los paquetes para otras plataformas quedarán fuera del primer entregable.

## 3. Dados y límites

La pantalla principal ofrecerá accesos directos para los siguientes dados:

- d4
- d6
- d8
- d10
- d12
- d16
- d20
- d50
- d100

También permitirá ingresar una cantidad personalizada de caras.

- Caras permitidas: entre 2 y 1.000.
- Cantidad de dados permitida: entre 1 y 1.000.
- Selector rápido de cantidad: valores del 1 al 10.
- Campo personalizado de cantidad: cualquier entero válido dentro del límite.

La notación visible seguirá el formato `cantidad d caras`, por ejemplo, `22d350`.

## 4. Flujo principal

1. El usuario selecciona un dado rápido o introduce su cantidad de caras.
2. Selecciona de 1 a 10 dados o introduce una cantidad personalizada.
3. Decide si desea mostrar la suma.
4. Opcionalmente configura un comparador y un umbral.
5. Presiona **Tirar dados**.
6. La aplicación valida los datos.
7. El motor genera todos los resultados.
8. La interfaz muestra los valores, la suma solicitada y las coincidencias.
9. La tirada se guarda automáticamente en el historial.

El generador utilizará `secrets.randbelow(caras) + 1`, con límites inclusivos entre 1 y la cantidad de caras.

## 5. Resultados, suma y filtros

Todos los valores generados se mostrarán individualmente. Si la cantidad no cabe en el espacio disponible, el área de resultados tendrá desplazamiento.

La opción **Mostrar suma** controlará la visibilidad de la suma en la pantalla. La suma se calculará y almacenará siempre, aunque la opción esté desactivada.

El filtro será opcional y admitirá:

- Mayor que (`>`).
- Mayor o igual que (`≥`).
- Menor que (`<`).
- Menor o igual que (`≤`).
- Igual a (`=`).

Los resultados coincidentes se resaltarán en dorado. También se mostrará un resumen contextual, por ejemplo: **9 de 22 resultados superaron 12**.

Las acciones posteriores serán:

- **Repetir tirada:** reutiliza la configuración y genera resultados nuevos.
- **Copiar resultados:** copia notación, valores y, cuando corresponda, suma y resumen del filtro.

## 6. Interfaz visual

La pantalla principal tendrá dos sectores:

- Área principal izquierda: dados, cantidad, filtro, acción de tirar, resultados y resúmenes.
- Panel derecho: historial reciente y acceso al historial completo.

Dirección visual:

- Fantasía oscura inspirada en ENOM.
- Fondo marrón oscuro y negro cálido.
- Paneles semejantes a cuero o pergamino oscuro.
- Bordes y resaltados dorados.
- Tipografía de títulos con carácter fantástico y texto de controles muy legible.
- Animaciones discretas; las tiradas numerosas deben aparecer sin demoras artificiales.
- Diseño adaptable a distintos tamaños de ventana, manteniendo accesibles los controles principales.

## 7. Historial persistente

Cada registro almacenará:

- Identificador interno.
- Fecha y hora local.
- Cantidad de dados.
- Cantidad de caras.
- Lista completa de resultados.
- Suma total.
- Estado de **Mostrar suma**.
- Comparador utilizado, si corresponde.
- Umbral utilizado, si corresponde.
- Cantidad de coincidencias.

El historial completo se abrirá en una ventana independiente. Mostrará primero las tiradas más recientes y permitirá:

- Consultar el detalle de una tirada.
- Filtrar por fecha.
- Filtrar por tipo de dado, incluido un dado personalizado.
- Repetir una configuración.
- Copiar una tirada.
- Eliminar un registro.
- Borrar todo el historial con confirmación previa.

## 8. Validaciones y errores

Solo se aceptarán números enteros dentro de los límites establecidos. Se rechazarán campos vacíos requeridos, texto, decimales, ceros, negativos y valores fuera de rango.

Los mensajes indicarán el problema y su solución, por ejemplo: **La cantidad de caras debe estar entre 2 y 1.000**. Un error de validación no cerrará la aplicación ni eliminará los valores introducidos.

Si el ejecutable no puede crear o modificar `datos/historial.db`, se informará que la carpeta actual no permite escritura y se recomendará mover la aplicación a otra ubicación. No se simulará que la tirada fue guardada.

## 9. Componentes internos

- **Motor de dados:** valida los límites y genera resultados sin depender de la interfaz.
- **Analizador de tiradas:** calcula suma, aplica comparadores y produce el resumen.
- **Interfaz PySide6:** administra las ventanas, controles y presentación visual.
- **Repositorio SQLite:** crea el esquema y administra altas, consultas y eliminaciones.
- **Rutas portables:** resuelve la ubicación del ejecutable y del directorio `datos`.
- **Formateador de portapapeles:** transforma una tirada en texto legible.

Cada componente tendrá responsabilidades acotadas y podrá probarse de forma independiente.

## 10. Verificación

Las pruebas cubrirán:

- Dados rápidos y dados personalizados.
- Tiradas mínimas y máximas: `1d2` y `1000d1000`.
- Inclusión correcta de los extremos 1 y cantidad de caras.
- Rechazo de entradas inválidas y fuera de rango.
- Funcionamiento de los cinco comparadores.
- Suma correcta de todos los resultados.
- Resumen correcto de coincidencias.
- Guardado y recuperación del historial después de reiniciar.
- Repetición, copia, eliminación individual y borrado total.
- Persistencia al mover la carpeta completa.
- Respuesta y legibilidad con grandes cantidades de resultados.

## 11. Fuera del alcance de la primera versión

- Sonidos.
- Animaciones complejas o simulación física de dados.
- Modificadores matemáticos.
- Expresiones combinadas como `2d20 + 1d6`.
- Sincronización en línea.
- Perfiles de usuario.
- Integración directa con la aplicación o la campaña de ENOM.

Estas funciones podrán evaluarse para versiones posteriores sin formar parte del primer entregable.
