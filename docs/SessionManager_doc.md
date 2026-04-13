# `SessionManager`

## Descripción general

`SessionManager` es el componente encargado de manejar y administrar una ronda experimental completa de escritura a mano alzada dentro de la arquitectura `pyhwr`. Su responsabilidad principal consiste en coordinar la progresión temporal del experimento, la secuencia de runs y trials, la comunicación con la tablet Android, la emisión de marcadores LSL y la actualización de la interfaz local de control.

La clase hereda de `QWidget` y actúa como punto de integración entre los siguientes subsistemas:

- metadata de sesión (`SessionInfo`),
- mensajería PC → tablet (`TabletMessenger`),
- emisión de marcadores LSL (`MarkerManager`),
- interfaz de control local (`LauncherApp`),
- widgets auxiliares de estado (`SquareWidget`),
- y la app Android que persiste la información trial a trial.

En términos de diseño, `SessionManager` funciona como el **orquestador central** del experimento completo.

---

## Responsabilidades principales

`SessionManager` concentra cinco responsabilidades operativas:

1. **Configurar la sesión experimental**
   - letras por trial,
   - número de runs,
   - orden de presentación,
   - duraciones de `cue` y `rest`,
   - aleatorización y semilla.

2. **Administrar la máquina de estados temporal**
   - avanzar automáticamente entre fases,
   - actualizar el tiempo objetivo de transición,
   - ejecutar acciones específicas en cada fase.

3. **Sincronizar la laptop con la tablet**
   - enviar mensajes JSON por ADB broadcast,
   - informar la fase actual,
   - proporcionar `sessionStartTime` para sincronización temporal,
   - solicitar el cierre de sesión en Android.

4. **Emitir marcadores LSL**
   - un stream para eventos reconstruidos en la laptop,
   - un stream para el contenido persistido por la tablet.

5. **Actualizar la interfaz de control local**
   - mostrar metadata de la sesión,
   - exponer controles de inicio, detención y cierre,
   - visualizar el estado del cue y el avance temporal.

---

## Dependencias directas

### `SessionInfo`

`SessionManager` recibe un objeto `SessionInfo` que encapsula la metadata de la sesión. Ese objeto se consume de forma mixta:

- por atributo, por ejemplo `sessioninfo.session_id` o `sessioninfo.subject_id`,
- y por indexación, por ejemplo `sessioninfo["bids_file"]` o `sessioninfo["root_folder"]`.

Esto es posible porque `SessionInfo` implementa `__getitem__()` como fachada sobre `to_dict()`.

### `TabletMessenger`

`TabletMessenger` se utiliza para:

- construir mensajes con `make_message(...)`,
- enviarlos a Android con `send_message(...)`,
- leer `trial_<id>.json` con `read_trial_json(...)`,
- y listar/descargar JSONs almacenados por la tablet.

### `MarkerManager`

`MarkerManager` encapsula un `StreamOutlet` de LSL y permite enviar payloads de tipo `dict` o `str` como muestras de un stream de marcadores.

### `LauncherApp`

`LauncherApp` provee la interfaz local de operación. Expone señales para iniciar, detener y cerrar la sesión.

### `SquareWidget`

`SquareWidget` se utiliza como widget auxiliar para mostrar:

- información textual de la sesión,
- estado del cue,
- y un bloque visual reservado para calibración.

---

## Firma del constructor

```python
SessionManager(
    sessioninfo,
    mainTimerDuration=50,
    tabid="com.handwriting.ACTION_MSG",
    experimento="ejecutada",
    n_runs=1,
    letters=None,
    randomize_per_run=True,
    seed=None,
    cue_base_duration=4.5,
    cue_tmin_random=1.0,
    cue_tmax_random=2.0,
    rest_base_duration=1,
    rest_tmin_random=0.0,
    rest_tmax_random=1.0,
    randomize_cue_duration=True,
    randomize_rest_duration=True,
    tabletID="R52Y50AG4FF",
)
```

### Parámetros relevantes

- `sessioninfo`: instancia de `SessionInfo` con la metadata de la sesión.
- `mainTimerDuration`: período del timer principal, en milisegundos.
- `tabid`: action Android usada para el broadcast ADB.
- `experimento`: etiqueta textual del tipo de experimento.
- `n_runs`: cantidad de runs.
- `letters`: lista de letras por run. Si es `None`, se usa el set por defecto.
- `randomize_per_run`: si es `True`, mezcla el orden de letras en cada run.
- `seed`: semilla para el generador pseudoaleatorio usado en el orden por run.
- `cue_base_duration`: duración base de la fase `cue`.
- `cue_tmin_random`, `cue_tmax_random`: rango adicional aleatorio para `cue`.
- `rest_base_duration`: duración base de la fase `rest`.
- `rest_tmin_random`, `rest_tmax_random`: rango adicional aleatorio para `rest`.
- `randomize_cue_duration`: habilita o no la aleatorización de `cue`.
- `randomize_rest_duration`: habilita o no la aleatorización de `rest`.
- `tabletID`: serial ADB del dispositivo Android.

---

## Configuración experimental

### Letras por defecto

Si no se entrega una lista explícita, la sesión usa el siguiente conjunto:

```python
['e', 'a', 'o', 's', 'n', 'r', 'u', 'l', 'd', 'm']
```

### Runs y trials

La estructura de repetición queda definida por:

- `trials_per_run = len(letters)`
- `total_trials = trials_per_run * n_runs`

El estado discreto de avance se mantiene con:

- `current_run`,
- `current_trial`,
- `trials_acummulated`,
- `current_letter`,
- `session_finished`.

### Orden de presentación

El orden por run se construye con `_make_run_order()`. Si `randomize_per_run=True`, cada run contiene una copia de `letters` mezclada con `self.rng.shuffle(...)`.

---

## Reproducibilidad y aleatorización

La clase instancia un generador reproducible con:

```python
self.rng = np.random.default_rng(seed)
```

Ese generador controla el **orden de letras por run** y también para las duraciones extra de `cue` y `rest`.

---

## Máquina de estados

La máquina de fases se define así:

```python
PHASES = {
    "first_jump": {"next": "start", "duration": 5.0},
    "start": {"next": "precue", "duration": 2.0},
    "precue": {"next": "cue", "duration": 1.0},
    "cue": {"next": "rest", "duration": 5.0},
    "fadeoff": {"next": "rest", "duration": 1.0},
    "rest": {"next": "trialInfo", "duration": 1.0},
    "trialInfo": {"next": "sendMarkers", "duration": 0.2},
    "sendMarkers": {"next": "start", "duration": 0.2},
}
```

### Flujo nominal

En su forma actual, la secuencia efectiva es:

```text
first_jump -> start -> precue -> cue -> rest -> trialInfo -> sendMarkers -> start
```

---

## Temporización

La clase usa dos `QTimer`:

### `mainTimer`

- frecuencia configurable mediante `mainTimerDuration`,
- responsable de decidir cuándo cambiar de fase,
- ejecuta `update_main()`.

### `uiTimer`

- intervalo fijo de 50 ms,
- actualiza la información visible en la UI,
- ejecuta `_update_information_label()`.

### Variables temporales internas

Se mantienen, entre otras, las siguientes referencias temporales:

- `creation_time`,
- `_last_phase_time`,
- `next_transition`,
- `sessionStartTime`,
- `trialStartTime`,
- `precueTime`,
- `trialCueTime`,
- `trialFadeOffTime`,
- `trialRestTime`,
- `sessionFinalTime`.

### Nota sobre la base temporal

La lógica principal de `SessionManager` utiliza `time.time()` para temporización y sellado temporal. Sólo `moveTo()` usa `local_clock()` de LSL. Esto introduce una mezcla de referencias temporales que no afecta el flujo nominal, pero sí conviene tener presente al interpretar operaciones manuales de cambio de fase.

---

## Comunicación con la tablet

### Canal de comunicación

La comunicación PC → tablet se realiza con `TabletMessenger.send_message(...)`, que construye un comando `adb shell am broadcast` sobre la action configurada en `tabid`, por defecto:

```python
"com.handwriting.ACTION_MSG"
```

### Estructura del mensaje

El payload sigue esta forma general:

```json
{
  "sesionStatus": "on",
  "session_id": "...",
  "run_id": 1,
  "subject_id": "...",
  "trialInfo": {
    "trialID": 1,
    "trialPhase": "cue",
    "letter": "a",
    "duration": 5.0
  }
}
```

El método `make_message(...)` admite además claves extra en nivel superior, por ejemplo `sessionStartTime`.

### Inicio de sesión

Al comenzar la sesión, `startSession()`:

1. fija `creation_time`,
2. calcula `t0_abs` en milisegundos,
3. guarda `sessionStartTime` en `laptop_marker_dict`,
4. prepara el primer trial,
5. envía a la tablet un mensaje inicial con `sessionStartTime=t0_abs`,
6. establece `next_transition`,
7. llama a `handle_phase_transition()`,
8. arranca los timers.

### Observaciones sobre el arranque

En el momento del primer envío, `in_phase` todavía vale `first_jump`. Eso significa que el primer broadcast de sesión incluye `trialPhase="first_jump"`.

En la implementación Android disponible, `MainActivity.kt` no define una rama explícita para `first_jump`. Por tanto, esa fase funciona más como estado interno del controlador que como fase operativa con efectos visibles definidos en Android.

Además, `startSession()` envía un mensaje inicial y, acto seguido, `handle_phase_transition()` vuelve a enviar otro mensaje con la fase actual. En consecuencia, el arranque puede producir un doble envío de la fase inicial.

---

## Contrato operativo observado en Android

La app Android recibe el broadcast con `PCMessenger`, que almacena el JSON en `latestMessage`. Luego `MainActivity.kt` interpreta `sesionStatus` y `trialInfo.trialPhase` para actualizar el flujo visual y persistir la información del trial.

### Fases reconocidas en Android

En el código observado, Android implementa comportamiento explícito para:

- `start`,
- `precue`,
- `cue`,
- `fadeoff`,
- `rest`,
- `trialInfo`.

### Comportamiento por fase

- **`start`**: limpia la pantalla, mantiene el círculo central visible y actualiza el estado del trial.
- **`precue`**: registra tiempo y dispara el sonido de precue.
- **`cue`**: oculta el círculo central, muestra la letra, habilita el dibujo y comienza el muestreo.
- **`fadeoff`**: limpia la pantalla y vuelve a mostrar el círculo central.
- **`rest`**: limpia la pantalla y muestra un mensaje de descanso.
- **`trialInfo`**: consume puntos, eventos `penDown`/`penUp`, construye el JSON del trial y lo guarda en almacenamiento.

### Sincronización temporal PC ↔ tablet

La tablet espera recibir `sessionStartTime` al comienzo de la sesión. Ese valor se usa como referencia para alinear los tiempos Android con la base temporal de la laptop.

Según `MainActivity.kt`, los tiempos relativos de trial se obtienen a partir de una referencia compartida derivada de:

- `t0Laptop = sessionStartTime` recibido desde la PC,
- `t0TabletNano = System.nanoTime()` capturado en Android.

Con esa convención, eventos como `trialStartTime`, `trialCueTime`, `trialRestTime`, `penDownMarkers` y la mayoría de los timestamps de coordenadas quedan expresados sobre una escala temporal alineada con la laptop.

---

## Persistencia del trial en la tablet

Durante `trialInfo`, Android construye y guarda un JSON con el siguiente esquema conceptual:

```json
{
  "trialID": 1,
  "letter": "a",
  "runID": "1",
  "sessionStartTime": 0,
  "trialStartTime": 0,
  "trialPrecueTime": 0,
  "trialCueTime": 0,
  "trialFadeOffTime": 0,
  "trialRestTime": 0,
  "penDownMarkers": [],
  "penUpMarkers": [],
  "coordinates": [[x, y, t], ...],
  "sessionFinalTime": 0
}
```

Los archivos se almacenan como:

```text
/storage/emulated/0/Documents/<subject>/<session>/<run>/trial_<id>.json
```

Posteriormente, `SessionManager` relee ese JSON usando `TabletMessenger.read_trial_json(...)` y lo reemite por LSL.

---

## Marcadores LSL

`SessionManager` crea dos outlets de LSL.

### `Laptop_Markers`

Se inicializa con:

- `stream_name="Laptop_Markers"`,
- `stream_type="Markers"`,
- `source_id="Laptop"`,
- `channel_count=1`,
- `channel_format="string"`,
- `nominal_srate=0`.

El payload se arma con `laptop_marker_dict`, que contiene:

- `trialID`,
- `letter`,
- `runID`,
- `sessionStartTime`,
- `trialStartTime`,
- `trialPrecueTime`,
- `trialCueTime`,
- `trialFadeOffTime`,
- `trialRestTime`,
- `sessionFinalTime`.

### `Tablet_Markers`

Se inicializa con los mismos parámetros operativos, pero con:

- `stream_name="Tablet_Markers"`,
- `source_id="Tablet"`.

El payload enviado por este stream corresponde al JSON del trial recuperado desde la tablet.

### Momento de emisión

Ambos marcadores se envían durante la fase `sendMarkers`:

1. se intenta leer `trial_<id>.json` desde Android,
2. si la lectura es exitosa, el contenido se reenvía por `Tablet_Markers`,
3. luego se serializa `laptop_marker_dict` y se envía por `Laptop_Markers`.

---

## Flujo interno de ejecución

### Preparación del siguiente trial

`_prepare_next_trial()` se encarga de:

- avanzar dentro del run,
- pasar al siguiente run cuando corresponde,
- marcar `session_finished=True` cuando no quedan trials,
- y actualizar `current_letter`.

### Avance automático

`update_main()` compara `time.time()` contra `next_transition`. Cuando el tiempo actual supera ese umbral:

1. se avanza a la siguiente fase con `_advance_phase()`,
2. se ejecuta `handle_phase_transition()`.

### Lógica por transición

`handle_phase_transition()` realiza, en este orden:

1. logging de fase actual,
2. reconfiguración aleatoria de `cue` y/o `rest` si corresponde,
3. envío del estado actualizado a la tablet,
4. actualización de `laptop_marker_dict`,
5. ejecución de la acción específica de la fase.

### Acción de fase estándar

`_on_phase(...)` se utiliza para fases simples. Su comportamiento consiste en:

- registrar el tiempo de la fase en `laptop_marker_dict`,
- actualizar `sessionFinalTime` con el timestamp actual,
- cambiar el color del widget `marcador_cue`,
- y ejecutar una acción opcional adicional.

---

## Interfaz gráfica local

La inicialización de la UI se realiza en `initUI()`.

### `LauncherApp`

Se crea una instancia de `LauncherApp` y se actualiza con:

- sujeto,
- task,
- cantidad de runs,
- archivo BIDS,
- carpeta raíz,
- sesión,
- run.

Además, se conectan las señales:

- `start_session_signal` → `startSession`,
- `stop_session_signal` → `stopSession`,
- `quit_session_signal` → `quitSession`.

### `information_label`

Es un `SquareWidget` que presenta información dinámica del bloque:

- run actual,
- trial acumulado,
- letra actual,
- duración de cue,
- tiempo transcurrido.

### `marcador_cue`

Es un `SquareWidget` visual que cambia de color según la fase. En la implementación actual:

- negro en `start`, `precue`, `fadeoff` y `rest`,
- blanco en `cue`.

### `marcador_calibration`

Es un bloque visual con el texto “Para calibrar sensores”. En el estado actual del código se crea y se muestra, pero no participa en la lógica temporal del experimento.

---

## Finalización de sesión

Cuando ya no hay más trials, `_finish_session()`:

1. actualiza `sessionFinalTime`,
2. fuerza `letter="fin"`,
3. fuerza `trialID="fin"`,
4. cambia `in_phase` a `"final"`,
5. intenta enviar un mensaje final a la tablet,
6. muestra el mensaje de ronda finalizada,
7. detiene los timers y cierra el widget.

El mensaje final hacia Android usa:

- `sesionStatus="final"`,
- `run_id="final"`,
- `trialPhase="final"`,
- `letter="fin"`.

---

## Ejemplo mínimo de uso

```python
import sys
import time
import logging
from PyQt5.QtWidgets import QApplication
from pyhwr.utils import SessionInfo
from pyhwr.managers import SessionManager

logging.basicConfig(level=logging.INFO)

app = QApplication(sys.argv)

session_info = SessionInfo(
    sub=1,
    ses=1,
    task="entrenamiento",
    run=1,
    suffix="eeg",
    session_date=time.strftime("%Y-%m-%d"),
    bids_file="sub-01_ses-01_task-entrenamiento_run-01_eeg.bdf",
    root_folder="data/",
    session_id="entrenamiento",
    subject_id="sub-01",
)

manager = SessionManager(
    session_info,
    n_runs=2,
    letters=["a", "e", "l", "n"],
    randomize_per_run=True,
    seed=42,
    cue_base_duration=4.5,
    cue_tmin_random=0.0,
    cue_tmax_random=1.0,
    rest_base_duration=1.0,
    rest_tmin_random=0.0,
    rest_tmax_random=1.0,
    randomize_cue_duration=True,
    randomize_rest_duration=True,
    tabletID="R52Y50AG4FF",
)

sys.exit(app.exec_())
```

---

## Métodos relevantes

### `startSession()`
Inicia la sesión, prepara el primer trial, envía el mensaje inicial a la tablet y arranca los timers.

### `stopSession()`
Detiene la ejecución temporal y marca la sesión como finalizada.

### `quitSession()`
Detiene la ejecución, cierra el launcher y finaliza la aplicación Qt.

### `update_main()`
Controla el avance automático entre fases en función del tiempo.

### `handle_phase_transition()`
Centraliza la lógica ejecutada al entrar en cada fase.

### `_send_markers_phase()`
Lee el trial persistido por la tablet, lo envía por `Tablet_Markers`, envía el estado de laptop por `Laptop_Markers` y prepara el siguiente trial.

### `moveTo(phase_name)`
Permite mover manualmente la sesión a una fase concreta.

### `show_final_message()`
Reemplaza el contenido de `information_label` por un mensaje de finalización.

---

## Limitaciones y observaciones de diseño

### 1. `fadeoff` no integra el flujo nominal
Aunque existe como fase definida y Android sabe interpretarla, la transición normal de `cue` apunta directamente a `rest`.

### 2. Reproducibilidad incompleta de duraciones
La semilla del constructor no gobierna las duraciones aleatorias de `cue` y `rest`.

### 3. Mezcla de referencias temporales
La clase combina `time.time()` y `local_clock()` según el método utilizado.

### 4. Doble envío posible al inicio
`startSession()` emite un mensaje inicial y luego `handle_phase_transition()` vuelve a emitir el estado.

### 5. `first_jump` no tiene semántica operativa explícita en Android
La fase existe en el controlador de laptop, pero no aparece tratada de forma específica en `MainActivity.kt`.

### 6. `marcador_calibration` es actualmente decorativo
El widget se crea y muestra, pero no interviene en la lógica experimental.

### 7. `sessionFinalTime` se actualiza durante fases intermedias
En `_on_phase(...)`, `sessionFinalTime` se reescribe en cada entrada de fase. Por nombre semántico, ese campo sugiere un tiempo de fin de sesión, pero en la implementación también actúa como timestamp de última actualización.

### 8. Dependencia fuerte del contrato Android actual
La clase no es un scheduler experimental genérico. Está acoplada al formato JSON, a la action Android configurada y al esquema de persistencia de la app de tablet.

---

## Ubicación dentro de la arquitectura

El flujo general observado en la aplicación es:

```text
InitAPP
  -> RunConfigurationApp
      -> SessionInfo
      -> SessionManager
          -> LauncherApp
          -> TabletMessenger
          -> MarkerManager (Laptop_Markers / Tablet_Markers)
          -> MainActivity.kt en Android
```

Dentro de ese flujo, `SessionManager` es el componente que conecta configuración, ejecución temporal, UI local, mensajería Android y emisión LSL.

---

## Resumen

`SessionManager` implementa un controlador de sesión experimental orientado a adquisición sincronizada PC–tablet para tareas de escritura. Su diseño articula una máquina de estados temporizada, una interfaz local de control, un contrato de mensajería Android y dos streams de marcadores LSL.

La clase resulta adecuada como núcleo operativo del experimento, aunque presenta varios acoplamientos y decisiones de implementación que conviene mantener explícitos en cualquier mantenimiento futuro: reproducibilidad parcial, coexistencia de bases temporales, doble envío inicial, fase `fadeoff` fuera del flujo nominal y dependencia estrecha del esquema JSON persistido por la tablet.
