# ⚙️ MarkerManager — Módulo de Envío de Marcadores vía LSL

Este módulo proporciona una interfaz sencilla para crear y enviar **marcadores de eventos** mediante **Lab Streaming Layer (LSL)** en el marco del proyecto de doctorado del *[MSc Bioingeniero BALDEZZARI Lucas](https://www.linkedin.com/in/lucasbaldezzari/)*.

---

## Contenido del Módulo

- [MarkerManager](#markermanager)
  - [Inicialización](#inicialización-de-markermanager)
  - [Métodos principales](#métodos-principales)
  - [Ejemplo de uso](#ejemplo-de-uso)
- [Ejemplo con otros módulos](#ejemplo-con-otros-módulos)
- [Dependencias y créditos](#dependencias-y-créditos)

---

## `MarkerManager`

Clase para gestionar la creación y transmisión de **marcadores** (eventos) por un flujo de **LSL (Lab Streaming Layer)**.

### Inicialización de `MarkerManager`

```python
MarkerManager(
    stream_name: str = "Generic_Markers",
    stream_type: str = "Events",
    source_id: Optional[str] = None,
    channel_count: int = 1,
    channel_format: str = "string",
    nominal_srate: float = 0.0,
    logger: Optional[logging.Logger] = None
)
```

**Parámetros:**

| Parámetro | Tipo | Descripción |
|------------|------|-------------|
| `stream_name` | `str` | Nombre del flujo de salida (por defecto `"Generic_Markers"`). |
| `stream_type` | `str` | Tipo de evento o categoría del flujo (`"Events"`, `"Triggers"`, etc.). |
| `source_id` | `str` | Identificador único del emisor. Si no se especifica, se genera automáticamente. |
| `channel_count` | `int` | Número de canales (1 por marcador textual). |
| `channel_format` | `str` | Formato de los datos enviados (`"string"` recomendado). |
| `nominal_srate` | `float` | Frecuencia nominal de muestreo (0 para eventos asincrónicos). |
| `logger` | `logging.Logger` | Logger opcional para personalizar la salida de mensajes. |

---

### Atributos automáticos

| Atributo | Descripción |
|-----------|-------------|
| `outlet_info` | Objeto `StreamInfo` con los metadatos del flujo LSL. |
| `outlet` | Instancia de `StreamOutlet` para transmitir los marcadores. |
| `logger` | Instancia de `logging.Logger` configurada automáticamente. |
| `stream_name`, `stream_type`, `source_id` | Identificación del flujo creado. |

---

### Métodos principales

#### `.send_marker(message)`
Envía un marcador (evento) al flujo LSL.

**Parámetros:**

| Parámetro | Tipo | Descripción |
|------------|------|-------------|
| `message` | `str | dict | Any` | Mensaje o evento a enviar. Si es un diccionario, se convierte automáticamente a JSON. |

**Comportamiento:**
- Si el mensaje es `dict`, se serializa como JSON.
- Si el mensaje es vacío o `None`, se ignora y muestra una advertencia.
- Si ocurre un error de transmisión, se registra mediante `logging`.

**Ejemplo:**
```python
marker = MarkerManager(stream_name="Exp_Markers", stream_type="Cognitive_Events")
marker.send_marker({"event": "stimulus_onset", "trial": 3, "time": 12.45})
```

---

### `__str__()` / `__repr__()`
Devuelve una representación legible del objeto con el nombre, tipo y `source_id` del flujo.

```python
print(marker)
# ➜ MarkerManager(Generic_Markers, Events, ID=Generic_Markers_8472)
```

---

## Ejemplo de uso

```python
from MarkerManager import MarkerManager
import logging

logging.basicConfig(level=logging.INFO)

marker_gen = MarkerManager(
    stream_name="Generic_Markers",
    stream_type="Test_Events",
    source_id="Test_Source"
)

marker_gen.send_marker("Inicio del experimento")
marker_gen.send_marker({"trial": 1, "event": "stimulus", "time": 2.34})
```

**Salida esperada:**
```
[MarkerManager] INFO: Outlet LSL creado: Generic_Markers (Test_Events) [Test_Source]
[MarkerManager] DEBUG: Marcador enviado: {"trial": 1, "event": "stimulus", "time": 2.34}
```

---

## Ejemplo con otros módulos

Ejemplo de integración con `TabletMessenger` (u otro generador de eventos):

```python
from pyhwr.managers import TabletMessenger
from MarkerManager import MarkerManager

tablet = TabletMessenger(serial="R52W70ATD1W")
marker_gen = MarkerManager(stream_name="Tablet_Events")

trial_data, _ = tablet.read_trial_json("subject01", 1, 2, 1)
marker_gen.send_marker(trial_data)
```

---

## Dependencias y créditos

**Dependencias:**
```bash
pip install pylsl
```

**Módulos estándar utilizados:**
- `json`, `random`, `logging`
- `typing` (`Optional`, `Union`, `Any`)

**Desarrollado por:**  
Equipo de Investigación — *Interfaces Cerebro-Computadora (BCI)*  
Laboratorio de Neurotecnología Aplicada

---

📅 **Última actualización:** 2025-11-03  
🧩 **Versión compatible:** Python 3.9+
