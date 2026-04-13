# DataManagers

## Descripción general

El módulo `DataManagers.py` reúne dos clases de acceso a datos orientadas a la post-adquisición dentro de la arquitectura experimental:

- `GHiampDataManager`: lectura y organización de archivos `.hdf5` generados por el amplificador g.HIAMP.
- `LSLDataManager`: lectura y estructuración de archivos `.xdf` con streams registrados mediante Lab Streaming Layer (LSL).

Ambas clases cumplen funciones distintas. `GHiampDataManager` se enfoca en señales y marcadores almacenados por el sistema de adquisición del amplificador, mientras que `LSLDataManager` reconstruye la lógica del experimento a partir de streams de marcadores y payloads JSON emitidos durante la sesión.

El módulo no constituye una capa de abstracción completamente homogénea para cualquier fuente de datos. En la práctica, cada clase refleja el formato, las convenciones y los supuestos de la arquitectura experimental vigente.

---

## Ubicación dentro de la arquitectura

El módulo se sitúa en la etapa de análisis o inspección offline. No participa en el control en tiempo real de la sesión, pero consume artefactos producidos por otros componentes del sistema:

- `SessionManager` y `PreExperimentManager` generan el flujo temporal del experimento.
- `MarkerManager` publica marcadores LSL.
- `TabletMessenger`, `PCMessenger`, `MainActivity`, `EventManager` y `touchView` definen el contrato funcional de los payloads que terminan almacenados en los streams o en los JSON de trial.

Como consecuencia, `LSLDataManager` depende fuertemente del esquema de datos producido por esa arquitectura. No debe describirse como lector XDF genérico, sino como lector especializado para este pipeline experimental.

---

## Dependencias

El módulo utiliza las siguientes bibliotecas:

- `pyxdf`
- `h5py`
- `json`
- `numpy`
- `pandas`
- `matplotlib`
- `xml.etree.ElementTree`
- `datetime`
- `collections.defaultdict`

---

## Clase `GHiampDataManager`

### Propósito

`GHiampDataManager` encapsula la lectura de archivos `.hdf5` generados por g.HIAMP y expone una interfaz orientada a:

- acceder a las muestras crudas del amplificador,
- recuperar metadatos de canales,
- reconstruir los tiempos de muestreo,
- obtener la fecha/hora de registro,
- organizar los marcadores asíncronos del archivo.

### Constructor

```python
GHiampDataManager(filename, subject="Test", normalize_time=True)
```

### Parámetros

- `filename`: ruta al archivo `.hdf5`.
- `subject`: identificador textual del sujeto, usado sólo como metadato descriptivo.
- `normalize_time`: si es `True`, los tiempos se expresan en segundos; en caso contrario, se expresan en muestras.

### Inicialización

Durante la construcción del objeto se cargan y derivan automáticamente los siguientes elementos:

- `file_data`: manejador HDF5 abierto.
- `fecha_registro`, `timestamp_registro`: fecha/hora del registro, inferida desde el XML interno del archivo.
- `raw_data`: matriz de muestras de `RawData/Samples`.
- `channels_info`: resumen de canales usados y capacidades del dispositivo.
- `sample_rate`: frecuencia de muestreo inferida desde la descripción de canales usados.
- `markers_info`: diccionario de marcadores asíncronos.
- `times`: vector temporal de las muestras.

### Atributos principales

- `filename`
- `subject`
- `file_data`
- `normalize_time`
- `fecha_registro`
- `timestamp_registro`
- `raw_data`
- `channels_info`
- `sample_rate`
- `markers_info`
- `times`

### Métodos principales

#### `_read_data(filename)`
Abre el archivo `.hdf5` con `h5py.File`.

#### `_get_channels_info()`
Reconstruye dos tablas de canales a partir de XML internos:

- `used_channels`: configuración utilizada en la adquisición.
- `device_capabilities`: capacidades declaradas por el dispositivo.

#### `_resume_channels_from_xml(xml_bytes, root_tag="ChannelProperties")`
Parsea un bloque XML y lo convierte en `pandas.DataFrame`, con conversiones básicas de tipos numéricos y booleanos.

#### `_get_samples()`
Recupera las muestras crudas desde `RawData/Samples`.

#### `_get_times(tinit=0, tend=None)`
Construye el eje temporal de las muestras a partir de `sample_rate`.

#### `_get_markers_info()`
Recupera los marcadores almacenados en `AsynchronData`, reindexa los `TypeID` para comenzar en `1` y devuelve un diccionario donde cada clave corresponde a un marcador y cada valor es la lista de tiempos asociados.

#### `changeMarkersNames(new_names)`
Renombra claves existentes de `markers_info`.

#### `_get_datetime()`
Extrae la fecha de inicio del registro desde el XML de `AcquisitionTaskDescription`, la interpreta en UTC y la convierte a UTC-3.

#### `__getitem__((time_mark, idx))`
Permite indexar tiempos de marcadores de forma compacta.

Ejemplos:

```python
gmanager["trialTablet", :]
gmanager["penDown", 0:10]
```

#### `__str__()` / `__repr__()`
Generan un resumen textual del archivo, sujeto, frecuencia, canales y marcadores disponibles.

#### `__len__()`
Está declarado, pero no implementado actualmente.

### Ejemplo de uso

```python
import os
import numpy as np
from pyhwr.managers import GHiampDataManager

path = "D:\\repos\\pyhwr\\test\\data\\gtec_recordings\\full_steup"
filename = "full_setup_2.hdf5"

gmanager = GHiampDataManager(os.path.join(path, filename), normalize_time=True)

print("Nombre de los marcadores:", gmanager.markers_info.keys())
print("Tiempos de los marcadores:", gmanager.markers_info.values())

gmanager.changeMarkersNames({1: "inicioSesión", 2: "trialTablet", 3: "penDown", 4: "trialLaptop"})

markers_info = gmanager.markers_info
trials_tablet = np.array(markers_info["trialTablet"])
trials_laptop = np.array(markers_info["trialLaptop"])
```

### Observaciones de diseño

- La clase se comporta como lector estructurado de archivos g.HIAMP, no como wrapper universal de HDF5.
- La fecha de registro depende de la presencia de `RecordingDateBegin` en el XML interno.
- El método `__len__()` quedó pendiente de implementación.
- El reindexado de marcadores en `_get_markers_info()` modifica los `TypeID` originales para hacerlos comenzar en `1`; esto debe tenerse en cuenta si se desea comparar contra identificadores externos sin normalizar.

---

## Clase `LSLDataManager`

### Propósito

`LSLDataManager` encapsula la lectura de archivos `.xdf` registrados con LSL y reconstruye una representación estructurada de los streams presentes, con énfasis en los streams de marcadores generados por laptop y tablet durante el experimento.

Además de leer datos crudos, la clase agrega lógica de conveniencia para:

- resumir trials,
- calcular tiempos relativos,
- extraer coordenadas de escritura,
- estimar latencias de inicio de trazo,
- consultar trials por letra,
- visualizar trazos individuales o agrupados.

### Constructor

```python
LSLDataManager(filename)
```

### Parámetros

- `filename`: ruta al archivo `.xdf`.

### Inicialización

Durante la construcción del objeto se generan automáticamente:

- `raw_data`, `header`: contenido crudo del archivo XDF.
- `streamers_names`: nombres de los streams detectados.
- `streamers_keys`: claves disponibles por streamer.
- `time_series`: contenido parseado de cada stream.
- `fecha_registro`, `timestamp_registro`: fecha/hora del archivo XDF.
- `trials_info`: información organizada por streamer y trial.
- `first_lsl_timestamp`: primer timestamp interno de LSL por streamer.
- `first_timestamp`: timestamp del inicio de la primera ronda por streamer.
- `coordinates_info`: trazos reconstruidos desde `Tablet_Markers`.
- `pendown_delays`: latencia entre cue y primer `penDown`.
- `trials_times`: dataframes con tiempos relativos por streamer.

### Atributos principales

- `filename`
- `raw_data`
- `header`
- `streamers_names`
- `streamers_keys`
- `time_series`
- `fecha_registro`
- `timestamp_registro`
- `trials_info`
- `first_lsl_timestamp`
- `first_timestamp`
- `coordinates_info`
- `pendown_delays`
- `trials_times`

### Propiedades y métodos principales

#### `_read_data(filename)`
Carga el archivo con `pyxdf.load_xdf`.

#### `_parse_trial_message(raw)`
Normaliza y parsea el contenido JSON almacenado en cada muestra de `time_series`.

#### `_get_streamers_names()`
Obtiene los nombres de los streams presentes en el archivo.

#### `_get_streamers_keys()`
Inspecciona el primer mensaje de cada stream para inferir sus claves.

#### `trials_qty`
Propiedad que retorna la cantidad de trials por streamer.

#### `_get_timeseries()`
Recorre el contenido de cada streamer y devuelve una estructura parseada a nivel de mensajes.

#### `trialsTimes()`
Construye un diccionario de `DataFrame` con tiempos relativos por streamer. Cada tabla incluye:

- `letter`
- `trialStartTime`
- `trialCueTime`
- `trialRestTime`

Todos los tiempos se expresan relativos al `sessionStartTime` de la primera ronda detectada para ese streamer.

#### `get_coordinates_info()`
Reconstruye un diccionario indexado por `trialID` con:

- `letter`
- `coordinates`: lista de ternas `(x, y, t)`

Los tiempos de coordenadas se normalizan restando el primer timestamp del trazo.

#### `getTrialCoordinates(trialID)`
Devuelve las coordenadas de un trial como `numpy.ndarray`.

#### `_get_datetime()`
Recupera la fecha/hora del archivo XDF a partir del header.

#### `_get_first_lsl_timestamp()`
Extrae el primer timestamp LSL almacenado en el footer de cada stream.

#### `_get_first_run_timestamp()`
Toma `sessionStartTime` del trial con índice `1` en cada streamer y lo considera como inicio de la primera ronda.

#### `_get_trials_info()`
Organiza los trials por streamer y filtra entradas vacías.

#### `describe_trials()`
Retorna un `DataFrame` con estadísticas resumidas por dispositivo, incluyendo:

- duración total,
- cantidad de trials,
- tiempo medio entre trials,
- tiempo medio de cue,
- letras presentadas.

#### `get_pendownDelays()`
Calcula la demora entre `trialCueTime` y el primer `penDown` para cada trial de `Tablet_Markers`.

#### `infoTrial(trialID)`
Devuelve un diccionario con información consolidada de un trial específico de tablet, incluyendo:

- letra,
- tiempos relativos de inicio, cue y rest,
- `penDownMarkers`,
- `penUpMarkers`,
- `writing_duration`,
- `pendown_delay`.

#### `lettersTrials(letter)`
Retorna dos listas de `trialID`, una para `Laptop_Markers` y otra para `Tablet_Markers`, correspondientes a la letra solicitada.

#### `is_none_like(coordinates)`
Ayuda a identificar valores equivalentes a `None` en coordenadas.

#### `plot_traces(...)`
Grafica el trazo correspondiente a un trial individual.

#### `plot_all_traces(...)`
Grafica todos los trazos de `Tablet_Markers`, organizados en una grilla por letra y trial.

#### `__getitem__((streamer, label, idx))`
Permite acceso abreviado a valores internos del stream.

Ejemplos:

```python
lsl_manager["Laptop_Markers", "letter", :]
lsl_manager["Tablet_Markers", "trialStartTime", 0:5]
```

#### `__str__()` / `__repr__()`
Generan un resumen textual del archivo, streamers y trials disponibles.

#### `__len__()`
Retorna la cantidad de streamers detectados.

### Ejemplo de uso

```python
import os
from pyhwr.managers import LSLDataManager

path = "test\\data\\pruebas_piloto\\testeo_marcadores\\"
filename = "sub-contrazos_ses-03_task-ejecutada_run-01_eeg.xdf"

lsl_manager = LSLDataManager(os.path.join(path, filename))

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
    show=False,
)
fig.show()
```

### Observaciones de diseño

- La clase asume la existencia de streams con nombres específicos, especialmente `Tablet_Markers` y `Laptop_Markers`.
- La reconstrucción de coordenadas depende de que `Tablet_Markers` incluya una clave `coordinates` con la estructura esperada.
- `_get_first_run_timestamp()` asume que el trial con clave `1` existe y es válido para cada streamer.
- `streamers_keys` se infiere a partir del primer mensaje parseado del stream; si dicho mensaje es vacío o no tiene la estructura esperada, la inferencia puede fallar.
- La clase contiene lógica específica del paradigma de escritura a mano alzada; por eso no debe documentarse como lector XDF agnóstico al experimento.
- `get_pendownDelays()` contiene una instrucción `print(...)` de depuración que conviene remover en una versión estable.
- `infoTrial()` utiliza principalmente información del streamer de tablet y no pretende representar una fusión perfecta laptop/tablet.

---

## Relación entre ambas clases

Aunque ambas pertenecen al mismo módulo, no implementan una interfaz formal común.

- `GHiampDataManager` está centrada en señales y marcadores almacenados por el amplificador.
- `LSLDataManager` está centrada en marcadores, eventos, tiempos de trial y trazos registrados por el ecosistema LSL.

El uso combinado de ambas puede resultar útil para contrastar:

- tiempos del amplificador versus tiempos LSL,
- marcadores del hardware versus marcadores de software,
- eventos de cue y `penDown` versus trazos reales capturados en tablet.

---

## Limitaciones conocidas

1. `GHiampDataManager.__len__()` no está implementado.
2. `LSLDataManager` depende de nombres de streamers y claves JSON altamente específicas.
3. Varias funciones de `LSLDataManager` presuponen que existe al menos un trial válido con datos útiles.
4. El módulo mezcla responsabilidades de lectura, transformación, resumen y visualización, lo que vuelve más difícil su extensión futura.

---

## Recomendaciones de evolución

- Implementar `__len__()` en `GHiampDataManager`.
- Separar la lectura de datos de la capa de visualización en `LSLDataManager`.
- Introducir validaciones explícitas de schema para streams y payloads JSON.
- Reducir los supuestos rígidos sobre nombres de streamers.
- Definir una interfaz base compartida si se desea homogeneizar el acceso entre fuentes de datos.
- Considerar clases auxiliares específicas para métricas conductuales y plotting.

---

## Resumen

`DataManagers.py` constituye la capa de acceso offline a los datos principales del sistema. Su diseño actual es funcional y pragmático: prioriza resolver el pipeline experimental concreto antes que ofrecer una abstracción general. La documentación y el uso de este módulo deben reflejar esa realidad para evitar expectativas incorrectas sobre su grado de generalidad.
