# PreExperimentManager

## Resumen

`PreExperimentManager` es el gestor de sesiones utilizado para rondas de preexperimento, en particular para tareas de tipo `basal`, `emg` y `eog`. Su arquitectura, temporización general y lógica de control de fases son, en términos prácticos, muy cercanas a las de `SessionManager`, pero con dos diferencias estructurales centrales: no realiza comunicación con la tablet y agrega una ventana de estímulos dedicada para presentar instrucciones o desplazamientos visuales durante la ronda. 

La clase se inicializa con un objeto `SessionInfo`, recibe la configuración temporal de la sesión, construye el orden de acciones por run y administra la progresión de cada trial mediante un `QTimer` principal. Al igual que `SessionManager`, mantiene una máquina de estados con fases secuenciales, actualiza un diccionario de marcadores temporales y publica eventos por LSL mediante `MarkerManager`. Sin embargo, a diferencia de la sesión de entrenamiento o escritura, aquí no se instancia `TabletMessenger`, no se envían mensajes ADB/JSON a Android y no se genera un stream `Tablet_Markers`; toda la lógica de estimulación y control se resuelve del lado de la aplicación de escritorio. fileciteturn29file0turn28file2turn28file8

## Rol dentro de la arquitectura

`PreExperimentManager` es instanciado desde `RunConfigurationApp` cuando el tipo de tarea seleccionado corresponde a `basal`, `emg` o `eog`. En ese flujo, `RunConfigurationApp` construye el `SessionInfo`, recoge desde la UI los parámetros temporales y crea el manager con el tipo de preexperimento especificado en `pre_experiment`. fileciteturn28file0turn28file3

Una vez creado, el manager despliega:

- un `LauncherApp` para iniciar, detener o salir de la sesión,
- varios `SquareWidget` para mostrar información de estado y marcadores visuales,
- y una `StimuliWindow` adicional para presentar instrucciones textuales o desplazamientos de una cruz de fijación, según el paradigma activo. fileciteturn29file1turn28file10

Esa `StimuliWindow` es la principal diferencia de interfaz respecto de `SessionManager`: en lugar de delegar la presentación del estímulo a la tablet, el estímulo se produce localmente dentro del entorno Qt. fileciteturn29file1turn28file2

## Diferencias principales respecto de SessionManager

### 1. No existe comunicación con la tablet

`SessionManager` crea un `TabletMessenger`, arma payloads JSON y los envía por ADB broadcast hacia Android durante las transiciones de fase y al finalizar la sesión. `PreExperimentManager` no importa ni instancia `TabletMessenger`, y su flujo no depende de `MainActivity`, `PCMessenger` ni de la persistencia de trials en la tablet. fileciteturn28file2turn28file8turn29file0

### 2. Sólo se emiten marcadores de laptop

`SessionManager` utiliza tanto `Laptop_Markers` como `Tablet_Markers`. `PreExperimentManager` crea únicamente un `MarkerManager` llamado `Laptop_Markers` y publica un único payload JSON por trial en la fase `sendMarkers`. fileciteturn28file9turn29file1

### 3. El estímulo visual se presenta localmente

En `SessionManager`, la tablet forma parte del lazo de estimulación. En `PreExperimentManager`, la presentación se resuelve en la aplicación de escritorio mediante `StimuliWindow`, con lógica específica para cada tipo de preexperimento:

- en `emg`, durante `cue` se muestra una orden textual,
- en `eog`, durante `cue` se mueve la cruz hacia arriba, abajo, izquierda o derecha,
- en `basal`, la cruz permanece centrada sin instrucción adicional. fileciteturn29file1

### 4. La unidad de trial no es una letra sino una acción

`SessionManager` organiza cada trial en torno a una letra (`current_letter`). `PreExperimentManager` lo hace en torno a una acción (`current_action`) definida a partir del tipo de preexperimento. Para `emg` usa por defecto acciones motoras, para `eog` utiliza direcciones de la cruz, y para `basal` define una única acción fija. fileciteturn29file0

## Máquina de estados

La clase mantiene una máquina de estados propia en `PHASES`, compuesta por:

- `first_jump`
- `start`
- `precue`
- `cue`
- `rest`
- `trialInfo`
- `sendMarkers` fileciteturn29file0

La secuencia funcional es muy similar a la de `SessionManager`: un temporizador principal consulta periódicamente si el instante actual supera `next_transition`; cuando eso ocurre, la clase avanza de fase, ejecuta la acción asociada y actualiza los estímulos locales. fileciteturn29file1turn28file2

La fase `first_jump` se utiliza como pantalla preparatoria. Durante esa fase, si existe `StimuliWindow`, se muestra el mensaje “Prepárate...”. Luego la sesión avanza hacia el resto del ciclo de fases. fileciteturn29file1

## Acciones por tipo de preexperimento

### EMG

Para `emg`, el manager define por defecto la lista:

- `cerrar las manos`
- `mover brazos`
- `morder y contraer músculos del cuello` fileciteturn29file0

Durante la fase `cue`, la acción activa se muestra como texto en `StimuliWindow`. Fuera de `cue`, esa orden se oculta. fileciteturn29file1

### EOG

Para `eog`, la lista de acciones es:

- `cruz_arriba`
- `cruz_abajo`
- `cruz_izquierda`
- `cruz_derecha` fileciteturn29file0

Durante `cue`, la cruz cambia de posición en la `StimuliWindow` según la acción actual. En las demás fases, la cruz vuelve al centro. fileciteturn29file1

### Basal

Para `basal`, el trial se reduce a una única acción fija (`basal`) y la ventana de estímulos mantiene la cruz centrada. Este modo actúa como una ronda de fijación sin instrucción motora ni desplazamiento ocular. fileciteturn29file0turn29file1

## Interfaz gráfica asociada

La interfaz de `PreExperimentManager` se construye en `initUI()` y contiene cuatro piezas principales:

1. `LauncherApp`, que expone las señales de control de sesión.
2. `information_label`, implementado con `SquareWidget`, que resume run, trial, acción y tiempo transcurrido.
3. `marcador_inicio` y `marcador_cue`, también implementados con `SquareWidget`, usados como marcadores visuales locales.
4. `marcador_calibration`, un widget adicional con texto de calibración que diferencia esta clase del flujo estándar de `SessionManager`.
5. `StimuliWindow`, que materializa los estímulos del preexperimento. fileciteturn29file1turn28file10

Desde la perspectiva documental, el elemento extra más relevante es `marcador_calibration`: el widget se crea como parte de la UI, pero no participa activamente en la lógica de transición de fases ni en el despacho de marcadores. Por lo tanto, forma parte del layout visual más que del control efectivo de la sesión. fileciteturn29file1

## Marcadores y temporización

Durante la sesión se actualiza `laptop_marker_dict`, que contiene, entre otras claves, `trialID`, `letter`, `runID`, `sessionStartTime`, `trialStartTime`, `trialPrecueTime`, `trialCueTime`, `trialFadeOffTime`, `trialRestTime` y `sessionFinalTime`. Aunque la clave se denomina `letter`, en este manager se utiliza para almacenar la acción actual del preexperimento. fileciteturn29file0turn29file1

En la fase `sendMarkers`, ese diccionario se serializa como JSON y se envía por LSL mediante `self.laptop_marker.sendMarker(...)`. No existe un envío paralelo a Android ni recuperación posterior de datos desde la tablet. fileciteturn29file1

## Inicio y finalización

Al iniciar la sesión, `startSession()` hace lo siguiente:

- cambia el color de `marcador_inicio`,
- guarda `sessionStartTime`,
- prepara el primer trial,
- fija `next_transition` usando la duración de la fase actual,
- ejecuta inmediatamente `handle_phase_transition()`,
- y arranca `mainTimer` y `uiTimer`. fileciteturn29file1

Al finalizar, `_finish_session()` marca la sesión como terminada, actualiza `sessionFinalTime`, reemplaza `letter` y `trialID` por `"fin"`, detiene los timers y actualiza tanto `StimuliWindow` como `information_label` para mostrar el mensaje de cierre. Ese cierre visual es más rico que en `SessionManager`, ya que combina el panel de estado con la ventana de estímulos. fileciteturn29file1turn28file4

## Observaciones de implementación

Existen varios detalles que conviene dejar explícitos en la documentación técnica:

- `PreExperimentManager` es conceptualmente muy próximo a `SessionManager`, pero no hereda de él; mantiene una implementación paralela y parcialmente duplicada. fileciteturn29file0turn28file2
- El método `moveTo()` usa `self.now`, atributo que no está definido en la clase, por lo que no es seguro en su estado actual. fileciteturn29file1
- El diccionario de acciones de fase incluye `fadeoff`, pero `fadeoff` no forma parte de `PHASES`; por tanto, esa rama no se ejecuta en el flujo normal. fileciteturn29file1
- La clave `letter` dentro de `laptop_marker_dict` no representa una letra en este contexto, sino una acción. Conviene documentarlo para evitar ambigüedad semántica. fileciteturn29file0turn29file1
- El comentario del método `_send_markers_phase()` todavía menciona envío a tablet, aunque en la implementación sólo se envían marcadores de laptop. fileciteturn29file1

## Resumen breve para documentación

`PreExperimentManager` es el gestor de rondas de preexperimento para paradigmas `basal`, `emg` y `eog`. Su estructura general replica la de `SessionManager` en cuanto a runs, trials, temporización y emisión de marcadores por LSL, pero elimina por completo la comunicación con la tablet. En su lugar, incorpora una `StimuliWindow` y un widget adicional de calibración para resolver localmente la presentación de estímulos e instrucciones. En consecuencia, la clase debe entenderse como una variante de `SessionManager` orientada a rondas de calibración y control fisiológico, con estimulación visual local y marcadores exclusivamente del lado de la laptop. fileciteturn29file0turn29file1turn28file2
