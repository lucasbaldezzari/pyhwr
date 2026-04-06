# Documentación API — `DataManagers`

## Resumen

El módulo `DataManagers.py` define dos clases principales:

- `GHiampDataManager`: lector y organizador de archivos `.hdf5` generados por el amplificador g.HIAMP.
- `LSLDataManager`: lector y organizador de archivos `.xdf` exportados desde LSL, con una capa de interpretación orientada al experimento de handwriting.

A diferencia de un lector genérico, `LSLDataManager` está acoplado al flujo experimental actual: espera mensajes JSON por trial, reconstruye la información por streamer y asume la existencia de streams como `Tablet_Markers` y `Laptop_Markers`.

---

# 1. `GHiampDataManager`

## Propósito

`GHiampDataManager` encapsula la lectura de un archivo HDF5 del g.HIAMP y expone:

- muestras crudas (`raw_data`)
- tiempos de muestra (`times`)
- información de canales (`channels_info`)
- frecuencia de muestreo (`sample_rate`)
- marcadores asíncronos (`markers_info`)
- fecha/hora de registro (`fecha_registro`, `timestamp_registro`)

Su función principal es servir como capa de acceso estructurada a un registro EEG proveniente del amplificador.

## Constructor

```python
GHiampDataManager(filename, subject="Test", normalize_time=True)
```

### Parámetros

- `filename: str`  
  Ruta al archivo `.hdf5`.
- `subject: str`  
  Identificador descriptivo del sujeto. Se usa sólo a nivel de metadatos del objeto.
- `normalize_time: bool`  
  Si `True`, los tiempos se expresan en segundos. Si `False`, se conservan en unidades de muestra.

## Atributos principales

### `filename`
Ruta del archivo fuente.

### `subject`
Etiqueta del sujeto asociada al registro.

### `file_data`
Objeto `h5py.File` con acceso directo al contenido del archivo.

### `raw_data`
Array con las muestras crudas de `RawData/Samples`.

### `channels_info`
Diccionario con dos `DataFrame`:

- `channels_info["used_channels"]`
- `channels_info["device_capabilities"]`

Incluyen nombres de canal, tipo, sample rate, filtros, offset y otras propiedades parseadas desde XML.

### `sample_rate`
Frecuencia de muestreo extraída de `channels_info["used_channels"]["SampleRate"][0]`.

### `markers_info`
Diccionario de marcadores asíncronos. Las claves inicialmente son IDs numéricos y los valores son listas de tiempos.

### `times`
Lista de tiempos para las muestras EEG, construida a partir de `sample_rate`.

### `fecha_registro`, `timestamp_registro`
Fecha/hora del inicio de adquisición extraída de `AcquisitionTaskDescription`.

## Métodos públicos

### `changeMarkersNames(new_names)`

Renombra marcadores en `markers_info`.

```python
gmanager.changeMarkersNames({
    1: "inicioSesión",
    2: "trialTablet",
    3: "penDown",
    4: "trialLaptop"
})
```

#### Parámetros

- `new_names: dict`  
  Diccionario `{id_original: nuevo_nombre}`.

#### Efecto

Reemplaza las claves numéricas existentes por nombres más semánticos.

---

### `__getitem__(key)`

Permite acceso indexado a los marcadores.

#### Forma esperada

```python
gmanager["trialTablet", :]
gmanager["trialTablet", 0:10]
```

#### Retorna

Una lista o sublista de tiempos asociados al marcador solicitado.

#### Observación

Si la clave no existe, retorna `None`.

---

### `__str__()` / `__repr__()`

Devuelve un resumen textual con:

- archivo
- sujeto
- fecha de registro
- frecuencia de muestreo
- cantidad de canales usados
- canales por tipo
- cantidad de eventos
- IDs de marcadores

---

### `__len__()`

Está declarado pero **no implementado** (`pass`).

#### Implicancia

Actualmente no debe asumirse que `len(gmanager)` funcione correctamente.

## Ejemplo de uso

```python
import os
import numpy as np
from pyhwr.managers import GHiampDataManager

path = "D:\\repos\\pyhwr\\test\\data\\gtec_recordings\\full_steup"
lsl_filename = "full_setup_2.hdf5"

gmanager = GHiampDataManager(os.path.join(path, lsl_filename), normalize_time=True)

print("Nombre de los marcadores:", gmanager.markers_info.keys())
print("Tiempos de los marcadores:", gmanager.markers_info.values())

gmanager.changeMarkersNames({1: "inicioSesión", 2: "trialTablet", 3: "penDown", 4: "trialLaptop"})
markers_info = gmanager.markers_info

trials_tablet = np.array(markers_info["trialTablet"])
trials_laptop = np.array(markers_info["trialLaptop"])
```

## Patrón de uso recomendado

`GHiampDataManager` resulta adecuado cuando quieres:

- inspeccionar marcadores del amplificador
- recuperar frecuencia de muestreo
- consultar propiedades de canales
- obtener muestras crudas y construir tu propio pipeline EEG

No incluye todavía métodos de alto nivel para epochs, segmentación o análisis espectral.

## Limitaciones actuales

1. `__len__()` no está implementado.
2. `times` se genera a partir de `sample_rate`, pero no hay API pública para recortar ventanas temporales sobre `raw_data`.
3. No hay integración interna con MNE ni métodos de extracción de eventos al estilo `events`/`annotations`.

---

# 2. `LSLDataManager`

## Propósito

`LSLDataManager` carga un archivo `.xdf` y reconstruye la sesión a partir de streams LSL cuyos samples contienen mensajes JSON por trial. Además de exponer el contenido bruto, agrega una capa semántica para el experimento de handwriting:

- organiza la información por streamer
- arma `trials_info`
- obtiene tiempos relativos por trial
- extrae coordenadas del trazo
- calcula latencias de `penDown`
- ofrece funciones de visualización de trazos

## Constructor

```python
LSLDataManager(filename)
```

### Parámetros

- `filename: str`  
  Ruta al archivo `.xdf`.

## Atributos principales

### `filename`
Ruta del archivo `.xdf`.

### `raw_data`, `header`
Salida directa de `pyxdf.load_xdf(filename)`.

### `streamers_names`
Lista con los nombres de los streams detectados.

### `streamers_keys`
Diccionario `{streamer: [claves_json_detectadas]}` usando el primer sample parseable de cada stream.

### `time_series`
Diccionario `{streamer: [trial_1, trial_2, ...]}` donde cada trial es el JSON parseado de un mensaje LSL.

### `fecha_registro`, `timestamp_registro`
Fecha/hora extraída del header del archivo XDF.

### `trials_info`
Diccionario jerárquico:

```python
{
    "Tablet_Markers": {
        1: {...},
        2: {...},
        ...
    },
    "Laptop_Markers": {
        1: {...},
        2: {...},
        ...
    }
}
```

### `first_lsl_timestamp`
Primer timestamp LSL crudo por stream, tomado del footer del XDF.

### `first_timestamp`
Timestamp del inicio de la primera ronda por streamer. Se calcula con:

```python
self.trials_info[name][1]["sessionStartTime"]
```

### `coordinates_info`
Diccionario con coordenadas por trial provenientes de `Tablet_Markers`.

### `pendown_delays`
Diccionario con el retardo entre `trialCueTime` y el primer `penDown` por trial.

### `trials_times`
Diccionario de `DataFrame` con tiempos relativos por trial y streamer.

### `trials_qty` (property)
Cantidad de trials detectados por streamer.

## Métodos públicos más importantes

### `trialsTimes()`

Retorna un diccionario de `DataFrame`, uno por streamer, con columnas:

- `letter`
- `trialStartTime`
- `trialCueTime`
- `trialRestTime`

Los tiempos quedan expresados en segundos y relativos al `sessionStartTime` del primer trial válido.

```python
trials_times = lsl_manager.trialsTimes()
```

---

### `get_coordinates_info()`

Reconstruye un diccionario de trazos a partir de `Tablet_Markers`.

#### Formato de salida

```python
{
    trialID: {
        "letter": "a",
        "coordinates": [(x, y, t), ...]
    }
}
```

Los tiempos `t` quedan relativizados al primer punto del trazo de ese trial.

---

### `getTrialCoordinates(trialID)`

Retorna las coordenadas de un trial como `numpy.ndarray`.

```python
coords = lsl_manager.getTrialCoordinates(2)
```

Si el trial no existe, retorna `None`.

---

### `describe_trials()`

Devuelve un `DataFrame` resumen con métricas por streamer:

- duración total
- cantidad de trials
- tiempo promedio entre trials
- desvío del tiempo entre trials
- duración promedio del cue
- desvío de la duración del cue
- conjunto de letras registradas

```python
summary = lsl_manager.describe_trials()
print(summary)
```

---

### `get_pendownDelays()`

Calcula, para cada trial de `Tablet_Markers`, la diferencia entre:

- `trialCueTime`
- primer elemento de `penDownMarkers`

Retorna un diccionario:

```python
{
    trialID: {
        "letter": "a",
        "delay": 0.742
    }
}
```

Si no hubo `penDown`, el delay queda en `None`.

---

### `infoTrial(trialID)`

Devuelve un diccionario resumen de un trial de tablet.

#### Incluye

- `letter`
- `trialStartTime`
- `trialCueTime`
- `trialRestTime`
- `pendowns`
- `penups`
- `writing_duration`
- `pendown_delay`

Todos los tiempos quedan expresados en segundos relativos al comienzo de la sesión del streamer `Tablet_Markers`, salvo que la duración de escritura se toma desde las coordenadas del trazo.

```python
trial_info = lsl_manager.infoTrial(20)
```

---

### `lettersTrials(letter)`

Retorna dos listas:

```python
laptop_ids, tablet_ids = lsl_manager.lettersTrials("a")
```

La primera contiene trials de `Laptop_Markers` y la segunda de `Tablet_Markers` para la letra solicitada.

---

### `plot_traces(...)`

Grafica el trazo de un trial individual.

```python
fig, ax = lsl_manager.plot_traces(
    7,
    line_color="#12259d",
    show=False
)
```

#### Parámetros más útiles

- `trialID`
- `title`
- `filename`
- `show`
- `save`
- `figsize`
- `line_color`, `line_width`
- `point_color`, `point_size`
- `hide_title`, `hide_axes`, `hide_ticks`, `hide_labels`, `hide_spines`

#### Retorna

```python
(fig, ax)
```

---

### `plot_all_traces(...)`

Grafica todos los trazos de `Tablet_Markers` sobre una grilla donde:

- cada columna corresponde a una letra
- cada fila corresponde a un trial de esa letra

```python
fig, axes = lsl_manager.plot_all_traces(
    figsize=(25, 10),
    line_color="#040508",
    point_color="#ffffff",
    point_size=5,
    hide_title=True,
    hide_axes=True,
    hide_ticks=True,
    hide_labels=True,
    hide_spines=True,
    show=False
)
fig.show()
```

#### Retorna

```python
(fig, axes)
```

---

### `__getitem__(key)`

Permite acceso indexado a valores concretos por streamer y label.

#### Forma esperada

```python
lsl_manager["Tablet_Markers", "trialStartTime", :]
lsl_manager["Laptop_Markers", "letter", :]
lsl_manager["Tablet_Markers", "coordinates", 0]
```

#### Semántica

1. selecciona el streamer
2. filtra los trials que contienen `label`
3. aplica slicing/indexing sobre la lista resultante

#### Observación importante

El acceso se hace por presencia de label, no por `trialID` directo. Es decir, el tercer elemento indexa la secuencia filtrada, no necesariamente el `trialID` lógico.

---

### `__str__()` / `__repr__()`

Devuelve un resumen con:

- archivo
- fecha de registro
- timestamp inicial
- streamers detectados
- número de marcadores por streamer
- letras observadas por streamer

---

### `__len__()`

Retorna la cantidad de streamers detectados.

```python
n_streamers = len(lsl_manager)
```

## Ejemplo de uso

```python
import os
from pyhwr.managers import LSLDataManager

path = "test\\data\\pruebas_piloto\\testeo_marcadores\\"
lsl_filename = "sub-contrazos_ses-03_task-ejecutada_run-01_eeg.xdf"

lsl_manager = LSLDataManager(os.path.join(path, lsl_filename))

print(lsl_manager.streamers_names)
print(lsl_manager.describe_trials())
print(lsl_manager.pendown_delays)

lsl_manager.coordinates_info[1]["letter"]
lsl_manager.getTrialCoordinates(2)
lsl_manager.trialsTimes()
lsl_manager.lettersTrials("a")
lsl_manager.infoTrial(20)

fig, axes = lsl_manager.plot_traces(7, line_color="#12259d", show=False)

fig, axes = lsl_manager.plot_all_traces(
    figsize=(25, 10),
    line_color="#040508",
    point_color="#ffffff",
    point_size=5,
    hide_title=True,
    hide_axes=True,
    hide_ticks=True,
    hide_labels=True,
    hide_spines=True,
    show=False
)
fig.show()
del fig, axes
```

## Patrón de uso recomendado

`LSLDataManager` es apropiado cuando quieres:

- inspeccionar el orden y contenido de los streamers LSL
- comparar marcas laptop/tablet
- obtener tiempos relativos por trial
- reconstruir trazos `(x, y, t)`
- medir latencia cue → penDown
- agrupar trials por letra
- generar figuras de trazos para reportes o control de calidad

## Relación con el resto de la arquitectura

Esta clase no trabaja sobre cualquier XDF arbitrario. Está alineada con el flujo actual del experimento:

1. `SessionManager` controla fases, runs, letras y tiempos de trial.
2. `TabletMessenger` envía mensajes JSON por ADB a Android.
3. `MainActivity` recibe esos mensajes, sincroniza tiempos y persiste la información del trial.
4. Los streamers LSL terminan guardando mensajes JSON por trial que luego `LSLDataManager` vuelve a parsear.

Por eso `LSLDataManager` espera campos como:

- `sessionStartTime`
- `sessionFinalTime`
- `trialStartTime`
- `trialCueTime`
- `trialRestTime`
- `penDownMarkers`
- `penUpMarkers`
- `coordinates`
- `letter`
- `trialID`

## Limitaciones y advertencias

### 1. Acoplamiento fuerte a nombres de streamer

La clase asume la existencia de:

- `Tablet_Markers`
- `Laptop_Markers`

Si esos nombres cambian, varios métodos dejan de funcionar.

### 2. Supuesto frágil sobre el primer trial válido

`first_timestamp` usa:

```python
self.trials_info[name][1]["sessionStartTime"]
```

Esto supone que el primer trial válido tiene clave `1`. Si el trial 1 fue filtrado o está vacío, la lógica puede fallar.

### 3. `streamers_keys` depende del primer mensaje parseable

Las keys de cada streamer se infieren a partir del primer `time_series[0][0]`. Si ese sample está vacío o incompleto, las claves inferidas pueden ser incorrectas.

### 4. `describe_trials()` y otros métodos no son agnósticos al experimento

La implementación está pensada para un paradigma concreto donde existen eventos de cue, rest y escritura. No es una capa genérica de análisis LSL.

### 5. Posibles diferencias de escala temporal

En la arquitectura actual, la sincronización PC/tablet depende del contrato entre `SessionManager`, `TabletMessenger` y `MainActivity`. Si algún timestamp persistido por Android no queda en la misma base temporal, los cálculos derivados en `LSLDataManager` pueden resultar inconsistentes.

---

# 3. Guía rápida de uso

## Caso A — inspeccionar HDF5 del g.HIAMP

```python
from pyhwr.managers import GHiampDataManager

manager = GHiampDataManager("registro.hdf5", normalize_time=True)
print(manager)
print(manager.sample_rate)
print(manager.channels_info["used_channels"].head())
print(manager.markers_info)
```

## Caso B — renombrar marcadores del amplificador

```python
manager.changeMarkersNames({
    1: "sessionStarted",
    2: "trialLaptop",
    3: "trialTablet",
    4: "penDown"
})

print(manager["trialLaptop", :])
```

## Caso C — resumir una sesión XDF

```python
from pyhwr.managers import LSLDataManager

lsl = LSLDataManager("registro.xdf")
print(lsl.streamers_names)
print(lsl.describe_trials())
print(lsl.trials_qty)
```

## Caso D — obtener coordenadas y latencias

```python
coords = lsl.getTrialCoordinates(5)
trial_info = lsl.infoTrial(5)
delays = lsl.pendown_delays
```

## Caso E — graficar trazos

```python
fig, ax = lsl.plot_traces(5, show=False)
fig.show()

fig, axes = lsl.plot_all_traces(show=False)
fig.show()
```

---

# 4. Recomendaciones de mejora de API

## Para `GHiampDataManager`

1. Implementar `__len__()`.
2. Agregar un método público para recuperar ventanas temporales de `raw_data`.
3. Exponer un método `get_events()` que devuelva eventos en un formato más cercano a MNE.
4. Agregar validaciones del contenido HDF5 y mensajes de error más explícitos.

## Para `LSLDataManager`

1. Desacoplar los nombres fijos `Tablet_Markers` y `Laptop_Markers`.
2. Hacer robusta la detección del primer trial válido.
3. Separar lectura genérica de XDF de la lógica específica del experimento.
4. Agregar typing y validaciones de estructura JSON.
5. Corregir la dependencia implícita del primer sample para inferir `streamers_keys`.

---

# 5. Conclusión

`GHiampDataManager` y `LSLDataManager` cumplen roles distintos pero complementarios:

- `GHiampDataManager` organiza el registro neurofisiológico del amplificador.
- `LSLDataManager` reconstruye la semántica experimental de la sesión y facilita análisis conductuales y visualización de escritura.

En su estado actual, ambos son útiles y prácticos dentro de tu pipeline, pero `LSLDataManager` debe entenderse más como una capa especializada para tu paradigma de handwriting que como una API universal para archivos XDF.
