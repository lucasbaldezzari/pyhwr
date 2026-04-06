# Documentación API: `PreExperimentManager`

## 1. Resumen

`PreExperimentManager` es un gestor de rondas de **pre-experimento** orientado a protocolos breves de calibración o registro auxiliar, actualmente para tres modos:

- `"emg"`
- `"eog"`
- `"basal"`

La clase implementa una **máquina de estados temporizada** basada en `QTimer`, administra **runs** y **trials**, actualiza una interfaz gráfica local compuesta por `LauncherApp`, `SquareWidget` y `StimuliWindow`, y emite marcadores por LSL mediante un outlet `Laptop_Markers`.

A diferencia de `SessionManager`, esta clase **no envía mensajes a la tablet** ni instancia `TabletMessenger`. Su salida observable consiste en:

1. cambios de estado en la UI local,
2. actualización del contenido visual de `StimuliWindow`,
3. envío de marcadores LSL serializados en JSON.

---

## 2. Ubicación en la arquitectura

Dentro del flujo general de la aplicación, `PreExperimentManager` es instanciado desde `RunConfigurationApp` cuando la tarea seleccionada es `basal`, `emg` o `eog`.

Flujo típico:

```text
InitAPP -> RunConfigurationApp -> PreExperimentManager
```

Responsabilidades principales:

- construir el orden de acciones por run,
- controlar las transiciones temporales entre fases,
- mostrar instrucciones o estímulos locales,
- registrar tiempos absolutos de eventos relevantes,
- emitir un marcador LSL por trial.

No es un widget visual en sí mismo: hereda de `QObject` y compone ventanas/widgets auxiliares.

---

## 3. Firma de la clase

```python
class PreExperimentManager(QObject):
```

### Fases por defecto

```python
PHASES = {
    "first_jump": {"next": "start", "duration": 4.0},
    "start": {"next": "precue", "duration": 1.0},
    "precue": {"next": "cue", "duration": 0.1},
    "cue": {"next": "rest", "duration": 5.0},
    "rest": {"next": "trialInfo", "duration": 4.0},
    "trialInfo": {"next": "sendMarkers", "duration": 0.1},
    "sendMarkers": {"next": "start", "duration": 0.1},
}
```

Observaciones:

- La clase comienza en `first_jump`.
- `fadeoff` aparece en `handle_phase_transition()`, pero **no está definido** en `PHASES`, por lo que no forma parte del flujo normal.
- El ciclo normal de un trial es:

```text
first_jump -> start -> precue -> cue -> rest -> trialInfo -> sendMarkers -> start
```

---

## 4. Constructor

```python
PreExperimentManager(
    sessioninfo,
    pre_experiment,
    mainTimerDuration=50,
    n_runs=1,
    randomize_per_run=True,
    seed=None,
    cue_base_duration=4.5,
    cue_tmin_random=1.0,
    cue_tmax_random=2.0,
    rest_base_duration=4,
    rest_tmin_random=0.0,
    rest_tmax_random=1.0,
    randomize_cue_duration=False,
    randomize_rest_duration=False,
    emg_actions=None,
)
```

### Parámetros

#### `sessioninfo: SessionInfo`
Objeto con metadatos de sesión. La clase consume tanto atributos (`sessioninfo.sub`) como acceso tipo diccionario (`sessioninfo["bids_file"]`, `sessioninfo["root_folder"]`, `sessioninfo["ses"]`, `sessioninfo["run"]`).

#### `pre_experiment: str`
Tipo de pre-experimento. Se normaliza a minúsculas y debe ser uno de:

- `"emg"`
- `"eog"`
- `"basal"`

Cualquier otro valor provoca `ValueError`.

#### `mainTimerDuration: int = 50`
Intervalo del timer principal en milisegundos. Controla la frecuencia con que se chequea si debe ocurrir una transición de fase.

#### `n_runs: int = 1`
Cantidad total de runs.

#### `randomize_per_run: bool = True`
Si es `True`, el orden de acciones se permuta independientemente para cada run.

#### `seed: int | None = None`
Semilla para `numpy.random.default_rng`, útil para reproducibilidad.

#### `cue_base_duration: float = 4.5`
Duración base del `cue` en segundos.

#### `cue_tmin_random: float = 1.0`
Límite inferior del incremento aleatorio agregado a `cue_base_duration` cuando `randomize_cue_duration=True`.

#### `cue_tmax_random: float = 2.0`
Límite superior del incremento aleatorio agregado a `cue_base_duration` cuando `randomize_cue_duration=True`.

#### `rest_base_duration: float = 4`
Duración base del período `rest` en segundos.

#### `rest_tmin_random: float = 0.0`
Límite inferior del incremento aleatorio agregado al `rest`.

#### `rest_tmax_random: float = 1.0`
Límite superior del incremento aleatorio agregado al `rest`.

#### `randomize_cue_duration: bool = False`
Si es `True`, recalcula la duración de `cue` antes de cada fase `cue`.

#### `randomize_rest_duration: bool = False`
Si es `True`, recalcula la duración de `rest` antes de cada fase `rest`.

#### `emg_actions: list[str] | None = None`
Lista personalizada de acciones para la ronda EMG. Si no se especifica, se usa:

```python
[
    "cerrar las manos",
    "mover brazos",
    "morder y contraer músculos del cuello",
]
```

---

## 5. Selección de acciones por tipo de pre-experimento

### Modo `emg`
Usa `self.emg_actions`.

### Modo `eog`
Usa:

```python
[
    "cruz_arriba",
    "cruz_abajo",
    "cruz_izquierda",
    "cruz_derecha",
]
```

### Modo `basal`
Usa una única acción:

```python
["basal"]
```

### Consecuencia práctica

`self.trials_per_run = len(self.actions)`

Por lo tanto:

- EMG: un trial por acción definida.
- EOG: cuatro trials por run.
- BASAL: un trial por run.

---

## 6. Estado interno principal

### Control de sesión

- `self.pre_experiment`
- `self.actions`
- `self.trials_per_run`
- `self.n_runs`
- `self.randomize_per_run`
- `self.current_run`
- `self.current_trial`
- `self.trials_acummulated`
- `self.current_action`
- `self.session_finished`

### Control temporal

- `self.phases`
- `self.in_phase`
- `self.last_phase`
- `self.next_transition`
- `self.creation_time`
- `self._last_phase_time`

### Tiempos registrados nominalmente

La clase declara además:

- `self.sessionStartTime`
- `self.trialStartTime`
- `self.precueTime`
- `self.trialCueTime`
- `self.trialFadeOffTime`
- `self.trialRestTime`
- `self.sessionFinalTime`

Sin embargo, en la implementación actual los timestamps operativos se almacenan realmente en `self.laptop_marker_dict`, no en estos atributos individuales.

### Timers Qt

- `self.mainTimer`: chequea transiciones de fase.
- `self.uiTimer`: actualiza la etiqueta de información cada 100 ms.

### LSL

- `self.laptop_marker`: instancia de `MarkerManager`.
- `self.laptop_marker_dict`: diccionario serializable con la información del trial actual.

### UI

- `self.launcher`: ventana de control `LauncherApp`.
- `self.information_label`: `SquareWidget` con resumen textual de la ronda.
- `self.marcador_inicio`: `SquareWidget` visual de inicio.
- `self.marcador_cue`: `SquareWidget` visual asociado al cue.
- `self.marcador_calibration`: `SquareWidget` rotulado “Para calibrar sensores”.
- `self.stimuli_window`: ventana de estímulos `StimuliWindow`.

---

## 7. Marcadores LSL emitidos

`PreExperimentManager` crea un outlet:

```python
MarkerManager(
    stream_name="Laptop_Markers",
    stream_type="Markers",
    source_id="Laptop",
    channel_count=1,
    channel_format="string",
    nominal_srate=0,
)
```

El payload enviado en fase `sendMarkers` es un JSON derivado de:

```python
{
    "trialID": ...,
    "letter": ...,
    "runID": ...,
    "sessionStartTime": ...,
    "trialStartTime": ...,
    "trialPrecueTime": ...,
    "trialCueTime": ...,
    "trialFadeOffTime": ...,
    "trialRestTime": ...,
    "sessionFinalTime": ...,
}
```

Notas:

- El campo `letter` se reutiliza para la acción actual, aunque en pre-experimentos no siempre representa una letra literal.
- En la sesión final se sobrescriben `letter="fin"` y `trialID="fin"`.
- No existe outlet `Tablet_Markers` en esta clase.

---

## 8. Ciclo de vida de un run/trial

### Inicio de la sesión

`startSession()`:

1. cambia el color de `marcador_inicio` a blanco,
2. fija `creation_time` en ms absolutos,
3. guarda `sessionStartTime` en `laptop_marker_dict`,
4. prepara el primer trial con `_prepare_next_trial()`,
5. deja `next_transition` apuntando al final de la fase actual (`first_jump`),
6. ejecuta `handle_phase_transition()` inmediatamente,
7. arranca `mainTimer` y `uiTimer`.

Importante: el primer `handle_phase_transition()` ocurre todavía en `first_jump`, no en `start`.

### Avance automático

`update_main()` compara `time.time()` con `self.next_transition`. Cuando el tiempo se supera:

1. llama a `_advance_phase()`,
2. luego a `handle_phase_transition()`.

### Final de un trial

En `sendMarkers`:

1. serializa `laptop_marker_dict`,
2. lo envía por LSL,
3. prepara el siguiente trial,
4. si no quedan más trials/runs, llama a `_finish_session()`.

### Final de la sesión

`_finish_session()`:

- marca la sesión como finalizada,
- actualiza `sessionFinalTime`,
- pone `letter="fin"` y `trialID="fin"`,
- detiene timers,
- muestra mensajes de cierre en la UI.

---

## 9. Semántica visual por tipo de ronda

## 9.1. `emg`

Durante `cue`:

- se oculta la cruz,
- se muestra `label_orden`,
- se actualiza la orden textual con `current_action`.

Fuera de `cue`:

- `label_orden` se oculta.

## 9.2. `eog`

Durante `cue`:

- se oculta `label_orden`,
- se muestra la cruz,
- `current_state` toma valores como `cruz_arriba`, `cruz_abajo`, `cruz_izquierda`, `cruz_derecha`.

Fuera de `cue`:

- la cruz vuelve al centro con `current_state = "cruz_centrada"`.

## 9.3. `basal`

En todas las fases relevantes:

- `label_orden` permanece oculto,
- la cruz permanece visible,
- `current_state = "cruz_centrada"`.

## 9.4. `first_jump`

Se presenta una instrucción previa:

```text
Prepárate...
```

con color naranja y tamaño de fuente grande.

## 9.5. Cierre

Se presenta:

```text
Podes descansar...
```

con color verde.

---

## 10. API pública y semipública

### `update_main() -> bool`
Avanza de fase cuando el tiempo programado se supera.

Retorna:

- `True` si hubo transición,
- `False` si no hubo transición o si la sesión ya terminó.

### `nextPhase()`
Fuerza el avance a la siguiente fase de manera manual/asíncrona. Solo llama a `_advance_phase()`. No ejecuta automáticamente `handle_phase_transition()`.

### `moveTo(phase_name)`
Intenta mover manualmente a una fase específica.

**Advertencia:** la implementación actual usa `self.now`, atributo que no existe. En el estado actual del código, este método es defectuoso y probablemente lance una excepción si se ejecuta.

### `get_elapsed_time() -> float`
Devuelve el tiempo transcurrido desde el inicio de sesión en milisegundos.

### `runSession()`
Obtiene o crea una instancia de `QApplication`, pero no ejecuta el event loop ni inicia la sesión. Su utilidad práctica actual es limitada.

### `initUI()`
Construye toda la UI asociada al manager, conecta señales del launcher y muestra ventanas/widgets.

### `startSession()`
Inicia la secuencia temporal del protocolo.

### `stopSession()`
Detiene timers, marca la sesión como finalizada y muestra el mensaje de fin.

### `quitSession()`
Detiene timers, muestra el mensaje final, cierra el launcher y termina la aplicación Qt.

---

## 11. Métodos internos relevantes

### `_advance_phase()`
Actualiza:

- `last_phase`
- `in_phase`
- `_last_phase_time`
- `next_transition`

### `_prepare_next_trial() -> bool`
Avanza `(run, trial)` y actualiza `current_action`.

Retorna:

- `True` si pudo preparar un nuevo trial,
- `False` si la sesión ya no tiene trials pendientes.

### `_set_random_cue_duration()`
Valida límites y asigna:

```python
self.phases["cue"]["duration"] = cue_base_duration + extra
```

### `_set_random_rest_duration()`
Análogo para `rest`.

### `handle_phase_transition()`
Es el núcleo de la lógica por fase. Se encarga de:

1. recalcular duraciones aleatorias si corresponde,
2. actualizar `runID`, `trialID` y `letter` en `laptop_marker_dict`,
3. despachar la acción correspondiente a la fase,
4. actualizar los estímulos visuales.

### `_update_stimuli()`
Sincroniza `StimuliWindow` con `pre_experiment` y fase actual.

### `_on_phase(time_key, color, extra_action=None, log=None)`
Método auxiliar para:

- registrar el timestamp absoluto de la fase en `laptop_marker_dict`,
- actualizar también `sessionFinalTime`,
- cambiar color de `marcador_cue`,
- emitir logging opcional.

### `_update_information_label()`
Actualiza el `SquareWidget` informativo con:

- run actual,
- trial actual,
- acción actual,
- duración actual del cue,
- tiempo transcurrido.

### `_on_first_jump()`
Muestra la instrucción “Prepárate...” en `StimuliWindow`.

### `_send_markers_phase()`
Serializa y envía `laptop_marker_dict` por LSL y luego prepara el siguiente trial.

### `_make_run_order()`
Genera la lista de acciones de un run. Si `randomize_per_run=True`, la permuta con el RNG del objeto.

### `_show_end_message()`
Actualiza `StimuliWindow` e `information_label` con el mensaje final.

---

## 12. Dependencias contractuales

## 12.1. `SessionInfo`
`PreExperimentManager` asume que `sessioninfo`:

- expone atributos `.sub`, `.ses`, `.run`,
- soporta indexación tipo diccionario para `"bids_file"` y `"root_folder"`.

Eso coincide con la implementación actual de `SessionInfo`, que ofrece `__getitem__()` delegando en `to_dict()`.

## 12.2. `LauncherApp`
`initUI()` conecta:

- `start_session_signal -> startSession`
- `stop_session_signal -> stopSession`
- `quit_session_signal -> quitSession`

Además usa `update_session_info(...)` para propagar metadatos de sesión a la interfaz.

## 12.3. `SquareWidget`
Se usa como panel visual y como marcador de color. Métodos utilizados:

- `change_text(...)`
- `change_color(...)`

## 12.4. `StimuliWindow`
Aunque el archivo fuente no fue parte del conjunto actual, el contrato mínimo inferible por uso es:

- atributo `label_orden`,
- atributo `cruz`,
- atributo `current_state`,
- método `update_order(...)`,
- método `update_positions()`,
- métodos de ventana estándar Qt: `show()`, `raise_()`, `activateWindow()`, `update()`, `repaint()`.

---

## 13. Ejemplos de uso

### Ejemplo mínimo

```python
import sys
import time
import logging
from PyQt5.QtWidgets import QApplication
from pyhwr.utils import SessionInfo
from pyhwr.managers import PreExperimentManager

logging.basicConfig(level=logging.INFO)
app = QApplication(sys.argv)

session_info = SessionInfo(
    sub=1,
    ses=1,
    task="basal",
    run=1,
    suffix="eeg",
    session_date=time.strftime("%Y-%m-%d"),
    bids_file="sub-01_ses-01_task-basal_run-01_eeg.bdf",
)

manager = PreExperimentManager(
    session_info,
    pre_experiment="basal",
    n_runs=1,
    randomize_per_run=True,
    seed=None,
    cue_base_duration=1.0,
    cue_tmin_random=0.1,
    cue_tmax_random=0.5,
    randomize_cue_duration=True,
    rest_base_duration=2.0,
    rest_tmin_random=0.1,
    rest_tmax_random=1.0,
    randomize_rest_duration=True,
)

sys.exit(app.exec_())
```

### Instanciación desde `RunConfigurationApp`

La integración prevista por la UI es:

```python
self.manager = PreExperimentManager(
    session_info,
    pre_experiment=task,
    n_runs=n_runs,
    randomize_per_run=self.randomize_per_run_box.isChecked(),
    seed=self.get_semilla(),
    cue_base_duration=cue_base_duration,
    cue_tmin_random=cue_tmin,
    cue_tmax_random=cue_tmax,
    randomize_cue_duration=randomize_cue,
    rest_base_duration=rest_base_duration,
    rest_tmin_random=rest_tmin,
    rest_tmax_random=rest_tmax,
    randomize_rest_duration=randomize_rest,
)
```

---

## 14. Diferencias importantes respecto de `SessionManager`

`PreExperimentManager` reutiliza gran parte del patrón arquitectónico de `SessionManager`, pero hay diferencias sustantivas:

### 14.1. No existe `TabletMessenger`
No se envían mensajes ADB/JSON a la tablet.

### 14.2. No existe `Tablet_Markers`
Solo se emiten `Laptop_Markers`.

### 14.3. El estímulo es local
La lógica de estímulo se resuelve en `StimuliWindow`, no en la app Android.

### 14.4. El dominio semántico es “acción”, no “letra”
Internamente algunos campos siguen llamándose `letter`, pero en EMG/EOG almacenan acciones o estados oculares.

---

## 15. Observaciones de diseño y puntos frágiles

### 15.1. `moveTo()` está roto
Usa `self.now`, atributo inexistente.

### 15.2. `fadeoff` es inconsistente
Aparece en el despachador de fases, pero no en `PHASES`. En el flujo actual es inalcanzable salvo manipulación manual del estado.

### 15.3. La docstring heredada es parcialmente engañosa
Habla de “comunicación con tablet”, pero el `TabletMessenger` está comentado y no se usa.

### 15.4. Atributos temporales redundantes
`sessionStartTime`, `trialStartTime`, etc. se declaran como atributos, pero los valores útiles se escriben en `laptop_marker_dict`.

### 15.5. `session_status` no se actualiza
Se inicializa en `"standby"`, pero no participa del flujo operativo.

### 15.6. `accumulated_time` no se usa
Queda como resto de una lógica de acumulación temporal no finalizada.

### 15.7. `runSession()` está incompleto
Obtiene `QApplication`, pero no inicia sesión ni event loop.

### 15.8. `marcador_calibration` no interviene en la lógica
Se crea y se muestra, pero no hay cambios de estado asociados en el código actual.

### 15.9. Campo `letter` reutilizado
En pre-experimentos sería más claro renombrarlo a `action` en el payload LSL, o documentar firmemente su semántica extendida.

---

## 16. Recomendaciones de mejora

1. Corregir `moveTo()` usando `time.time()` o una función temporal unificada.
2. Eliminar `fadeoff` del dispatcher o incorporarlo explícitamente a `PHASES`.
3. Renombrar `letter` a `action` en los marcadores de pre-experimento.
4. Eliminar o reutilizar los atributos temporales redundantes.
5. Implementar una interfaz explícita o abstracta para `StimuliWindow`.
6. Decidir si `marcador_calibration` debe tener un rol funcional o desaparecer.
7. Ajustar la docstring del constructor para reflejar que no hay mensajería con tablet.
8. Si se desea trazabilidad más homogénea con `SessionManager`, considerar un segundo outlet o un esquema de eventos más explícito por fase.

---

## 17. Resumen operativo

`PreExperimentManager` es un gestor de rondas cortas y temporizadas para pre-experimentos EMG/EOG/Basal. Su fortaleza es la simplicidad: organiza acciones, temporiza fases, actualiza una UI local y emite un marcador LSL estructurado por trial. Su limitación principal es que hereda parte del diseño de `SessionManager` sin completar algunas piezas, lo que deja restos de API y nombres que conviene refinar antes de considerarlo una interfaz pública estable.
