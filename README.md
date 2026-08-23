# Transcriptor Pro

Transcriptor de audio y video basado en [OpenAI Whisper](https://github.com/openai/whisper)
y [FFmpeg](https://ffmpeg.org/), con interfaz gráfica de escritorio (PySide6/Qt).

Permite transcribir cualquier archivo de audio o video a texto, con soporte
de GPU (CUDA) cuando está disponible, y exportar el resultado en cinco
formatos seleccionables: **TXT, Markdown, SRT, VTT y JSON**.

## Características

- **Interfaz gráfica moderna** (PySide6): selección de archivo, modelo y
  formatos mediante checkboxes, sin necesidad de usar la terminal.
- **No bloquea la interfaz**: la transcripción corre en un hilo en segundo
  plano (`QThread`); la ventana permanece responsiva durante todo el proceso.
- **Detección automática de FFmpeg**: busca primero en la configuración
  guardada, luego en el `PATH` del sistema, y solo pide selección manual
  si no lo encuentra.
- **Detección automática de GPU**: usa CUDA si hay una GPU NVIDIA disponible,
  y CPU en caso contrario.
- **Progreso real de la transcripción**: la barra de progreso muestra el
  porcentaje real de avance (no solo un indicador indeterminado), calculado
  a partir de los frames de audio ya procesados por Whisper.
- **Recomendación de modelo según tu hardware**: detecta la RAM del sistema
  y, si existe, la VRAM de la GPU, y sugiere el modelo Whisper (`tiny` a
  `large`) más adecuado para esa capacidad, con un botón para aplicarlo.
- **Persistencia de preferencias**: recuerda la ruta de FFmpeg, el último
  modelo usado, los formatos de salida elegidos y la carpeta de salida.
- **Arquitectura desacoplada**: la lógica de negocio (`core/`) no depende de
  ningún framework de interfaz, lo que la hace fácilmente testeable y
  reutilizable (por ejemplo, en una futura versión de línea de comandos).

## Estructura del proyecto

```
transcriptor_pro/
├── main.py                 # Punto de entrada único
├── core/                   # Lógica de negocio (sin dependencias de GUI)
│   ├── config.py           # Persistencia de configuración (JSON)
│   ├── ffmpeg_utils.py      # Detección y validación de FFmpeg
│   ├── hardware.py           # Detección de RAM/VRAM y recomendación de modelo
│   ├── transcriber.py       # Wrapper de Whisper (dispositivo, modelo, transcripción, progreso)
│   └── exporters.py         # Exportadores TXT / MD / SRT / VTT / JSON
├── gui/                     # Interfaz gráfica (PySide6)
│   ├── main_window.py       # Ventana principal (orquesta los paneles)
│   ├── worker.py             # QThread que ejecuta la transcripción
│   └── widgets/               # Paneles independientes y reutilizables
│       ├── ffmpeg_panel.py
│       ├── file_panel.py
│       ├── hardware_panel.py
│       ├── model_panel.py
│       ├── format_panel.py
│       └── log_panel.py
├── tests/                   # Suite de tests (pytest + smoke/integration)
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── .pylintrc
```

## Instalación

Requiere **Python 3.10 o superior**.

> 💡 **Recomendado: Python 3.12.** Es la versión con la que se ha probado
> y desarrollado el proyecto; con versiones anteriores (3.10/3.11) debería
> funcionar igualmente, pero 3.12 es la configuración de referencia.

```bash
# 1. Crear y activar un entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt
```

> ⚠️ **Importante:** la carpeta del entorno virtual (`venv/`, `env/`) **nunca**
> debe subirse al repositorio. Ya está excluida en `.gitignore`.

### FFmpeg

La aplicación necesita un ejecutable de FFmpeg. Si ya está instalado y
accesible desde el `PATH` del sistema, se detectará automáticamente. Si no,
la interfaz te pedirá que selecciones manualmente el ejecutable la primera
vez, y recordará esa ruta en las siguientes ejecuciones.

- Descarga oficial: https://ffmpeg.org/download.html

## Uso

```bash
python3 main.py
```

1. La aplicación intenta detectar FFmpeg automáticamente. Si no lo logra,
   pulsa **"Seleccionar ejecutable…"** y localiza `ffmpeg` / `ffmpeg.exe`.
2. Pulsa **"Examinar…"** para elegir el archivo de audio o video a transcribir.
3. (Opcional) Elige una carpeta de salida distinta a la del archivo original.
4. Revisa el panel **"Hardware detectado"**: muestra tu RAM/VRAM y el modelo
   Whisper recomendado; pulsa **"Usar modelo recomendado"** para aplicarlo,
   o elige otro manualmente en el panel de modelo.
5. Selecciona el modelo de Whisper (`tiny` a `large`, o `turbo` si está disponible).
6. Marca los formatos de salida que quieres generar (TXT, MD, SRT, VTT, JSON).
7. Pulsa **"Transcribir"**. El panel inferior muestra el progreso, incluyendo
   el porcentaje real de avance una vez comienza la transcripción.

## Modelos de Whisper disponibles

| Modelo   | Velocidad | Precisión | Uso recomendado |
|----------|-----------|-----------|------------------|
| `tiny`   | Muy rápida | Baja | Pruebas rápidas |
| `base`   | Rápida | Media | Uso general (por defecto) |
| `small`  | Media | Buena | Buen equilibrio |
| `medium` | Lenta | Alta | Cuando la precisión importa |
| `large`  | Muy lenta | Máxima | Máxima calidad, requiere más recursos |
| `turbo`  | Rápida | Alta | Alternativa moderna rápida y precisa |

### Recomendación automática según hardware (`core/hardware.py`)

Al abrir la aplicación, el panel **"Hardware detectado"** calcula una
sugerencia de modelo:

- **Con GPU disponible**: usa la VRAM total de la GPU principal y los
  requisitos oficiales de VRAM publicados en el
  [README de openai/whisper](https://github.com/openai/whisper#available-models-and-languages)
  (`tiny`/`base` ~1 GB, `small` ~2 GB, `medium` ~5 GB, `turbo` ~6 GB,
  `large` ~10 GB) para elegir el modelo más potente que entra en esa VRAM.
- **Sin GPU (solo CPU)**: usa la RAM total del sistema. No existe una
  tabla oficial de RAM para CPU, así que se aplica una estimación
  orientativa (el doble del requisito de VRAM de cada modelo, más un
  margen fijo para el sistema operativo).

En ambos casos es solo una sugerencia de partida: el modelo real puede
elegirse libremente en el panel correspondiente.

## Desarrollo y tests

```bash
pip install -r requirements-dev.txt
```

### Ejecutar la suite de tests unitarios

```bash
python3 -m pytest tests/ -v
```

Cubre `core/config.py`, `core/ffmpeg_utils.py`, `core/exporters.py`,
`core/hardware.py` y `core/transcriber.py` (con mocks para
`whisper`/`torch`/`psutil`, por lo que no requieren tener esas
dependencias pesadas instaladas para correr).

### Verificar la interfaz gráfica (smoke test)

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=. python3 tests/smoke_test_gui.py
```

### Test de integración de punta a punta

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=. python3 tests/integration_test_worker.py
```

### Calidad de código

El proyecto sigue PEP 8 / Google Python Style Guide, verificado con:

```bash
black core/ gui/ main.py --check   # Formato
mypy core/ gui/ main.py            # Tipado estático
pylint core/ gui/ main.py          # Linting (10.00/10)
```

## Formatos de exportación

| Formato | Extensión | Contenido |
|---------|-----------|-----------|
| Texto plano | `.txt` | Solo el texto transcrito |
| Markdown | `.md` | Texto + metadatos (modelo, fecha) |
| SRT | `.srt` | Subtítulos con marcas de tiempo (`HH:MM:SS,mmm`) |
| WebVTT | `.vtt` | Subtítulos con marcas de tiempo (`HH:MM:SS.mmm`) |
| JSON | `.json` | Texto, idioma detectado y segmentos con timestamps |

## Notas de arquitectura

- **Separación estricta GUI / lógica**: ningún archivo en `core/` importa
  PySide6 ni ningún otro framework de interfaz. Esto permite testear toda
  la lógica de negocio sin necesidad de un entorno gráfico, y facilita
  construir en el futuro otras interfaces (CLI, web, etc.) reutilizando
  el mismo `core/`.
- **Importación perezosa de `whisper`/`torch`/`psutil`**: estas dependencias
  pesadas se importan dentro de las funciones que las usan, no al nivel de
  módulo, para que `core/transcriber.py` y `core/hardware.py` puedan
  testearse (con mocks) en entornos donde no estén instaladas.
- **Worker en `QThread`**: toda operación potencialmente lenta (carga de
  modelo, transcripción, exportación) ocurre fuera del hilo de la UI, que
  se mantiene siempre responsiva.
- **Progreso sin tocar Whisper**: el porcentaje real de avance se obtiene
  sustituyendo temporalmente la clase `tqdm` que usa `whisper.transcribe`
  internamente (ver `core/transcriber._progress_reporting`), en vez de
  parchear o vendorizar la librería.
