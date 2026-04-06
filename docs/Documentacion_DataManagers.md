# Documentación técnica de `DataManagers.py`

## 1. Propósito general del módulo

El módulo `DataManagers.py` define dos clases orientadas a la lectura, organización y consulta de datos experimentales registrados por dos vías distintas del sistema: `GHiampDataManager`, para archivos `.hdf5` provenientes del amplificador g.HIAMP, y `LSLDataManager`, para archivos `.xdf` registrados mediante Lab Streaming Layer (LSL). En conjunto, estas clases constituyen la capa de acceso a datos offline del experimento. fileciteturn12file0

Dentro de la arquitectura general, `SessionManager` genera y emite marcadores de laptop y tablet a través de LSL, mientras que la tablet Android registra información de trials, coordenadas y eventos de lápiz; luego `DataManagers.py` permite reconstruir y analizar esos datos desde los archivos persistidos. fileciteturn11file16 fileciteturn11file11 fileciteturn11file15 fileciteturn11file18

## 2. Dependencias del módulo

El archivo importa `pyxdf`, `h5py`, `json`, `numpy`, `pandas`, `matplotlib`, `datetime`, `collections.defaultdict` y `xml.etree.ElementTree`. Esto revela que el módulo está diseñado para: cargar archivos binarios de adquisición, parsear metadatos XML embebidos, manipular datos tabulares, realizar cálculos numéricos y producir visualizaciones de los trazos registrados. fileciteturn12file0

## 3. Clase `GHiampDataManager`

### 3.1 Objetivo

`GHiampDataManager` encapsula la lectura y consulta de un archivo `.hdf5` generado por el amplificador g.HIAMP. Su responsabilidad principal es exponer de manera estructurada las muestras crudas, la información de canales, los tiempos de muestra, los marcadores asíncronos y la fecha de adquisición. fileciteturn12file0

### 3.2 Constructor

Firma:

```python
GHiampDataManager(filename, subject="Test", normalize_time=True)
```

Parámetros:
- `filename`: ruta al archivo `.hdf5`.
- `subject`: identificador del sujeto, usado sólo como metadato descriptivo interno.
- `normalize_time`: si es `True`, normaliza tiempos a segundos; si es `False`, deja los tiempos en unidades de muestra. fileciteturn12file0

Durante la inicialización, la clase realiza toda la carga principal: abre el archivo HDF5, obtiene la fecha de registro, extrae las muestras, obtiene la información de canales, infiere la frecuencia de muestreo desde `used_channels["SampleRate"][0]`, reconstruye los marcadores y genera el vector temporal. Es decir, el constructor deja el objeto listo para consulta inmediata. fileciteturn12file0

### 3.3 Atributos principales

Después de construir la instancia, quedan disponibles estos atributos de interés:
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
- `times` fileciteturn12file0

### 3.4 Métodos internos y comportamiento

#### `_read_data(filename)`
Abre el archivo con `h5py.File(filename, "r")` y retorna el manejador HDF5. No implementa validaciones adicionales ni manejo explícito de errores de apertura. fileciteturn12file0

#### `_get_channels_info()`
Lee dos bloques XML desde el HDF5: `RawData/AcquisitionTaskDescription` y `RawData/DAQDeviceCapabilities`. Ambos se parsean mediante `_resume_channels_from_xml(...)` para devolver dos `DataFrame`:
- `used_channels`: canales realmente usados en la adquisición.
- `device_capabilities`: canales disponibles según el dispositivo. fileciteturn12file0

La salida se organiza como un diccionario con esas dos entradas. El código muestra que existió la intención de construir además una tabla de correspondencia (`df_match`) por `PhysicalChannelNumber`, pero ese bloque quedó comentado. fileciteturn12file0

#### `_resume_channels_from_xml(xml_bytes, root_tag="ChannelProperties")`
Convierte XML a `DataFrame`. Soporta dos estructuras explícitas:
- `AcquisitionTaskDescription` → busca `.//ChannelProperties/ChannelProperties`
- `DAQDeviceCapabilities` → busca `.//AnalogChannelProperties/ChannelProperties` fileciteturn12file0

Además realiza conversión de tipos:
- columnas numéricas a `float/int` usando `pd.to_numeric`
- columnas booleanas (`IsBipolar`, `IsTriggerChannel`) a `True/False` mediante mapeo de strings. fileciteturn12file0

#### `_get_samples()`
Devuelve `self.file_data["RawData"]["Samples"][:]`, es decir, la matriz completa de muestras almacenadas en el archivo. fileciteturn12file0

#### `_get_times(tinit=0, tend=None)`
Construye el eje temporal de las muestras a partir de `n_samples` y `sample_rate` usando `np.linspace(..., endpoint=False)`. Aunque recibe `tinit` y `tend`, en la implementación actual `tinit` no se usa y `tend` sólo se usa para calcular un valor por defecto, pero luego no afecta la construcción del vector; en la práctica, el método genera siempre el vector temporal completo desde cero. fileciteturn12file0

#### `_get_markers_info()`
Extrae marcadores desde `AsynchronData/TypeID` y `AsynchronData/Time`. Reescala los `TypeID` para que comiencen en `1`, agrupa los tiempos por ID y devuelve un diccionario `marker_id -> lista de tiempos`. Si `normalize_time=True`, divide los tiempos por la frecuencia de muestreo para expresarlos en segundos; si no, los deja en la escala original. fileciteturn12file0

#### `changeMarkersNames(new_names)`
Permite reemplazar claves numéricas de `markers_info` por nombres más descriptivos. Modifica `self.markers_info` in-place. fileciteturn12file0

#### `_get_datetime()`
Busca el tag `<RecordingDateBegin>` dentro del XML de adquisición, lo parsea como UTC, lo convierte a UTC-3 y devuelve tanto el `datetime` localizado como su timestamp. Si no encuentra el tag, retorna `(None, None)`. fileciteturn12file0

### 3.5 Métodos especiales

#### `__getitem__(key)`
Permite indexar marcadores con la sintaxis:

```python
manager["time_mark", :]
manager["time_mark", 0:20]
```

El formato esperado es una tupla de longitud 2: `(time_mark, idx)`. Si la clave no existe, retorna `None`. Esto vuelve cómoda la consulta rápida de tiempos de marcadores. fileciteturn12file0

#### `__str__()` y `__repr__()`
Devuelven un resumen textual con archivo, sujeto, fecha, frecuencia de muestreo, cantidad de canales usados, canales por tipo, cantidad total de eventos e IDs de marcadores. fileciteturn12file0

#### `__len__()`
Está declarado para “retornar la cantidad de eventos registrados”, pero actualmente contiene `pass`, por lo que no está implementado. Este punto debe considerarse un defecto pendiente del módulo. fileciteturn12file0

### 3.6 Uso esperado de `GHiampDataManager`

Esta clase está pensada para análisis offline de señales del amplificador: inspección de canales, frecuencia de muestreo, sincronización con marcadores y acceso a la matriz cruda de muestras. No implementa, por sí misma, preprocesamiento EEG, filtrado, epoching ni análisis espectral; sólo expone datos y metadatos. fileciteturn12file0

## 4. Clase `LSLDataManager`

### 4.1 Objetivo

`LSLDataManager` encapsula la lectura de un archivo `.xdf` y reconstruye la información registrada por los streams LSL del experimento. La clase no se limita a leer los streams de forma genérica: presupone una estructura de trials con mensajes JSON y ofrece utilidades específicas para el paradigma de handwriting, incluyendo letras, tiempos de trial, coordenadas del lápiz, pen-downs, pen-ups y trazos. fileciteturn12file0

### 4.2 Contexto dentro del sistema

`SessionManager` crea dos streams de marcadores llamados `Laptop_Markers` y `Tablet_Markers`. El primero contiene el diccionario de marcas de la laptop; el segundo recibe la información reconstruida desde el JSON persistido por la tablet al final de cada trial. `LSLDataManager` está claramente construido para consumir precisamente esos streams. fileciteturn11file16 fileciteturn11file11

El JSON que la tablet envía y/o guarda contiene campos como `sessionStartTime`, `trialStart`, `trialFadein`, `trialCue`, `trialFadeout`, `trialRest`, `penDownMarkers`, `penUpMarkers`, `coordinates` y `sessionFinalTime`. En `SessionManager`, parte de esos datos se vuelven a empaquetar y emitir por LSL para `Tablet_Markers`; por eso `LSLDataManager` asume etiquetas como `trialStartTime`, `trialCueTime`, `trialRestTime`, `penDownMarkers`, `penUpMarkers`, `coordinates`, `trialID` y `letter`. fileciteturn11file14 fileciteturn11file15 fileciteturn11file11

### 4.3 Constructor

Firma:

```python
LSLDataManager(filename)
```

Al instanciarse, ejecuta toda la reconstrucción principal:
- carga el `.xdf`
- obtiene nombres de streamers
- obtiene las keys de cada streamer
- reconstruye las series temporales
- obtiene fecha del archivo
- extrae `trials_info`
- calcula el primer timestamp LSL de cada stream
- calcula un timestamp de referencia por streamer (`first_timestamp`)
- reconstruye coordenadas por trial
- calcula retrasos entre cue y primer pen-down
- construye tablas de tiempos por trial. fileciteturn12file0

El objeto queda listo para análisis exploratorio y visualización. fileciteturn12file0

### 4.4 Atributos principales

Los atributos más relevantes son:
- `filename`
- `raw_data`, `header`
- `streamers_names`
- `streamers_keys`
- `time_series`
- `fecha_registro`, `timestamp_registro`
- `trials_info`
- `first_lsl_timestamp`
- `first_timestamp`
- `coordinates_info`
- `pendown_delays`
- `trials_times` fileciteturn12file0

### 4.5 Métodos de carga y parseo

#### `_read_data(filename)`
Carga el archivo usando `pyxdf.load_xdf(filename)`. Retorna datos crudos y header. fileciteturn12file0

#### `_parse_trial_message(raw)`
Recibe cada muestra textual del stream, decodifica bytes si hace falta, limpia comillas exteriores si quedaron por logging y luego aplica `json.loads`. Si el valor está vacío, retorna una lista vacía. Este método es central: toda la clase asume que cada mensaje del stream es un JSON serializado. fileciteturn12file0

#### `_get_streamers_names()`
Devuelve la lista de nombres de streams registrados en el `.xdf`. fileciteturn12file0

#### `_get_streamers_keys()`
Toma la primera muestra de cada stream, la parsea como dict y extrae sus claves. Esto permite inferir dinámicamente qué campos tiene cada streamer. Sin embargo, también vuelve a la implementación dependiente de que la primera muestra válida no sea vacía ni malformada. fileciteturn12file0

#### `_get_timeseries()`
Reconstruye todas las muestras de cada streamer como listas de diccionarios ya parseados. El resultado es un diccionario `streamer_name -> list[dict]`. fileciteturn12file0

#### `_get_trials_info()`
Convierte `time_series` a una estructura indexada por `trialID` implícito (1, 2, 3, ...), una por streamer. Luego elimina las entradas vacías. El resultado final es:

```python
{
    "Laptop_Markers": {
        1: {...},
        2: {...}
    },
    "Tablet_Markers": {
        1: {...},
        2: {...}
    }
}
```

Es importante notar que el índice externo no proviene necesariamente del campo interno `trialID` del mensaje, sino de la posición en la serie tras el filtrado inicial. fileciteturn12file0

### 4.6 Tiempos y referencias temporales

#### `_get_datetime()`
Lee la fecha de registro desde `header["info"]["datetime"]`, la parsea y la convierte a UTC-3. Si falla, retorna `(None, None)`. fileciteturn12file0

#### `_get_first_lsl_timestamp()`
Extrae el primer timestamp LSL de cada stream desde el footer del archivo XDF. Esta referencia pertenece a la escala interna de LSL. fileciteturn12file0

#### `_get_first_run_timestamp()`
Calcula el “cero” experimental por streamer usando `self.trials_info[name][1]["sessionStartTime"]`. Esto implica dos supuestos fuertes: que existe el trial `1` y que el primer trial válido representa el inicio de la primera ronda. Si cualquiera de esos supuestos falla, el método puede romperse o producir una referencia errónea. fileciteturn12file0

#### `trialsTimes()`
Devuelve, para cada streamer, un `DataFrame` con `letter`, `trialStartTime`, `trialCueTime` y `trialRestTime`, todos expresados en segundos relativos a `first_timestamp`. Es una vista útil para análisis temporal por trial. fileciteturn12file0

### 4.7 Información de coordenadas y escritura

#### `get_coordinates_info()`
Recorre específicamente `self.time_series["Tablet_Markers"]`, toma `coordinates` y arma un diccionario por `trialID`. Si hay coordenadas, re-referencia el tiempo de cada punto al instante del primer punto del trazo; si no, guarda `coordinates=None`. La estructura resultante es:

```python
{
    trialID: {
        "letter": "a",
        "coordinates": [(x, y, t_rel), ...]
    }
}
```

Este método presupone que existe el streamer `Tablet_Markers`; por lo tanto, la clase no es plenamente genérica para cualquier archivo XDF. fileciteturn12file0

#### `getTrialCoordinates(trialID)`
Devuelve las coordenadas de un trial como `numpy.ndarray` o `None` si el trial no existe en `coordinates_info`. fileciteturn12file0

#### `get_pendownDelays()`
Calcula, para cada trial de `Tablet_Markers`, la demora entre `trialCueTime` y el primer `penDownMarkers[0]`. Devuelve un diccionario con letra y delay en segundos. Si no hubo pen-down, asigna `None`. Este método es útil para estimar latencia conductual desde el cue al inicio de escritura. fileciteturn12file0

#### `infoTrial(trialID)`
Construye un resumen detallado de un trial de la tablet con:
- `letter`
- `trialStartTime`
- `trialCueTime`
- `trialRestTime`
- `pendowns`
- `penups`
- `writing_duration`
- `pendown_delay` fileciteturn12file0

Los tiempos se expresan relativos a `first_timestamp["Tablet_Markers"]`, y la duración de escritura se calcula a partir del último timestamp del trazo. fileciteturn12file0

### 4.8 Resúmenes y utilidades analíticas

#### `trials_qty`
Propiedad que devuelve la cantidad de trials reconstruidos por streamer. fileciteturn12file0

#### `describe_trials()`
Produce un `DataFrame` resumen por dispositivo (`Tablet_Markers` y `Laptop_Markers`) con:
- duración total
- número de trials
- tiempo medio y desviación estándar entre inicios de trial
- tiempo medio y desviación estándar entre cue y rest
- conjunto de letras observadas. fileciteturn12file0

Esta rutina es útil para control de calidad temporal del experimento y para comparar coherencia entre laptop y tablet. fileciteturn12file0

#### `lettersTrials(letter)`
Devuelve dos listas: IDs de trials para la letra solicitada en laptop y en tablet. Útil para selección por condición simbólica. fileciteturn12file0

#### `is_none_like(coordinates)`
Chequea si una estructura de coordenadas es `None` o equivalente. Está pensada para robustecer el código de visualización. fileciteturn12file0

### 4.9 Visualización de trazos

#### `plot_traces(trialID, ...)`
Grafica el trazo de un único trial. Invierte el eje Y para respetar el sistema de coordenadas de la tablet y retorna `(fig, ax)`. Soporta numerosas banderas de estilo para ocultar título, ejes, ticks, labels y spines. fileciteturn12file0

#### `plot_all_traces(grilla=None, ...)`
Agrupa trials por letra y construye una grilla donde cada columna corresponde a una letra y cada fila a una repetición de esa letra. Devuelve `(fig, axes)`. Si no se define `grilla`, calcula automáticamente filas y columnas a partir de la cantidad de letras y el máximo número de trials por letra. fileciteturn12file0

### 4.10 Métodos especiales

#### `__getitem__(key)`
Permite consultas del tipo:

```python
lsl_manager["Laptop_Markers", "letter", :]
lsl_manager["Tablet_Markers", "trialStartTime", 0:5]
```

El formato esperado es `(streamer, label, idx)`. Filtra todos los trials que contienen esa etiqueta y luego aplica indexing o slicing sobre la lista resultante. fileciteturn12file0

#### `__str__()` y `__repr__()`
Construyen un resumen textual con archivo, fecha, timestamp inicial, lista de streamers y una vista resumida de trials y letras por streamer. fileciteturn12file0

#### `__len__()`
Retorna la cantidad de streamers detectados en el archivo XDF. fileciteturn12file0

## 5. Relación con el resto del sistema

`DataManagers.py` no es un módulo aislado: está acoplado de manera implícita al protocolo experimental definido por `SessionManager`, `TabletMessenger`, `PCMessenger` y `MainActivity`. `SessionManager` emite por LSL un stream `Laptop_Markers` y otro `Tablet_Markers`; además, al finalizar el trial lee el JSON guardado en la tablet y lo reenvía como marcador de tablet. `TabletMessenger` sabe dónde recuperar `trial_<id>.json` desde `Documents/<subject>/<session>/<run>/...`, y `PCMessenger` define el esquema JSON usado por la app Android para enviar o exponer la información del trial. fileciteturn11file16 fileciteturn11file11 fileciteturn11file15 fileciteturn11file18

En Android, `MainActivity` sincroniza el tiempo con la laptop mediante `sessionStartTime`, fija `t0TabletNano` y configura `touchView.timeProvider = { nowRelativeToT0() }`, lo que explica por qué las coordenadas y eventos recuperados por `LSLDataManager` están diseñados para poder compararse temporalmente con las marcas del cue. fileciteturn11file8 fileciteturn11file9

## 6. Fortalezas del diseño actual

El módulo tiene varias fortalezas prácticas: deja los objetos listos tras la construcción, expone resúmenes legibles por `__str__`, facilita indexación ad hoc por marcadores o etiquetas y contiene herramientas de exploración muy útiles para debugging experimental, especialmente en el caso de `LSLDataManager` con coordenadas, pen-down delay y plotting de trazos. fileciteturn12file0

## 7. Limitaciones, supuestos y puntos a documentar explícitamente

Hay varios supuestos que conviene dejar por escrito en la documentación de uso:

`GHiampDataManager.__len__()` no está implementado. Cualquier código que espere `len(manager)` como número de eventos fallará en la práctica o devolverá `None`. fileciteturn12file0

`GHiampDataManager._get_times()` acepta `tinit` y `tend`, pero actualmente no respeta una ventana temporal arbitraria; siempre construye el eje completo desde cero. fileciteturn12file0

`LSLDataManager` no es completamente genérico: depende de streams con estructura JSON y, además, asume explícitamente la existencia de `Tablet_Markers`. Si el archivo XDF no contiene ese streamer, `get_coordinates_info()`, `get_pendownDelays()` e `infoTrial()` pueden fallar. fileciteturn12file0

`_get_first_run_timestamp()` presupone que el primer trial válido tiene índice `1` y que contiene `sessionStartTime`. Si hay trials vacíos al principio, reordenamientos o faltan marcas, el cero temporal puede quedar mal definido. fileciteturn12file0

En `infoTrial()`, la variable `writing_duration` puede no inicializarse si no hay coordenadas válidas, pero luego se intenta usar. Eso merece endurecer el método para evitar errores en trials vacíos. fileciteturn12file0

La consistencia exacta entre los nombres de campos en Android (`trialFadein`, `trialCue`, `trialFadeout`, etc.) y los nombres consumidos en Python (`trialCueTime`, `trialRestTime`, etc.) depende de la transformación intermedia realizada por `SessionManager` al reemitir la información de la tablet. Ese contrato conviene mantenerlo estable y bien documentado. fileciteturn11file14 fileciteturn11file11

## 8. Recomendaciones de mejora

Conviene implementar `__len__()` en `GHiampDataManager`, agregar validaciones tempranas sobre existencia de streams esperados en `LSLDataManager`, desacoplar `get_coordinates_info()` del nombre fijo `Tablet_Markers`, blindar `infoTrial()` ante coordenadas ausentes y homogeneizar la nomenclatura temporal entre Android, `SessionManager` y `DataManagers`. También sería valioso separar la clase `LSLDataManager` en dos niveles: uno genérico para XDF/LSL y otro específico para handwriting/Tablet_Markers. Estas recomendaciones se deducen de la estructura y supuestos actuales del código. fileciteturn12file0 fileciteturn11file11 fileciteturn11file14

## 9. Resumen ejecutivo

`DataManagers.py` implementa la capa de lectura offline del sistema experimental. `GHiampDataManager` está orientado a datos del amplificador g.HIAMP en HDF5, mientras que `LSLDataManager` está claramente especializado en reconstruir y analizar trials del paradigma de handwriting desde un archivo XDF con streams `Laptop_Markers` y `Tablet_Markers`. El módulo ya es útil para inspección, control de calidad temporal y visualización de trazos, pero tiene varios supuestos rígidos que deben ser conocidos por quien lo use o extienda. fileciteturn12file0 fileciteturn11file16
