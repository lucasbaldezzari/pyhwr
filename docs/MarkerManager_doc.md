# MarkerManager

## Descripción general

`MarkerManager` implementa una capa mínima para la creación de un **outlet de marcadores en Lab Streaming Layer (LSL)** y el envío de eventos serializados hacia otros consumidores del ecosistema experimental. La clase centraliza la configuración del stream, la construcción del `StreamOutlet`, el manejo básico de logging y la conversión del contenido enviado a un formato compatible con un canal LSL de tipo `string`. fileciteturn27file0

En la arquitectura del proyecto, `MarkerManager` funciona como el componente responsable de exponer eventos de sincronización y metadatos de trial. `SessionManager` crea dos instancias, una para `Laptop_Markers` y otra para `Tablet_Markers`, mientras que `PreExperimentManager` utiliza una única instancia para `Laptop_Markers`. De esta forma, la clase actúa como el punto común de publicación de marcadores para rondas de escritura y preexperimentos. fileciteturn27file2 fileciteturn27file4

## Responsabilidad dentro del sistema

La responsabilidad de `MarkerManager` no consiste en interpretar la semántica de los eventos, sino en publicarlos sobre LSL con un contrato uniforme. La semántica concreta de cada marcador —por ejemplo, `trialStartTime`, `trialCueTime`, `sessionFinalTime`, letras o acciones— se define en los gestores de sesión que construyen los diccionarios antes de invocar `sendMarker(...)`. `MarkerManager` sólo se ocupa de transportar esos datos al stream correspondiente. fileciteturn27file0 fileciteturn27file2 fileciteturn27file4

## Dependencias principales

El módulo depende de los siguientes componentes:

- `pylsl.StreamInfo` para describir el stream.
- `pylsl.StreamOutlet` para publicar las muestras.
- `pylsl.local_clock` para asignar el timestamp LSL de cada envío.
- `json` para serializar diccionarios antes de enviarlos.
- `logging` para registrar eventos y errores.
- `random` para generar un `source_id` aleatorio cuando no se provee uno explícitamente. fileciteturn27file0

## Clase principal

### `class MarkerManager`

Clase encargada de crear y mantener un outlet LSL de marcadores.

#### Constructor

```python
MarkerManager(
    stream_name: str = "Generic_Markers",
    stream_type: str = "Events",
    source_id: Optional[str] = None,
    channel_count: int = 1,
    channel_format: str = "string",
    nominal_srate: float = 0.0,
    logger: Optional[logging.Logger] = None,
)
```

#### Parámetros

- `stream_name`: nombre lógico del stream LSL.
- `stream_type`: tipo del stream. En el proyecto suele usarse `Markers` o `Events`.
- `source_id`: identificador único del outlet. Si no se provee, se genera automáticamente a partir del nombre del stream y un entero aleatorio.
- `channel_count`: cantidad de canales del stream. La implementación está pensada, en la práctica, para `1`.
- `channel_format`: tipo de dato del canal. La implementación actual opera sobre `string`.
- `nominal_srate`: frecuencia nominal del stream. Para marcadores event-based se utiliza `0.0`.
- `logger`: logger externo opcional. Si no se pasa uno, la clase crea y configura uno propio llamado `MarkerManager`. fileciteturn27file0

#### Atributos relevantes

- `stream_name`: nombre configurado para el outlet.
- `stream_type`: tipo lógico del stream.
- `source_id`: identificador del origen.
- `outlet_info`: objeto `StreamInfo` con la metadata del stream.
- `outlet`: objeto `StreamOutlet` utilizado para el envío de muestras.
- `logger`: logger activo de la instancia. fileciteturn27file0

## Comportamiento de inicialización

Durante la construcción de la instancia se crea un `StreamInfo` con los parámetros recibidos y, a continuación, un `StreamOutlet` asociado. Si no se suministra un `logger`, se configura uno con `StreamHandler`, formato de mensaje explícito, nivel `INFO` y `propagate=False`. Tras la inicialización, se emite un mensaje de log que informa el nombre del outlet, el tipo del stream y el `source_id` asociado. fileciteturn27file0

## API pública

### `sendMarker(message)`

```python
sendMarker(message: Union[str, dict, Any]) -> None
```

Envía un marcador al outlet LSL activo.

#### Reglas de comportamiento

- Si `message` es `None` o una cadena vacía, el marcador se ignora y se registra una advertencia.
- Si `message` es un `dict`, se serializa con `json.dumps(...)` antes del envío.
- Si `message` no es un diccionario, se convierte con `str(...)`.
- El envío se realiza mediante `self.outlet.push_sample([payload], timestamp=local_clock())`.
- Si ocurre una excepción, ésta se registra con `exc_info=True`. fileciteturn27file0

#### Contrato efectivo del payload

Aunque la firma acepta `Any`, el contrato real de uso del proyecto se reduce a dos casos:

1. **Cadenas simples**, útiles para pruebas o señales puntuales.
2. **Diccionarios JSON-serializables**, que constituyen el caso principal de uso en la arquitectura experimental. fileciteturn27file0

En `SessionManager` y `PreExperimentManager` los marcadores se construyen como diccionarios que contienen identificadores de trial, run, letra o acción y marcas temporales en milisegundos absolutos. Esos diccionarios son luego enviados por `MarkerManager` sin reinterpretación adicional. fileciteturn27file2 fileciteturn27file4

## Integración con otros módulos

### Integración con `SessionManager`

`SessionManager` utiliza dos outlets diferenciados:

- `Laptop_Markers`, destinado a los eventos generados por la aplicación de escritorio.
- `Tablet_Markers`, destinado a registrar en LSL la información recuperada desde la tablet o asociada a ella. fileciteturn27file2

Esta separación permite que el archivo `.xdf` contenga streams semánticamente distintos, lo que después es aprovechado por `LSLDataManager`, que espera nombres de streamer como `Laptop_Markers` y `Tablet_Markers` para reconstruir la información de los trials y sus timestamps. fileciteturn27file8 fileciteturn27file11

### Integración con `PreExperimentManager`

`PreExperimentManager` crea únicamente el stream `Laptop_Markers`, ya que no interviene la mensajería con la tablet. Los eventos del preexperimento se publican con la misma mecánica de diccionarios serializados. fileciteturn27file4

### Relación con Android

`MarkerManager` no se comunica directamente con Android. Su rol se limita al ecosistema LSL. La integración con la tablet se produce en otra capa: `SessionManager` utiliza `TabletMessenger` para enviar mensajes por ADB/Broadcast, mientras que el lado Android registra su propia información y la hace disponible para posterior análisis. `MarkerManager` participa sólo en el registro LSL de los eventos del lado PC y de la semántica asociada al lado tablet cuando esos datos ya están disponibles en Python. fileciteturn27file2 fileciteturn27file14

## Ejemplos de uso

### Ejemplo mínimo

```python
from pyhwr.managers.MarkerManager import MarkerManager

marker = MarkerManager(
    stream_name="Generic_Markers",
    stream_type="Events",
    source_id="Test_Source",
)

marker.sendMarker({"event": "session_started", "timestamp": 1710000000000})
```

Este patrón coincide con el caso de uso esperado: un stream de un canal tipo `string` que recibe diccionarios serializados como JSON. fileciteturn27file0

### Ejemplo en una sesión experimental

```python
self.laptop_marker = MarkerManager(
    stream_name="Laptop_Markers",
    stream_type="Markers",
    source_id="Laptop",
    channel_count=1,
    channel_format="string",
    nominal_srate=0,
)

self.laptop_marker.sendMarker(self.laptop_marker_dict)
```

Ese es el patrón empleado por los gestores de sesión del proyecto. fileciteturn27file2 fileciteturn27file4

## Consideraciones de diseño

### 1. Canal y formato efectivamente fijos

Aunque el constructor permite parametrizar `channel_count` y `channel_format`, la implementación y los consumidores del proyecto están alineados con un único canal de tipo `string`. El método `sendMarker(...)` siempre envía una lista con un único elemento (`[payload]`), por lo que la flexibilidad expuesta por la firma es mayor que la soportada de hecho por el resto de la arquitectura. fileciteturn27file0

### 2. Timestamp en tiempo LSL

El timestamp usado en `push_sample(...)` proviene de `local_clock()`, es decir, del reloj interno de LSL. Esto es correcto para sincronización entre streams, pero convive con timestamps absolutos en milisegundos (`time.time()*1000`) incluidos dentro del payload JSON construido por `SessionManager` y `PreExperimentManager`. En consecuencia, los archivos `.xdf` combinan dos referencias temporales: el timestamp de muestra del stream LSL y los tiempos absolutos almacenados dentro del contenido del marcador. fileciteturn27file0 fileciteturn27file2 fileciteturn27file15

### 3. Serialización sin validación semántica

`MarkerManager` no valida la estructura del diccionario antes de serializarlo. Esto simplifica la clase, pero desplaza la responsabilidad de consistencia a los módulos que construyen los marcadores. Cualquier clave faltante, campo inconsistente o mezcla de unidades temporales se propaga tal como fue producida por el emisor. fileciteturn27file0

### 4. Logger autocontenido

La clase puede operar de forma autónoma en contextos de prueba porque configura un logger propio si no recibe uno externo. Esto evita dependencias adicionales, aunque también puede duplicar salidas de log si la aplicación principal configura logging de forma paralela. fileciteturn27file0

## Limitaciones actuales

1. **No existe recepción ni consulta de estado del stream.** La clase sólo publica marcadores.
2. **No existe validación estructural del payload.** La serialización de diccionarios se realiza sin esquema ni validación previa.
3. **La generalidad de la firma es mayor que la del comportamiento real.** La arquitectura asume un canal único tipo `string`.
4. **El ejemplo del bloque `__main__` está desactualizado respecto al contrato actual de `TabletMessenger`.** Allí se desempaquetan dos valores desde `read_trial_json(...)`, pero la implementación actual de `TabletMessenger` no garantiza consistentemente ese retorno. fileciteturn27file0

## Recomendaciones de mejora

- Restringir o documentar explícitamente que el uso soportado es un stream de un solo canal tipo `string`.
- Agregar validación opcional de payload para detectar diccionarios mal formados antes del envío.
- Definir una convención formal de esquema para los marcadores de laptop y tablet.
- Actualizar o eliminar el bloque `__main__` para alinearlo con la implementación actual de `TabletMessenger`.
- Considerar métodos auxiliares para envío de eventos tipados, por ejemplo `send_trial_marker(...)` o `send_session_marker(...)`, si se quisiera endurecer la API. fileciteturn27file0

## Resumen

`MarkerManager` constituye el componente de publicación LSL de la arquitectura. Su diseño es deliberadamente simple: crea un `StreamOutlet`, convierte el mensaje a texto, asigna un timestamp LSL y publica el marcador. La simplicidad de la clase facilita su reutilización en `SessionManager` y `PreExperimentManager`, pero también hace que la corrección semántica de los datos dependa completamente de los gestores que construyen los payloads. fileciteturn27file0 fileciteturn27file2 fileciteturn27file4
