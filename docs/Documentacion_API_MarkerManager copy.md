# Documentación API — `MarkerManager`

## Resumen

`MarkerManager` es una clase ligera para **publicar marcadores/eventos en un outlet LSL** (`Lab Streaming Layer`). Su responsabilidad no es almacenar eventos, resolver streams ni leer datos ya grabados, sino **serializar un payload y empujarlo inmediatamente a un `StreamOutlet`** con timestamp de `local_clock()`.  

En la arquitectura actual del proyecto, `SessionManager` la usa para crear dos outlets de eventos separados:

- `Laptop_Markers`
- `Tablet_Markers`

Esto permite que los eventos de laptop y tablet queden publicados como streams LSL independientes y luego puedan ser reconstruidos por `LSLDataManager`.

---

## Importaciones y dependencias

```python
import json
import random
import logging
from pylsl import StreamInfo, StreamOutlet, local_clock
from typing import Any, Optional, Union
```

### Dependencia externa crítica

La clase depende de `pylsl`. Si `pylsl` no está instalado o el entorno no puede inicializar LSL, la clase no podrá crear el outlet.

---

## Clase: `MarkerManager`

```python
class MarkerManager:
```

### Propósito

Encapsular la creación de un stream LSL de eventos y exponer un método simple, `sendMarker(...)`, para enviar marcadores al flujo.

### Diseño general

La implementación actual asume el patrón más común de tu proyecto:

- **1 canal**
- **formato string**
- **sample rate nominal 0** (event stream irregular)
- serialización de `dict` a JSON
- serialización del resto de objetos mediante `str(...)`

---

## Constructor

```python
def __init__(
    self,
    stream_name: str = "Generic_Markers",
    stream_type: str = "Events",
    source_id: Optional[str] = None,
    channel_count: int = 1,
    channel_format: str = "string",
    nominal_srate: float = 0.0,
    logger: Optional[logging.Logger] = None
) -> None:
```

### Parámetros

#### `stream_name: str = "Generic_Markers"`
Nombre lógico del stream LSL.

Ejemplos en tu arquitectura:
- `"Laptop_Markers"`
- `"Tablet_Markers"`

#### `stream_type: str = "Events"`
Tipo del stream LSL. En tu código suele usarse `"Markers"` o `"Events"`.

#### `source_id: Optional[str] = None`
Identificador único del origen del stream.  
Si no se provee, la clase genera uno automáticamente como:

```python
f"{stream_name}_{random.randint(1000, 9999)}"
```

Esto evita colisiones triviales, pero no garantiza unicidad global absoluta.

#### `channel_count: int = 1`
Cantidad de canales del stream.  
La implementación de `sendMarker(...)` empuja siempre una lista de longitud 1:

```python
[payload]
```

Por eso, aunque este parámetro sea configurable, el diseño real del método está orientado a **un solo canal**.

#### `channel_format: str = "string"`
Formato de los datos del stream.  
El uso normal en tu proyecto es `"string"`.

#### `nominal_srate: float = 0.0`
Frecuencia nominal del stream.  
Para marcadores/eventos irregulares, `0.0` es la configuración natural.

#### `logger: Optional[logging.Logger] = None`
Logger opcional.  
Si no se pasa uno, se crea/configura uno con nombre `"MarkerManager"`.

---

## Atributos generados

Tras instanciar la clase, los atributos principales son:

### `self.stream_name`
Nombre del stream LSL.

### `self.stream_type`
Tipo del stream LSL.

### `self.source_id`
ID de fuente efectivo, ya sea el provisto por el usuario o el autogenerado.

### `self.outlet_info`
Objeto `pylsl.StreamInfo` con la metadata del outlet.

### `self.outlet`
Objeto `pylsl.StreamOutlet` utilizado para empujar muestras.

### `self.logger`
Logger asociado a la instancia.

---

## Configuración interna del outlet

El constructor crea el `StreamInfo` así:

```python
self.outlet_info = StreamInfo(
    name=self.stream_name,
    type=self.stream_type,
    nominal_srate=nominal_srate,
    channel_format=channel_format,
    channel_count=channel_count,
    source_id=self.source_id
)
```

Luego crea el outlet:

```python
self.outlet = StreamOutlet(self.outlet_info)
```

### Consecuencia práctica

La creación del objeto `MarkerManager` **ya crea y publica** el outlet LSL.  
No existe un método posterior tipo `connect()`, `start()` o `open()`.

---

## Logging

Si no se inyecta un logger, el constructor configura uno:

```python
self.logger = logger or logging.getLogger("MarkerManager")
```

y, si el logger no tiene handlers, agrega:

- `StreamHandler`
- formato: `"[%(name)s] %(levelname)s: %(message)s"`
- nivel: `INFO`
- `propagate = False`

### Implicación

Si reutilizas el mismo logger entre varias instancias, la clase evita duplicar handlers.  
Si inyectas un logger externo ya configurado, ese logger queda bajo tu control.

---

## Método público: `sendMarker`

```python
def sendMarker(self, message: Union[str, dict, Any]) -> None:
```

### Propósito

Serializar el mensaje de entrada y enviarlo al stream LSL actual.

### Comportamiento

#### Caso 1: marcador vacío o nulo

Si `message is None` o `message == ""`, el método:

- registra un warning,
- no envía nada,
- retorna inmediatamente.

```python
if message is None or message == "":
    self.logger.warning("Intento de enviar marcador vacío o nulo — ignorado.")
    return
```

#### Caso 2: `message` es `dict`

Se serializa con `json.dumps(...)`:

```python
payload = json.dumps(message)
```

Esto es especialmente útil cuando el marcador lleva estructura, por ejemplo:

- `trialID`
- `runID`
- `letter`
- timestamps
- estado de fase

#### Caso 3: cualquier otro tipo

Se convierte a string:

```python
payload = str(message)
```

Esto permite enviar:
- strings simples,
- números,
- objetos con `__str__`,
- enums o estructuras livianas convertibles a texto.

#### Envío efectivo

El payload se envía como una muestra de un único canal:

```python
self.outlet.push_sample([payload], timestamp=local_clock())
```

### Timestamp usado

El método usa explícitamente:

```python
local_clock()
```

Por lo tanto, el timestamp del marcador queda en la escala temporal interna de LSL del host que publica el evento.

---

## Ejemplos de uso

### 1) Outlet genérico simple

```python
from pyhwr.managers.MarkerManager import MarkerManager

marker = MarkerManager()
marker.sendMarker("inicio_sesion")
```

### 2) Marcador estructurado en JSON

```python
marker = MarkerManager(
    stream_name="Laptop_Markers",
    stream_type="Markers",
    source_id="Laptop"
)

marker.sendMarker({
    "trialID": 4,
    "runID": 1,
    "letter": "a",
    "trialCueTime": 1712345678.123
})
```

### 3) Patrón real dentro de `SessionManager`

```python
self.laptop_marker = MarkerManager(
    stream_name="Laptop_Markers",
    stream_type="Markers",
    source_id="Laptop",
    channel_count=1,
    channel_format="string",
    nominal_srate=0
)

self.tablet_marker = MarkerManager(
    stream_name="Tablet_Markers",
    stream_type="Markers",
    source_id="Tablet",
    channel_count=1,
    channel_format="string",
    nominal_srate=0
)
```

---

## Integración con el resto de la arquitectura

### Con `SessionManager`

`SessionManager` crea dos instancias de `MarkerManager` para separar eventos de laptop y tablet.  
Eso implica que los consumers aguas abajo pueden distinguir ambas fuentes por nombre de stream y/o `source_id`.

### Con `LSLDataManager`

`LSLDataManager` reconstruye información del experimento a partir de streams XDF y depende de nombres de streamers concretos. En esa arquitectura, que `MarkerManager` publique streams con nombres estables es importante para la carga posterior.

### Con `TabletMessenger`

Un patrón útil del proyecto es:

1. enviar una instrucción a la tablet vía ADB/JSON (`TabletMessenger`),
2. actualizar estado/fase en la app Android,
3. publicar en LSL el marcador correspondiente con `MarkerManager`.

De ese modo quedan dos planos:
- **control**: broadcast ADB
- **registro sincronizable**: marcador LSL

---

## Contrato real de datos

Aunque la firma acepta `Union[str, dict, Any]`, en la práctica hay dos formas sanas de uso:

### A. `str`
Para eventos simples y compactos:

```python
marker.sendMarker("rest_start")
```

### B. `dict`
Para eventos ricos y reconstruibles:

```python
marker.sendMarker({
    "trialID": 7,
    "phase": "cue",
    "letter": "n",
    "sessionStartTime": 1234567890.0
})
```

### Recomendación

En esta arquitectura conviene preferir `dict`, porque luego los datos pueden parsearse con más robustez que un string libre.

---

## Manejo de errores

`sendMarker(...)` encapsula el envío en un `try/except`:

```python
except Exception as e:
    self.logger.error(f"Error enviando marcador: {e}", exc_info=True)
```

### Implicación

- El método **no relanza** la excepción.
- Si falla el envío, el error se registra, pero el flujo del programa continúa.

Esto puede ser deseable para no romper una sesión experimental, pero también significa que un fallo de publicación LSL puede pasar desapercibido si no se monitorean logs.

---

## Limitaciones de la implementación actual

### 1) API orientada de hecho a un solo canal
Aunque `channel_count` es configurable, `sendMarker(...)` siempre empuja una lista de un solo elemento:

```python
[payload]
```

Si se quisiera soportar `channel_count > 1`, habría que cambiar también la lógica de serialización/envío.

### 2) No hay método de cierre o liberación
La clase no expone algo como:
- `close()`
- `shutdown()`
- `disconnect()`

En muchos casos esto no es grave para LSL, pero es una omisión de API.

### 3) No hay validación fuerte del payload
- un `dict` se serializa a JSON,
- todo lo demás se convierte con `str(...)`.

Eso es flexible, pero puede ocultar errores semánticos si un objeto complejo termina convertido a una string poco útil.

### 4) No hay control explícito del timestamp externo
Siempre se usa `local_clock()`.  
No existe la opción de enviar un timestamp suministrado por el llamador.

### 5) No hay metadatos adicionales en `StreamInfo`
La clase no agrega descriptores al stream (`desc()`), por ejemplo:
- versión del protocolo,
- origen experimental,
- descripción del payload,
- codificación JSON,
- sujeto/sesión.

---

## Observación importante sobre el bloque `__main__`

El ejemplo final del archivo contiene:

```python
trial_data, _ = tablet_messenger.read_trial_json("test_subject", 1, 2, 1)
marker_gen.sendMarker(trial_data)
```

Sin embargo, la implementación actual de `TabletMessenger.read_trial_json(...)` **no devuelve consistentemente una tupla de dos elementos**; su contrato real es distinto y puede devolver un objeto JSON decodificado, listas vacías o `None` según el caso.

### Conclusión

Ese ejemplo debe considerarse **desactualizado o inconsistente con la implementación actual de `TabletMessenger`**.  
Si se quiere mantener un ejemplo ejecutable, conviene reemplazarlo por algo como:

```python
trial_data = tablet_messenger.read_trial_json("test_subject", "1", "2", 1)
if trial_data:
    marker_gen.sendMarker(trial_data)
```

---

## Buenas prácticas de uso

### Recomendadas

- usar `stream_name` estables y explícitos,
- usar `source_id` deterministas cuando importe la trazabilidad,
- preferir `dict` frente a strings libres,
- revisar logs durante la sesión,
- documentar el schema JSON de los marcadores.

### Evitar

- enviar objetos arbitrarios esperando que luego sean parseables,
- depender de `str(obj)` para payloads críticos,
- asumir que un outlet multi-canal está soportado solo porque `channel_count` existe.

---

## Ejemplo recomendado para tu proyecto

```python
from pyhwr.managers.MarkerManager import MarkerManager

laptop_marker = MarkerManager(
    stream_name="Laptop_Markers",
    stream_type="Markers",
    source_id="Laptop",
    channel_count=1,
    channel_format="string",
    nominal_srate=0
)

tablet_marker = MarkerManager(
    stream_name="Tablet_Markers",
    stream_type="Markers",
    source_id="Tablet",
    channel_count=1,
    channel_format="string",
    nominal_srate=0
)

laptop_marker.sendMarker({
    "runID": 1,
    "trialID": 3,
    "phase": "cue",
    "letter": "s"
})
```

---

## Recomendaciones de mejora de la API

1. **Agregar soporte explícito para timestamps externos**
   ```python
   def sendMarker(self, message, timestamp=None):
       ts = local_clock() if timestamp is None else timestamp
   ```

2. **Agregar validación opcional del payload**
   - exigir `dict | str`,
   - rechazar objetos arbitrarios,
   - opcionalmente validar un schema.

3. **Agregar método de cierre**
   Aunque LSL no siempre lo exige, una API explícita suele mejorar legibilidad.

4. **Agregar metadatos al stream**
   Incluir en `StreamInfo.desc()` información útil para parsing posterior.

5. **Separar serialización de envío**
   Un método como `_serialize_marker(...)` facilitaría testeo unitario.

6. **Corregir el ejemplo del bloque `__main__`**
   Para alinearlo con `TabletMessenger.read_trial_json(...)`.

---

## Resumen ejecutivo

`MarkerManager` es una clase pequeña pero estratégica: hace de puente entre el control experimental y el registro sincronizable por LSL. Su implementación es correcta para el caso dominante de tu proyecto —event streams de un canal con payload string/JSON—, pero conviene documentar explícitamente que:

- el outlet se crea en el constructor,
- los `dict` se serializan a JSON,
- el timestamp siempre sale de `local_clock()`,
- el diseño real es de un solo canal,
- el ejemplo `__main__` actual no está alineado con `TabletMessenger`.
