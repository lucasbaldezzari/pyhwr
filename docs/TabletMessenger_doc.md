# `TabletMessenger`

## Descripción general

`TabletMessenger` es el componente responsable de la comunicación operativa entre la aplicación Python que controla la sesión experimental y la tablet Android utilizada para la presentación de estímulos y el almacenamiento de datos trial a trial.

Su función principal consiste en:

- construir mensajes JSON con el estado de la sesión y del trial,
- enviarlos a Android mediante `adb shell am broadcast`,
- consultar si existen archivos `trial_<id>.json` en el dispositivo,
- leer esos JSON desde la PC,
- y descargarlos al sistema local cuando se requiere persistencia fuera de la tablet.

Dentro de la arquitectura general, `TabletMessenger` no actúa como un bus de eventos bidireccional ni como una capa de transporte robusta con acuse de recibo. En su estado actual, opera como una interfaz ligera sobre tres mecanismos concretos:

1. **ADB** para comunicación PC → Android,
2. **Broadcast Intents** para entregar payloads JSON a la app,
3. **archivos JSON en `Documents/`** para recuperar información trial a trial desde la tablet.

---

## Ubicación en la arquitectura

`TabletMessenger` ocupa una posición intermedia entre el controlador experimental en Python y la aplicación Android.

### Lado Python

Se utiliza principalmente desde `SessionManager`, que lo instancia para:

- enviar cambios de fase,
- informar inicio y finalización de sesión,
- propagar el identificador de sesión, run y sujeto,
- sincronizar la base temporal inicial con Android,
- y recuperar luego los datos de cada trial persistidos en el dispositivo.

### Lado Android

Los mensajes son recibidos por `PCMessenger`, que escucha la action:

```text
com.handwriting.ACTION_MSG
```

El payload JSON se entrega en el extra `payload`, se interpreta como `JSONObject` y se expone como `latestMessage` para que `MainActivity` procese el estado de sesión y la fase experimental.

### Persistencia Android

La información de cada trial se guarda en rutas del tipo:

```text
/storage/emulated/0/Documents/<subject>/<session>/<run>/trial_<id>.json
```

Esa ruta es el contrato principal consumido por `read_trial_json(...)`, `pull_trial_json(...)` y `list_trials(...)`.

---

## Responsabilidades principales

`TabletMessenger` concentra cinco responsabilidades operativas:

1. **Construcción del payload JSON**
   - arma el diccionario con `sesionStatus`, metadata de sesión y `trialInfo`.

2. **Envío de mensajes hacia Android**
   - serializa el payload con `json.dumps(...)`,
   - construye el comando ADB,
   - y lo ejecuta mediante `subprocess.run(...)`.

3. **Resolución de rutas de trials en el dispositivo**
   - genera la ruta esperada dentro de `Documents/`.

4. **Lectura remota de archivos JSON**
   - ejecuta `adb shell cat ...`,
   - interpreta la salida con `json.loads(...)`.

5. **Descarga local de JSONs de trial**
   - usa `adb pull` para copiar el archivo al sistema local.

---

## Dependencias directas

`TabletMessenger` depende únicamente de librerías estándar de Python:

- `subprocess`
- `json`
- `collections.deque`
- `pathlib.Path`
- `logging`

No depende de Qt, LSL ni MNE. Esa independencia lo convierte en un componente reusable para scripts de prueba, depuración o adquisición offline.

---

## Firma del constructor

```python
TabletMessenger(max_messages=200, serial="R52W70ATD1W")
```

### Parámetros

- `max_messages`: tamaño máximo del historial interno.
- `serial`: serial ADB del dispositivo Android.

### Atributos principales

- `buffer`: inicializado en `None`. No participa en la lógica actual.
- `history`: `deque(maxlen=max_messages)`. Reservado para historial de mensajes.
- `max_messages`: copia del valor recibido en el constructor.
- `serial`: identificador del dispositivo Android a utilizar en ADB.
- `logger`: logger con nombre `TabletMessenger`.
- `log_consola`: `StreamHandler` asociado al logger.

### Observación

Aunque existe un `history`, la implementación actual no agrega mensajes automáticamente a esa estructura. En consecuencia, `history` y `buffer` deben considerarse atributos reservados o incompletos, no una funcionalidad plenamente implementada.

---

## Contrato del mensaje

El método `make_message(...)` construye un payload con esta forma base:

```python
{
    "sesionStatus": sesionStatus,
    "session_id": sesion_id,
    "run_id": run_id,
    "subject_id": subject_id,
    "trialInfo": {
        "trialID": trialID,
        "trialPhase": trialPhase,
        "letter": letter,
        "duration": duration,
    }
}
```

### Campos principales

- `sesionStatus`: estado general de la sesión.
- `session_id`: identificador de sesión.
- `run_id`: identificador de corrida.
- `subject_id`: identificador del sujeto.
- `trialInfo.trialID`: índice del trial.
- `trialInfo.trialPhase`: fase experimental actual.
- `trialInfo.letter`: letra objetivo.
- `trialInfo.duration`: duración esperada de la fase.

### Observación importante

La clave se escribe como `sesionStatus` y no como `sessionStatus`. Esa grafía forma parte del contrato actual entre Python y Android. Dado que `MainActivity.kt` consulta explícitamente ese nombre, cualquier refactor debería coordinarse en ambos extremos.

### Campos extra

`make_message(...)` acepta `**extra`, que se incorporan al nivel raíz del mensaje. Esto permite incluir, por ejemplo:

- `sessionStartTime`,
- `mensaje_a_usuario`,
- flags auxiliares,
- o metadatos temporales adicionales.

---

## Métodos públicos

## `make_message(...)`

```python
make_message(
    sesionStatus,
    sesion_id,
    run_id,
    subject_id,
    trialID,
    trialPhase,
    letter,
    duration,
    **extra,
) -> dict
```

Construye el diccionario que será enviado a Android.

### Uso típico

```python
tablet = TabletMessenger(serial="R52W70ATD1W")

payload = tablet.make_message(
    sesionStatus="on",
    sesion_id=1,
    run_id=1,
    subject_id="S01",
    trialID=3,
    trialPhase="cue",
    letter="a",
    duration=2.0,
)
```

### Uso con campos adicionales

```python
payload = tablet.make_message(
    sesionStatus="on",
    sesion_id=1,
    run_id=1,
    subject_id="S01",
    trialID=3,
    trialPhase="trialInfo",
    letter="a",
    duration=0.0,
    mensaje_a_usuario="Prepararse",
    sessionStartTime=1712345678.123,
)
```

---

## `send_message(...)`

```python
send_message(message: dict, tabletID: str)
```

Envía el payload a la tablet mediante un broadcast ADB.

### Lógica interna

1. Convierte `message` a string JSON.
2. Construye un comando del tipo:

```bash
adb -s <serial> shell am broadcast -a <tabletID> --es payload '<json>'
```

3. Ejecuta el comando con `subprocess.run(..., shell=True, check=True)`.

### Parámetros

- `message`: diccionario listo para serializar.
- `tabletID`: action del broadcast Android.

### Valor habitual de `tabletID`

```python
"com.handwriting.ACTION_MSG"
```

### Uso típico

```python
tablet = TabletMessenger(serial="R52W70ATD1W")
payload = tablet.make_message(
    sesionStatus="on",
    sesion_id=1,
    run_id=1,
    subject_id="S01",
    trialID=1,
    trialPhase="precue",
    letter="l",
    duration=1.0,
)

tablet.send_message(payload, "com.handwriting.ACTION_MSG")
```

### Consideraciones operativas

- requiere que `adb` esté disponible en el `PATH`,
- requiere que el dispositivo esté conectado y visible por ADB,
- requiere que el `serial` corresponda al dispositivo correcto,
- y asume que la app Android está preparada para recibir esa `action`.

---

## `_device_docs_path(...)`

```python
_device_docs_path(subject: str, session: str, run: str, trial_id: int | None = None) -> str
```

Construye la ruta esperada en el almacenamiento de la tablet.

### Ejemplo

```python
path = tablet._device_docs_path("S01", "1", "2", 5)
# /storage/emulated/0/Documents/S01/1/2/trial_5.json
```

Aunque el método es interno, su contrato es importante porque todas las operaciones de lectura y descarga dependen de esta convención de nombres.

---

## `_exists_on_device(...)`

```python
_exists_on_device(device_path: str) -> bool
```

Verifica la existencia de un archivo en la tablet ejecutando un comando `adb shell test -f ...`.

Devuelve `True` si el archivo existe y `False` en caso contrario.

---

## `_choose_existing_device_path(...)`

```python
_choose_existing_device_path(subject: str, session: str, run: str, trial_id: int) -> str | None
```

Devuelve la primera ruta válida para el trial solicitado. En la implementación actual sólo prueba la ruta pública dentro de `Documents/`.

Su nombre sugiere que podría soportar múltiples ubicaciones, pero hoy el comportamiento efectivo es mucho más simple.

---

## `read_trial_json(...)`

```python
read_trial_json(subject: str, session: str, run: str, trial_id: int) -> dict
```

Lee el archivo `trial_<id>.json` directamente desde la tablet y devuelve su contenido como un objeto Python.

### Lógica interna

1. arma la ruta esperada con `_device_docs_path(...)`,
2. verifica que exista en el dispositivo,
3. ejecuta `adb shell cat <ruta>`,
4. interpreta la salida con `json.loads(...)`.

### Uso típico

```python
trial_data = tablet.read_trial_json("S01", "1", "1", 3)
```

### Estructura esperada del JSON

En el flujo actual de la app Android, el JSON suele incluir campos como:

- `trialID`
- `letter`
- `runID`
- `sessionStartTime`
- `trialStartTime`
- `trialPrecueTime`
- `trialCueTime`
- `trialFadeOffTime`
- `trialRestTime`
- `penDownMarkers`
- `penUpMarkers`
- `coordinates`
- `sessionFinalTime`

### Observación importante

Aunque la firma del método sugiere retorno `dict`, en la implementación actual también puede devolver `[]` cuando el archivo no existe o cuando ocurre un error. Por tanto, el contrato real es más laxo que el type hint declarado.

### Observación de implementación

Dentro del bloque `except`, el código invoca `logger.error(...)` en lugar de `self.logger.error(...)`. En su estado actual, ese detalle puede provocar un error adicional si la excepción se ejecuta en un contexto donde `logger` no está definido globalmente.

---

## `pull_trial_json(...)`

```python
pull_trial_json(
    subject: str,
    session: str,
    run: str,
    trial_id: int,
    local_dir: str | Path = "./",
) -> Path
```

Descarga el archivo del trial al sistema local usando `adb pull`.

### Lógica interna

1. resuelve la ruta del archivo en el dispositivo,
2. crea el directorio local si no existe,
3. ejecuta `adb pull`,
4. devuelve la ruta local resultante.

### Uso típico

```python
local_path = tablet.pull_trial_json(
    subject="S01",
    session="1",
    run="1",
    trial_id=3,
    local_dir="./trials",
)
```

### Observación

Si el archivo no existe, el método retorna `None`, aunque la anotación de retorno indique `Path`. Nuevamente, el contrato efectivo es más amplio que el type hint.

---

## `list_trials(...)`

```python
list_trials(subject: str, session: str, run: str) -> list[int]
```

Lista los identificadores de trials disponibles en la carpeta remota correspondiente a `subject/session/run`.

### Lógica interna

1. ejecuta `adb shell ls -1 <folder>`,
2. filtra los nombres con patrón `trial_<n>.json`,
3. extrae los índices numéricos,
4. los devuelve ordenados.

### Uso típico

```python
available = tablet.list_trials("S01", "1", "1")
# por ejemplo: [1, 2, 3, 4, 5]
```

### Utilidad práctica

Este método resulta útil para:

- verificar cuántos trials fueron persistidos,
- detectar trials faltantes,
- inspeccionar si la tablet guardó correctamente una run,
- y ayudar a depurar problemas de sincronización o persistencia.

---

## `enable_logging(...)`

```python
enable_logging(enabled=True)
```

Habilita o deshabilita el `StreamHandler` del logger interno.

### Uso típico

```python
tablet.enable_logging(False)
```

Esto permite silenciar temporalmente los mensajes por consola sin eliminar el logger.

---

## Relación con `SessionManager`

`SessionManager` depende directamente de `TabletMessenger` para el ciclo experimental completo. En particular:

- genera el payload con `make_message(...)`,
- envía cambios de fase con `send_message(...)`,
- usa `sessionStartTime` para sincronización inicial con Android,
- y recupera luego el JSON del trial para reenviarlo como marcador LSL en `Tablet_Markers`.

Esto significa que `TabletMessenger` no es un componente aislado dentro de la arquitectura de handwriting: forma parte del contrato que conecta la lógica temporal de Python con la persistencia y visualización Android.

---

## Relación con Android

### `PCMessenger.kt`

`PCMessenger` recibe el broadcast, interpreta el JSON y lo deja disponible como `latestMessage`.

### `MainActivity.kt`

`MainActivity` consulta `sesionStatus`, `trialInfo`, `sessionStartTime` y otros campos adicionales para:

- actualizar la UI,
- controlar el flujo del trial,
- fijar el cero temporal local,
- y persistir los datos de cada trial.

En consecuencia, cualquier modificación de nombres de clave, estructura JSON o action del broadcast debe coordinarse en Python y Android al mismo tiempo.

---

## Ejemplo de uso mínimo

```python
from TabletMessenger import TabletMessenger
import logging

tablet = TabletMessenger(serial="R52W70ATD1W")
tablet.logger.setLevel(logging.INFO)

payload = tablet.make_message(
    sesionStatus="on",
    sesion_id=1,
    run_id=1,
    subject_id="test_subject",
    trialID=1,
    trialPhase="cue",
    letter="l",
    duration=4.0,
    sessionStartTime=1712345678.123,
)

tablet.send_message(payload, "com.handwriting.ACTION_MSG")
trial_data = tablet.read_trial_json("test_subject", "1", "1", 1)
available = tablet.list_trials("test_subject", "1", "1")
```

---

## Ejemplo de uso para descarga local

```python
from pathlib import Path

local_file = tablet.pull_trial_json(
    subject="test_subject",
    session="1",
    run="1",
    trial_id=1,
    local_dir=Path("./descargas_trials"),
)
```

---

## Limitaciones actuales

La implementación actual presenta varias limitaciones que conviene conocer:

1. **No existe confirmación de recepción desde Android**
   - el envío exitoso por ADB no garantiza que la app haya procesado correctamente el JSON.

2. **`history` y `buffer` no están integrados a la lógica real**
   - son atributos presentes, pero no sostienen una cola operativa efectiva.

3. **Los type hints son más estrictos que los retornos reales**
   - `read_trial_json(...)` puede devolver `[]`,
   - `pull_trial_json(...)` puede devolver `None`.

4. **El manejo de errores de `read_trial_json(...)` tiene un bug menor**
   - se usa `logger.error(...)` en lugar de `self.logger.error(...)`.

5. **La resolución de rutas es rígida**
   - sólo se contempla la convención actual basada en `Documents/<subject>/<session>/<run>/`.

6. **La clase no versiona el contrato JSON**
   - cualquier cambio de estructura debe controlarse manualmente.

---

## Recomendaciones de mejora

Para una versión más robusta del componente, resultaría razonable considerar:

- unificar type hints y retornos reales,
- registrar en `history` los payloads enviados,
- agregar validación estructural del JSON antes del envío,
- incorporar reintentos o verificación de recepción,
- encapsular mejor el contrato de rutas remotas,
- y versionar el esquema del mensaje para sincronizar Python y Android sin ambigüedades.

---

## Resumen

`TabletMessenger` es la capa de transporte simple que articula la comunicación PC → tablet y la recuperación de datos de trial desde Android. Su diseño actual es pragmático y funcional para el flujo experimental existente, pero depende fuertemente de convenciones compartidas con `MainActivity.kt`, `PCMessenger.kt` y `SessionManager`.

En ese contexto, su valor principal no reside en ser un sistema genérico de mensajería, sino en actuar como un conector operativo entre:

- la lógica temporal del experimento en Python,
- la interfaz y captura en Android,
- y los archivos JSON que posteriormente se reutilizan en análisis, reconstrucción de marcadores y sincronización de datos.
