# El Oráculo de ENOM

Aplicación de escritorio para lanzar dados, analizar resultados y conservar un historial local. Está pensada para funcionar desde el código fuente o como una carpeta portable en Windows, sin instalador.

## Funciones

- Lanza entre 1 y 1.000 dados de 2 a 1.000 caras.
- Admite dados habituales y una cantidad de caras personalizada.
- Muestra la suma y filtra resultados con comparadores configurables.
- Copia el último resultado al portapapeles y repite su configuración.
- Guarda, busca, copia, repite y elimina tiradas del historial.
- Conserva los datos junto a la aplicación portable.

## Requisitos para ejecutar desde el código fuente

- Python 3.12 o posterior.
- Un entorno de escritorio compatible con PySide6.

Desde la raíz del repositorio:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m oraculo_enom.app
```

En Linux o macOS, la activación equivalente es `source .venv/bin/activate`.

## Pruebas

Ejecutá la suite completa desde la raíz del repositorio:

```powershell
python -m pytest -v
```

En un entorno Linux sin servidor gráfico, usá:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -v
```

## Compilación portable para Windows

La compilación debe ejecutarse en Windows; PyInstaller genera binarios para el sistema operativo donde se ejecuta.

```powershell
python -m pip install -e ".[dev]"
pyinstaller El-Oraculo-de-ENOM.spec --clean
```

El resultado queda en `dist/El Oraculo de ENOM/`. Para distribuirlo manualmente:

```powershell
Compress-Archive -Path "dist/El Oraculo de ENOM/*" -DestinationPath "El-Oraculo-de-ENOM-Windows.zip"
```

Distribuí la carpeta completa (o el ZIP), no solamente el ejecutable.

## Ubicación de los datos

El historial se guarda en `datos/historial.db`:

- En la versión portable, `datos/` se crea junto a `El Oraculo de ENOM.exe`.
- Al ejecutar desde el código fuente, `datos/` se crea en la raíz del repositorio.

La carpeta que contiene la aplicación debe permitir escritura. La base se crea al iniciar la aplicación y se actualiza con cada tirada guardada. El archivo de desarrollo no se incorpora a la compilación ni al artefacto de CI.

## Estructura del repositorio

```text
src/oraculo_enom/
├── app.py          # Punto de entrada y composición de la aplicación
├── domain/         # Reglas de dados y análisis de resultados
├── persistence/    # Esquema SQLite y repositorio del historial
├── services/       # Portapapeles y rutas portables
└── ui/             # Ventanas, diálogos y tema visual
tests/              # Pruebas de dominio, persistencia, servicios y UI
.github/workflows/  # Automatización de compilación para Windows
El-Oraculo-de-ENOM.spec
pyproject.toml
```

## Descargar el último artefacto de Actions

1. Abrí la pestaña **Actions** del repositorio en GitHub.
2. Elegí la ejecución exitosa más reciente del flujo **Build Windows portable**.
3. En la sección **Artifacts**, descargá **El-Oraculo-de-ENOM-Windows**.
4. Extraé `El-Oraculo-de-ENOM-Windows.zip` en una carpeta con permisos de escritura y ejecutá `El Oraculo de ENOM.exe`.

El flujo se ejecuta para cambios en `main`, pull requests y etiquetas que comienzan con `v`. Solo publica un artefacto de Actions; no crea una GitHub Release.

## Licencia

El Oráculo de ENOM se distribuye bajo la licencia [GNU General Public License v2.0 o posterior](LICENSE), identificada mediante SPDX como `GPL-2.0-or-later`.

## Captura

No se incluye una captura hasta disponer de una imagen real de la aplicación terminada.
