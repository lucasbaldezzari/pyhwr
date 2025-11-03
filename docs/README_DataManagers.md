# 📘 DataManagers — Módulo de Gestión de Datos EEG y LSL

Este módulo proporciona herramientas para gestionar y analizar datos provenientes de:
- **Amplificadores g.HIAMP** (`.hdf5`)
- **Streams de LSL (Lab Streaming Layer)** (`.xdf`)

Incluye clases y métodos para extraer, procesar y representar información relevante de los registros de EEG y eventos asociados.

---

## Contenido del Módulo

- [GHiampDataManager](#ghiampdatamanager)
  - [Inicialización](#inicialización-de-ghiampdatamanager)
  - [Métodos principales](#métodos-principales-ghiamp)
  - [Ejemplo de uso](#ejemplo-de-uso-ghiamp)
- [LSLDataManager](#lsldatamanager)
  - [Inicialización](#inicialización-de-lsldatamanager)
  - [Métodos principales](#métodos-principales-lsl)
  - [Ejemplo de uso](#ejemplo-de-uso-lsl)
- [Ejemplo completo](#ejemplo-completo)

---

## `GHiampDataManager`

Clase para gestionar los datos registrados desde el **amplificador g.HIAMP** (archivos `.hdf5`).

### Inicialización de `GHiampDataManager`

```python
GHiampDataManager(
    filename: str,
    subject: str = "Test",
    normalize_time: bool = True
)
```

**Parámetros:**

| Parámetro | Tipo | Descripción |
|------------|------|-------------|
| `filename` | `str` | Ruta al archivo `.hdf5` con los datos de registro. |
| `subject` | `str` | Nombre del sujeto o etiqueta del registro. |
| `normalize_time` | `bool` | Si `True`, los tiempos de los marcadores se normalizan a segundos. |

**Atributos automáticos:**

- `file_data`: instancia de `h5py.File`
- `raw_data`: matriz de muestras (`EEG`)
- `channels_info`: información sobre los canales usados y disponibles
- `markers_info`: diccionario con los marcadores del experimento
- `times`: array con los tiempos normalizados
- `fecha_registro`, `timestamp_registro`: fecha y timestamp local del registro
- `sample_rate`: frecuencia de muestreo (Hz)

---

### Métodos principales (GHiamp)

#### `._get_channels_info()`
Obtiene información sobre los canales usados (`AcquisitionTaskDescription`) y disponibles (`DAQDeviceCapabilities`).

**Retorna:**
```python
{
  "used_channels": pd.DataFrame,
  "device_capabilities": pd.DataFrame
}
```

---

#### `._get_samples()`
Lee los datos de EEG contenidos en `"RawData/Samples"` del archivo HDF5.

**Retorna:** `np.ndarray`

---

#### `._get_times(tinit=0, tend=None)`
Genera los tiempos de las muestras basados en la frecuencia de muestreo.

**Retorna:** `list[float]` (en segundos)

---

#### `._get_markers_info()`
Obtiene los marcadores del experimento (por ID), normalizando los tiempos si se indica.

**Retorna:** `dict[int, list[float]]`

---

#### `.changeMarkersNames(new_names: dict)`
Permite renombrar los marcadores existentes.

**Ejemplo:**
```python
ghiamp.changeMarkersNames({
    1: "sessionStarted",
    2: "trialLaptop",
    3: "trialTablet"
})
```

---

#### `.__getitem__(key)`
Permite indexar marcadores directamente.

```python
ghiamp["trialLaptop", :]
ghiamp["trialTablet", 0:10]
```

**Retorna:** lista de tiempos asociados al marcador.

---

#### `.__str__()` / `.__repr__()`
Representación legible del objeto, mostrando resumen de canales, frecuencia, marcadores, etc.

---

### Ejemplo de uso (GHiamp)

```python
from DataManagers import GHiampDataManager

filename = "data/session_01.hdf5"
ghiamp = GHiampDataManager(filename, subject="P01", normalize_time=True)

print(ghiamp)

# Acceso a datos
samples = ghiamp.raw_data
channels = ghiamp.channels_info["used_channels"]
print(channels.head())

# Marcadores
ghiamp.changeMarkersNames({1: "start", 2: "stimulus"})
print(ghiamp["start", :])
```

---

## 🌐 `LSLDataManager`

Clase para gestionar los datos provenientes de **Lab Streaming Layer** (archivos `.xdf`).

### Inicialización de `LSLDataManager`

```python
LSLDataManager(filename: str)
```

**Parámetros:**

| Parámetro | Tipo | Descripción |
|------------|------|-------------|
| `filename` | `str` | Ruta al archivo `.xdf` generado por LSL. |

**Atributos automáticos:**

- `raw_data`, `header`: datos crudos y metadatos del XDF
- `streamers_names`: nombres de los streams detectados
- `streamers_keys`: claves o etiquetas dentro de cada stream
- `time_series`: series temporales decodificadas por stream
- `fecha_registro`, `timestamp_registro`: fecha y hora del registro
- `first_timestamp`: timestamps iniciales por stream

---

### Métodos principales (LSL)

#### `._get_streamers_names()`
Devuelve los nombres de los streams registrados en el archivo XDF.

```python
['Tablet_Markers', 'Laptop_Markers', 'EEG_Stream']
```

---

#### `._get_streamers_keys()`
Devuelve un diccionario con las claves disponibles en cada stream.

```python
{
  "Tablet_Markers": ["trialStartTime", "coordinates"],
  "Laptop_Markers": ["trialStartTime", "letter"]
}
```

---

#### `._get_timeseries()`
Extrae la serie temporal completa de cada stream, parseando los mensajes JSON.

---

#### `._parse_trial_message(raw)`
Decodifica un mensaje JSON en formato bytes o string.

**Ejemplo:**
```python
raw = '{"trialStartTime": 12.45, "letter": "A"}'
lsl._parse_trial_message(raw)
# {'trialStartTime': 12.45, 'letter': 'A'}
```

---

#### `.__getitem__(key)`
Permite acceso directo a los datos por stream, etiqueta y rango:

```python
lsl["Laptop_Markers", "letter", :]
lsl["Tablet_Markers", "coordinates", 0:5]
```

**Retorna:** lista o array con los valores solicitados.

---

#### `.__str__()` / `.__repr__()`
Muestra resumen del archivo `.xdf`, incluyendo streams, cantidad de trials y marcadores.

---

### Ejemplo de uso (LSL)

```python
from DataManagers import LSLDataManager

filename = "data/subj01_task-default.xdf"
lsl = LSLDataManager(filename)

print(lsl)

# Streams y claves
print(lsl.streamers_names)
print(lsl.streamers_keys)

# Acceso a los tiempos de trials
times = lsl["Laptop_Markers", "trialStartTime", :]
letters = lsl["Laptop_Markers", "letter", :]

print(f"Trials: {len(times)} | Letras: {letters}")
```

---

## 🧩 Ejemplo completo

```python
from DataManagers import GHiampDataManager, LSLDataManager
import numpy as np

# --- G.HIAMP ---
ghiamp = GHiampDataManager("recordings/session_01.hdf5", normalize_time=True)
ghiamp.changeMarkersNames({1: "start", 2: "stimulus"})
print(ghiamp)

# --- LSL ---
lsl = LSLDataManager("recordings/sub-01_task-Default.xdf")
print(lsl)

# Sincronización de eventos
laptop_start = lsl["Laptop_Markers", "sessionStartTime", :][0]
trial_times = np.array(lsl["Laptop_Markers", "trialStartTime", :])

print("Inicio de sesión:", laptop_start)
print("Promedio entre trials:", np.diff(trial_times).mean())
```

---

## 🧾 Créditos y dependencias

**Dependencias:**
```bash
pip install pyxdf h5py numpy pandas
```

**Módulos estándar utilizados:**
- `datetime`, `json`, `xml.etree.ElementTree`
- `matplotlib` (solo para pruebas)
