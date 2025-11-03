# 🧠 SessionManager — Módulo de Control de Sesiones Experimentales

El módulo **SessionManager** gestiona el flujo completo de una **sesión experimental** basada en fases temporizadas, comunicación con **tablet Android** y envío de **marcadores vía LSL**.  

Su objetivo principal es el de sincronizar eventos entre PC/Laptop, tablet android y el g.HIAMP de gtec en el marco del proyecto de doctorado del *[MSc Bioingeniero BALDEZZARI Lucas](https://www.linkedin.com/in/lucasbaldezzari/)*.

---

## Contenido del Módulo

- [SessionManager](#sessionmanager)
  - [Inicialización](#inicialización-de-sessionmanager)
  - [Atributos principales](#atributos-principales)
  - [Fases del ciclo experimental](#fases-del-ciclo-experimental)
  - [Métodos principales](#métodos-principales)
  - [Interfaz gráfica](#interfaz-gráfica)
  - [Ejemplo de uso](#ejemplo-de-uso)
- [Dependencias y créditos](#dependencias-y-créditos)

---

## `SessionManager`

Clase principal encargada de controlar el **ciclo completo de una sesión experimental**, incluyendo:
- Control de **fases** temporizadas (inicio, cue, descanso, etc.)
- Comunicación con **Tablet Android** mediante `TabletMessenger`
- Envío de **marcadores LSL** mediante `MarkerManager`
- Interfaz visual basada en **PyQt5**

---

### Inicialización de `SessionManager`

```python
SessionManager(
    sessioninfo: SessionInfo,
    mainTimerDuration: int = 5,
    tabid: str = "com.handwriting.ACTION_MSG",
    runs_per_session: int = 1,
    letters: list[str] = None,
    randomize_per_run: bool = True,
    seed: int = None
)
```

**Parámetros:**

| Parámetro | Tipo | Descripción |
|------------|------|-------------|
| `sessioninfo` | `SessionInfo` | Información de la sesión (ID, sujeto, nombre, fecha). |
| `mainTimerDuration` | `int` | Intervalo base del `QTimer` principal (ms). |
| `tabid` | `str` | Acción de broadcast usada por la tablet. |
| `runs_per_session` | `int` | Cantidad de ejecuciones (runs) dentro de la sesión. |
| `letters` | `list[str]` | Letras o estímulos a presentar por ensayo (trial). |
| `randomize_per_run` | `bool` | Si es `True`, mezcla las letras en cada run. |
| `seed` | `int` | Semilla aleatoria para reproducibilidad. |

---

### Atributos principales

| Atributo | Descripción |
|-----------|-------------|
| `phases` | Diccionario con la secuencia de fases y sus duraciones. |
| `tabmanager` | Instancia de [`TabletMessenger`](README_TabletMessenger.md). |
| `tablet_markers` / `laptop_markers` | Instancias de [`MarkerManager`](README_MarkerManager.md). |
| `mainTimer` | `QTimer` que controla la actualización de fases. |
| `run_orders` | Lista de letras ordenadas o aleatorizadas por run. |
| `current_run`, `current_trial`, `current_letter` | Estado actual de ejecución. |
| `session_finished` | Indica si la sesión ha concluido. |
| `laptop_markers_dict` | Diccionario con tiempos y metadatos de cada fase/trial. |

---

## Fases del ciclo experimental

Cada sesión sigue una secuencia definida de **fases temporizadas**, almacenadas en el atributo `PHASES`:

| Fase | Duración (s) | Siguiente | Descripción |
|------|---------------|-----------|--------------|
| `first_jump` | 0.01 | `start` | Salto inicial técnico. |
| `start` | 3.0 | `fadein` | Muestra datos del ensayo actual. |
| `fadein` | 1.0 | `cue` | Transición de preparación visual. |
| `cue` | 5.0 | `fadeoff` | Presentación principal del estímulo. |
| `fadeoff` | 1.0 | `rest` | Cierre del ensayo. |
| `rest` | 3.0 | `trialInfo` | Período de descanso. |
| `trialInfo` | 0.3 | `sendMarkers` | Preparación de marcadores. |
| `sendMarkers` | 0.1 | `start` | Envío de datos y paso al siguiente ensayo. |

---

## Métodos principales

### `.startSession()`
Inicia la sesión, prepara el primer trial, envía el mensaje `"on"` a la tablet y arranca el `QTimer`.

### `.handle_phase_transition()`
Gestiona el comportamiento en cada fase mediante un **diccionario de acciones**.  
Llama internamente a:
- `_on_phase()` → aplica color, guarda tiempo y actualiza GUI.  
- `_send_markers_phase()` → envía marcadores al final de cada ensayo.

### `._on_phase(time_key, color, extra_action=None, log=None)`
Registra el tiempo de la fase y cambia el color del marcador correspondiente.

### `._send_markers_phase()`
Lee los datos del `trial_*.json` desde la tablet, los transmite por LSL, y prepara el siguiente ensayo.

### `.moveTo(phase_name)`
Permite mover manualmente el estado de la sesión a una fase específica.

### `.stop()`
Detiene la sesión y cierra la interfaz.

### `._finish_session()`
Finaliza la sesión, guarda los tiempos finales y envía un mensaje `"final"` a la tablet.  
También reenvía el JSON final de la tablet a través de LSL.

### `._read_final_with_retry()`
Intenta recuperar el último JSON de la tablet con reintentos exponenciales.

---

## Interfaz gráfica

### Descripción

Basada en **PyQt5**, la ventana muestra tres áreas principales:
- 🟩 **Inicio de Sesión**: estado general del experimento.
- ⚫ **Cue**: estímulo principal (controlado por cambio de color).
- ⚪ **Calibración**: referencia para sensores o cámaras externas.

### Controles del teclado

| Tecla | Acción |
|--------|---------|
| **Enter / Return** | Inicia la sesión. |
| **Escape** | Detiene la sesión y cierra la aplicación. |

---

## Ejemplo de uso

```python
import time, sys, logging
from pyhwr.utils import SessionInfo
from pyhwr.managers import SessionManager
from PyQt5.QtWidgets import QApplication

logging.basicConfig(level=logging.INFO)

app = QApplication(sys.argv)

session_info = SessionInfo(
    session_id="1",
    subject_id="subject01",
    session_name="writing_task",
    session_date=time.strftime("%Y-%m-%d"),
)

manager = SessionManager(
    session_info,
    runs_per_session=1,
    letters=["A", "B", "C", "D"],
    randomize_per_run=True,
    seed=42
)

exit_code = app.exec_()
sys.exit(exit_code)
```

**Salida esperada:**
```
[MarkerManager] INFO: Outlet LSL creado: Laptop_Markers (Markers) [Laptop]
[MarkerManager] INFO: Outlet LSL creado: Tablet_Markers (Markers) [Tablet]
Broadcasting: Intent { act=com.handwriting.ACTION_MSG flg=0x400000 (has extras) }
Broadcast completed: result=0
[INFO] Sesión iniciada
[INFO] Fase actual: start
...
```

---

## Dependencias y créditos

**Dependencias:**
```bash
pip install pyqt5 pylsl numpy
```

**Módulos relacionados:**
- [`MarkerManager`](README_MarkerManager.md)
- [`TabletMessenger`](README_TabletMessenger.md)
- [`SessionInfo`](pyhwr/utils.py)

**Desarrollado por:**  
Equipo de Investigación — *Interfaces Cerebro-Computadora (BCI)*  
Laboratorio de Neurotecnología Aplicada

---

📅 **Última actualización:** 2025-11-03  
🧩 **Versión compatible:** Python 3.9+
