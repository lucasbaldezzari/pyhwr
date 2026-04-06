# Documentación técnica de `SessionManager`

## 1. Propósito general

`SessionManager` es una clase basada en `QWidget` cuyo objetivo es coordinar una sesión experimental completa. 
Controla:

- la máquina de estados de fases del experimento,
- la secuencia run/trial/letra,
- el envío de mensajes hacia la tablet Android,
- la generación y emisión de marcadores LSL de laptop y tablet,
- la interfaz local de control mediante `LauncherApp`,
- y un conjunto de widgets visuales auxiliares para seguimiento del estado de la sesión.

La clase está pensada como el orquestador central entre la PC/laptop, la app Android y los flujos LSL.

---

## 2. Dependencias directas

`SessionManager` depende de los siguientes componentes:

### 2.1 `SessionInfo`
Provee la metadata de la sesión: sujeto, sesión, task, run, nombre BIDS y carpeta raíz.
La clase admite acceso tanto por atributo como por índice (`__getitem__`), lo que explica que `SessionManager` use expresiones como:

- `self.sessioninfo.session_id`
- `self.sessioninfo.subject_id`
- `self.sessioninfo["bids_file"]`
- `self.sessioninfo["root_folder"]`

### 2.2 `TabletMessenger`
Responsable de:

- construir mensajes JSON con `make_message(...)`,
- enviarlos por ADB broadcast a la tablet con `send_message(...)`,
- leer el JSON del trial desde la tablet con `read_trial_json(...)`,
- listar y descargar trials guardados en `/storage/emulated/0/Documents/<subject>/<session>/<run>/`.

### 2.3 `MarkerManager`
Encapsula un `StreamOutlet` LSL y permite enviar marcadores serializados en formato string/JSON usando `sendMarker(...)`.

### 2.4 `LauncherApp`
Es la interfaz de control local de la sesión. Expone señales PyQt:

- `start_session_signal`
- `stop_session_signal`
- `quit_session_signal`

Además, muestra información BIDS, root folder, run, sesión y checkboxes de prerequisitos.

### 2.5 `SquareWidget`
Se usa para construir widgets visuales simples con texto HTML y color variable:

- `information_label`
- `marcador_cue`
- `marcador_calibration`

---

## 3. Responsabilidad funcional de la clase

A nivel alto, `SessionManager` hace lo siguiente:

1. Inicializa parámetros experimentales y el orden de trials.
2. Configura duraciones de fases, con o sin aleatorización.
3. Instancia los canales de comunicación:
   - ADB/JSON hacia la tablet
   - LSL para marcadores de laptop
   - LSL para marcadores leídos desde la tablet
4. Prepara la UI de control local.
5. Cuando se inicia la sesión:
   - fija un tiempo absoluto de inicio,
   - prepara el primer trial,
   - notifica a la tablet,
   - entra al ciclo temporizado de fases.
6. En cada transición de fase:
   - actualiza tiempos internos,
   - envía un mensaje a la tablet,
   - actualiza marcadores locales,
   - ejecuta acciones asociadas a la fase.
7. Al final de cada trial:
   - lee el JSON generado en la tablet,
   - lo reemite como marcador LSL de tablet,
   - emite el marcador LSL de laptop,
   - prepara el siguiente trial o finaliza la sesión.

---

## 4. Máquina de estados de fases

La máquina de estados está definida por el diccionario `PHASES`:

```python
PHASES = {
    "first_jump": {"next": "start", "duration": 5.},
    "start": {"next": "precue", "duration": 2.0},
    "precue": {"next": "cue", "duration": 1.0},
    "cue": {"next": "rest", "duration": 5.0},
    "fadeoff": {"next": "rest", "duration": 1.0},
    "rest": {"next": "trialInfo", "duration": 1.},
    "trialInfo": {"next": "sendMarkers", "duration": 0.2},
    "sendMarkers": {"next": "start", "duration": 0.2},
}
```

### Observaciones importantes

- La fase inicial real es `first_jump`.
- La fase `fadeoff` existe en la definición, pero la transición por defecto de `cue` va a `rest`, no a `fadeoff`.
- Por lo tanto, en la configuración actual, `fadeoff` no forma parte del flujo normal salvo que se fuerce manualmente con `moveTo(...)`.

### Flujo nominal actual

```text
first_jump -> start -> precue -> cue -> rest -> trialInfo -> sendMarkers -> start ...
```

Cuando se terminan los trials/runs, la sesión entra en finalización mediante `_finish_session()`.

---

## 5. Configuración experimental

## 5.1 Letras
Si el usuario no entrega una lista, se usan por defecto:

```python
['e', 'a', 'o', 's', 'n', 'r', 'u', 'l', 'd', 't']
```

## 5.2 Runs y trials
- `trials_per_run = len(self.letters)`
- `total_trials = trials_per_run * n_runs`

La clase mantiene:

- `current_run`
- `current_trial`
- `trials_acummulated`
- `current_letter`

## 5.3 Aleatorización
El orden por run se genera con `_make_run_order()`.

Si `randomize_per_run=True`, se mezcla el orden de letras dentro de cada run usando `self.rng.shuffle(base)`.

### Importante
Aunque la clase crea un generador reproducible con:

```python
self.rng = np.random.default_rng(seed)
```

las funciones `_set_random_cue_duration()` y `_set_random_rest_duration()` usan:

```python
np.random.uniform(...)
```

y no `self.rng.uniform(...)`.

Eso significa que la semilla pasada a `default_rng(seed)` no controla de manera reproducible las duraciones aleatorias de `cue` y `rest`; sólo controla el orden de las letras si se usa `self.rng.shuffle(...)`.

---

## 6. Duraciones de fases

## 6.1 Cue
Puede ser fija o aleatoria.

- Si `randomize_cue_duration=False`, la duración de `cue` es `cue_base_duration`.
- Si `randomize_cue_duration=True`, la duración se calcula como:

```python
cue_base_duration + U(cue_tmin_random, cue_tmax_random)
```

con validación de que:

- `cue_tmin_random >= 0`
- `cue_tmax_random >= 0`
- `cue_tmin_random < cue_tmax_random`

## 6.2 Rest
Análogo a `cue`:

```python
rest_base_duration + U(rest_tmin_random, rest_tmax_random)
```

con las mismas validaciones de consistencia.

---

## 7. Temporización

La clase usa dos `QTimer`:

### 7.1 `mainTimer`
- Intervalo configurable por `mainTimerDuration`
- Ejecuta `update_main()`
- Controla el avance temporal de fases

### 7.2 `uiTimer`
- Intervalo fijo de 50 ms
- Ejecuta `_update_information_label()`
- Sólo actualiza la información visual de la UI

## 7.3 Variables temporales relevantes

- `creation_time`
- `_last_phase_time`
- `next_transition`
- `sessionStartTime`
- `trialStartTime`
- `precueTime`
- `trialCueTime`
- `trialFadeOffTime`
- `trialRestTime`
- `sessionFinalTime`

---

## 8. Estructura de comunicación con la tablet

`TabletMessenger.make_message(...)` arma un mensaje con esta estructura:

```json
{
  "sesionStatus": "...",
  "session_id": "...",
  "run_id": "...",
  "subject_id": "...",
  "trialInfo": {
    "trialID": ...,
    "trialPhase": "...",
    "letter": "...",
    "duration": ...
  }
}
```

Además admite claves extra mediante `**extra`, por ejemplo `sessionStartTime`.

Luego `send_message(...)` lo serializa a JSON y lo envía por ADB broadcast usando la action Android dada por `tabid`, típicamente:

```python
"com.handwriting.ACTION_MSG"
```

---

## 9. Contrato observado con `MainActivity.kt`

La app Android escucha mensajes con `sesionStatus` y `trialInfo.trialPhase`. 
Según `MainActivity.kt`, interpreta al menos:

- `sesionStatus`: `on`, `off`, `standby`, `final`
- `trialPhase`: `start`, `precue`, `cue`, `fadeoff`, `rest`, `trialInfo`

### 9.1 Sincronización temporal PC-tablet
La tablet espera explícitamente `sessionStartTime` cuando recibe el inicio de sesión. Si no llega, reporta error y no puede sincronizar tiempos.

La sincronización se hace así:

- la laptop envía `sessionStartTime` absoluto en ms,
- la tablet guarda ese valor como `t0Laptop`,
- fija su `t0TabletNano = System.nanoTime()`,
- y luego computa tiempos relativos absolutos con:

```kotlin
nowRelativeToT0() = t0Laptop + (System.nanoTime() - t0TabletNano) / 1_000_000
```

Esto permite que eventos como `trialStartTime`, `trialCueTime` y timestamps de coordenadas/penDown queden en la misma escala temporal de la laptop.

### 9.2 Fases en Android
En la tablet:

- `start`: limpia pantalla, muestra estado del trial, mantiene el círculo central.
- `precue`: registra tiempo y reproduce sonido de precue.
- `cue`: muestra la letra, oculta el círculo central, habilita dibujo y activa `touchView.startSampling()`.
- `fadeoff`: limpia pantalla y vuelve a mostrar el círculo central.
- `rest`: limpia pantalla y muestra mensaje de descanso.
- `trialInfo`: no usa el buffer de muestreo periódico, sino `consumeNewPoints()`, `getPenUpTimestamps()` y `getPenDownTimestamps()` para construir el JSON persistido del trial.

### 9.3 Persistencia del trial en Android
Cada trial se guarda como:

```text
/storage/emulated/0/Documents/<subject>/<session>/<run>/trial_<id>.json
```

El JSON incluye:

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

Las coordenadas se guardan como listas tipo:

```json
[x, y, timestamp]
```

### 9.4 Rol de `PCMessenger`, `EventManager` y `TouchView`

#### `PCMessenger`
Actúa como receptor Android del broadcast `com.handwriting.ACTION_MSG`.

Responsabilidades observadas:

- registra/desregistra un `BroadcastReceiver`,
- parsea el extra `payload` como `JSONObject`,
- mantiene el último mensaje en `latestMessage`,
- opcionalmente puede reenviar información al host vía Logcat con `sendToHost(...)` o `sendTrialInfo(...)`.

En el flujo actual de `MainActivity`, `pcMessenger.start()` se llama en `onCreate()`, y luego el loop de estado consulta repetidamente `pcMessenger.latestMessage`.

#### `EventManager`
No es usado directamente por `SessionManager`, pero sí por la app Android durante `trialInfo`.
Su rol es el de acumulador interno de eventos y datos por trial.

Almacena:

- inicio y final de sesión,
- listas de `trialID`,
- tiempos de `start`, `precue`, `cue`, `fadeoff`, `rest`,
- listas de listas para `penDown` y `penUp`,
- listas de coordenadas `DrawPoint`.

Esto sirve como respaldo estructural de los datos del trial antes o además del guardado en JSON.

#### `TouchView`
`TouchView` define la estructura `DrawPoint(x, y, timestamp)` y mantiene tres buffers conceptualmente distintos:

1. `pathPoints`: trayectoria dibujada en pantalla,
2. `pendingPoints`: puntos nuevos consumibles por trial mediante `consumeNewPoints()`,
3. `sampledPoints`: muestreo periódico cada ~2 ms generado por `startSampling()`.

Además mantiene:

- `penDownTimestamps`,
- `penUpTimestamps`,
- el círculo central visual (`showCenterCircle`),
- y la capacidad de sincronizar timestamps de eventos táctiles mediante `timeProvider`.

### 9.5 Implicancia temporal importante en Android

`MainActivity` asigna:

```kotlin
touchView.timeProvider = { nowRelativeToT0() }
```

Por lo tanto, los timestamps asociados a `ACTION_DOWN`, `ACTION_MOVE`, `ACTION_UP` y a los `DrawPoint` producidos en `onTouchEvent(...)` quedan en la misma base temporal sincronizada con la laptop.

Sin embargo, el muestreo periódico de `startSampling()` usa `System.currentTimeMillis()` y no `timeProvider`.

Consecuencia:

- `pendingPoints`, `penDownTimestamps` y `penUpTimestamps` sí quedan alineados con `sessionStartTime` enviado por la PC,
- `sampledPoints` puede quedar en otra base temporal.

En la implementación actual, esto no rompe el JSON persistido del trial porque `trialInfo` usa `consumeNewPoints()` y no `consumeSampledPoints()`. Pero es un punto importante para documentar, porque afecta cualquier análisis futuro que pretenda usar `sampledPoints` como fuente principal de coordenadas.

---

## 10. Marcadores LSL

`SessionManager` crea dos emisores LSL:

### 10.1 `laptop_marker`
Stream de nombre:

```text
Laptop_Markers
```

### 10.2 `tablet_marker`
Stream de nombre:

```text
Tablet_Markers
```

Ambos se configuran como:

- `stream_type="Markers"`
- `channel_count=1`
- `channel_format="string"`
- `nominal_srate=0`

`MarkerManager.sendMarker(...)` serializa a JSON si el payload es dict;

### 10.3 Contenido del marcador de laptop
`laptop_marker_dict` contiene:

- `trialID`
- `letter`
- `runID`
- `sessionStartTime`
- `trialStartTime`
- `trialPrecueTime`
- `trialCueTime`
- `trialFadeOffTime`
- `trialRestTime`
- `sessionFinalTime`

Estos tiempos se completan progresivamente durante el flujo de fases.

### 10.4 Emisión de marcadores
La fase `sendMarkers` hace dos cosas:

1. Lee el JSON del trial desde la tablet y lo reemite por `tablet_marker`.
2. Serializa `laptop_marker_dict` y lo emite por `laptop_marker`.

---

## 11. Interfaz gráfica local

`initUI()` crea y configura:

### 11.1 `LauncherApp`
Ventana principal de control de sesión.

Se usa para:

- mostrar metadata de sesión,
- iniciar,
- detener,
- salir.

`SessionManager` conecta sus señales a:

- `startSession`
- `stopSession`
- `quitSession`

### 11.2 `information_label`
Widget tipo `SquareWidget` que muestra información dinámica:

- run actual
- trial actual
- letra actual
- duración actual de cue
- tiempo transcurrido

### 11.3 `marcador_cue`
Indicador visual cuyo color cambia según la fase:

- negro en `start`, `precue`, `fadeoff`, `rest`
- blanco en `cue`

### 11.4 `marcador_calibration`
Widget estático visual con texto “Para calibrar sensores”.

---

## 12. Inicio de sesión

`startSession()` realiza la secuencia de arranque:

1. fija `creation_time = time.time()*1000`
2. fija `t0_abs = time.time()*1000`
3. guarda `sessionStartTime` en `laptop_marker_dict`
4. prepara el primer trial con `_prepare_next_trial()`
5. envía mensaje inicial a la tablet con:
   - `sesionStatus="on"`
   - `trialPhase=self.in_phase`
   - `sessionStartTime=t0_abs`
6. fija `next_transition`
7. llama `handle_phase_transition()`
8. inicia `mainTimer` y `uiTimer`

### Observación importante
En el instante del arranque, `self.in_phase` sigue siendo `first_jump`, porque esa es la fase inicial definida por la máquina de estados.

Eso significa que el primer mensaje de inicio enviado a la tablet usa `trialPhase="first_jump"`.

Sin embargo, en `MainActivity.kt` no aparece un caso explícito para `first_jump`.
Por lo tanto, ese mensaje no tiene una acción específica en la tablet, salvo la lógica general de entrada en `sesionStatus="on"`.

Además, `startSession()` envía un mensaje inicial y luego llama `handle_phase_transition()`, que vuelve a enviar un mensaje con la fase actual. 
En el inicio, eso puede implicar doble envío de la fase inicial hacia la tablet.

---

## 13. Avance de fases

El ciclo principal funciona así:

### 13.1 `update_main()`
Compara `time.time()` con `next_transition`.  
Si el tiempo actual supera el umbral:

- llama `_advance_phase()`
- llama `handle_phase_transition()`

### 13.2 `_advance_phase()`
Actualiza:

- `last_phase`
- `in_phase`
- `next_transition`

tomando la transición `next` del diccionario `PHASES`.

### 13.3 `handle_phase_transition()`
1. re-randomiza duración de `cue` si corresponde,
2. re-randomiza duración de `rest` si corresponde,
3. envía mensaje a la tablet,
4. actualiza `laptop_marker_dict`,
5. ejecuta la acción asociada a la fase.

---

## 14. Preparación del siguiente trial

`_prepare_next_trial()`:

- avanza dentro del run actual,
- si terminó el run, pasa al siguiente,
- si no hay más runs, marca `session_finished=True` y retorna `False`,
- actualiza:
  - `current_run`
  - `current_trial`
  - `trials_acummulated`
  - `current_letter`

Esta función es la responsable directa del avance discreto run/trial.

---

## 15. Lógica de finalización del trial

La fase `sendMarkers` cumple el cierre efectivo de cada trial:

1. intenta leer `trial_<id>.json` desde la tablet,
2. si puede, lo emite como marcador LSL,
3. emite el marcador de laptop,
4. prepara el siguiente trial,
5. si no existe siguiente trial, finaliza la sesión.

---

## 16. Finalización de sesión

`_finish_session()`:

1. actualiza `sessionFinalTime` en el marcador de laptop,
2. fuerza:
   - `letter = "fin"`
   - `trialID = "fin"`
3. pone `self.in_phase = "final"`
4. intenta avisar a la tablet enviando:
   - `sesionStatus="final"`
   - `run_id="final"`
   - `trialPhase="final"`
   - `letter="fin"`
5. muestra el mensaje final en la UI
6. llama `stop()`

### En la tablet
`MainActivity.kt` sí contempla `sesionStatus="final"` y:
- guarda un JSON final,
- reproduce sonido de éxito,
- ejecuta limpieza de procesos.

---

## 17. Métodos principales

## 17.1 `__init__(...)`
Configura todo el estado interno, timers, mensajería, marcadores y UI.

## 17.2 `_advance_phase()`
Avanza al siguiente estado y recalcula el próximo instante de transición.

## 17.3 `_prepare_next_trial()`
Selecciona el próximo trial/letra. Devuelve `False` si la sesión terminó.

## 17.4 `_set_random_cue_duration()`
Calcula duración aleatoria del cue con validación de parámetros.

## 17.5 `_set_random_rest_duration()`
Calcula duración aleatoria del rest con validación de parámetros.

## 17.6 `update_main()`
Bucle temporizado que decide si hay que cambiar de fase.

## 17.7 `nextPhase()`
Permite forzar el avance de fase manualmente.

## 17.8 `moveTo(phase_name)`
Permite mover manualmente a una fase dada y recalcula `next_transition`.

## 17.9 `handle_phase_transition()`
Método central de transición de estado.

## 17.10 `_on_phase(time_key, color, extra_action=None, log=None)`
Rutina auxiliar para:
- guardar un tiempo de fase en `laptop_marker_dict`,
- cambiar color del indicador de cue,
- ejecutar acciones extra opcionales.

## 17.11 `_update_information_label()`
Actualiza el panel informativo de la sesión.

## 17.12 `_send_markers_phase()`
Lee JSON de la tablet, envía marcadores LSL y prepara el siguiente trial.

## 17.13 `get_elapsed_time()`
Devuelve tiempo transcurrido desde `creation_time` en ms.

## 17.14 `initUI()`
Crea y conecta la UI local.

## 17.15 `startSession()`
Inicia la sesión, notifica a la tablet y arranca timers.

## 17.16 `_finish_session()`
Cierra la sesión de manera ordenada.

## 17.17 `stopSession()`
Detiene la sesión sin cerrar la aplicación.

## 17.18 `quitSession()`
Detiene timers, cierra launcher y sale de la aplicación.

## 17.19 `stop()`
Detiene timers, muestra mensaje final y cierra el widget.

## 17.20 `_make_run_order()`
Genera el orden de letras para un run.

## 17.21 `show_final_message()`
Reemplaza el contenido del panel informativo por el mensaje “RONDA FINALIZADA”.

---

## 18. Ambigüedades y puntos a documentar explícitamente

Para una documentación honesta, conviene dejar asentados estos puntos:

### 18.1 `fadeoff` no está en el flujo normal
Aunque existe una acción en Android para `fadeoff`, el flujo Python actual pasa de `cue` a `rest`.

### 18.2 `first_jump` no tiene manejo explícito en Android
La laptop puede enviar `first_jump`, pero la tablet no muestra un caso específico para esa fase en el `when (newTrialPhase)` compartido.

### 18.3 Posible doble envío al inicio
`startSession()` envía un mensaje inicial y luego llama `handle_phase_transition()`, que vuelve a enviar mensaje de la fase actual.

### 18.4 Mezcla de relojes
FIX ARRELGADO. (Se usan `time.time()` y `local_clock()` en distintos puntos.)

### 18.5 Reproducibilidad parcial
El seed controla el shuffle de letras, pero no necesariamente la aleatorización de duraciones.

### 18.6 Dos bases temporales dentro de `TouchView`
Los eventos táctiles usan `timeProvider` cuando está configurado, pero `startSampling()` usa `System.currentTimeMillis()`.
Eso implica que no todos los timestamps generados por `TouchView` comparten necesariamente la misma referencia temporal.

### 18.7 `sessionFinalTime` del JSON de trial puede quedar en otra escala temporal
En `MainActivity`, durante `trialInfo`, el campo `sessionFinalTime` se asigna con `System.currentTimeMillis()`, mientras que otros tiempos de trial se calculan con `nowRelativeToT0()`.
Eso puede introducir una inconsistencia temporal dentro del JSON persistido del trial.

### 18.8 Error potencial en `TabletMessenger.read_trial_json()`
Dentro del `except`, el código usa `logger.error(...)`, pero en el archivo mostrado no existe una variable local/global `logger`; debería ser `self.logger.error(...)`.

### 18.9 Método `runSession()` incompleto
El método existe pero no implementa una lógica real de ejecución.

---

## 19. Archivos todavía opcionales para una documentación de ecosistema completo

Con los archivos ya revisados, la documentación funcional de `SessionManager` y de su contrato con Android es suficiente y consistente.

Lo único que seguiría siendo opcional si quisieras una documentación todavía más amplia del proyecto completo es:

- `launcherApp.ui` y estilos CSS, para describir la UI local a nivel visual y no sólo funcional,
- recursos Android (`layout XML`, `drawables`, `raw/`), si se quiere documentar también la capa de presentación y no sólo la lógica.

---

## 20. Conclusión

Con los archivos revisados, `SessionManager` puede documentarse como el coordinador principal del experimento. 
Su diseño une cuatro subsistemas:

1. **control experimental** (fases, runs, trials, letras),
2. **mensajería PC → tablet** (ADB + JSON),
3. **persistencia y retrolectura de trial data** (JSON por trial),
4. **marcadores LSL** (laptop y tablet).

La clase es funcionalmente clara y bien delimitada, aunque presenta algunos detalles de consistencia temporal y de flujo que conviene dejar explícitos en cualquier documentación formal. Con `EventManager`, `PCMessenger` y `TouchView` ya revisados, esos detalles quedan mejor caracterizados y la documentación resultante es bastante más fiel al comportamiento real del sistema.
