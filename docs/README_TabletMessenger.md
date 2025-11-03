# 📱 TabletMessenger — Módulo de Comunicación ADB con Tablets Android

Este módulo permite enviar y recibir **mensajes JSON** entre una PC/Laptop y una **tablet Android** utilizando el comando `adb`.  
Su objetivo es la sincronización de eventos experimentales, transferencia de información de la sesión y coordinar flujos de datos entre sistemas en el marco del proyecto de doctorado del *[MSc Bioingeniero BALDEZZARI Lucas](https://www.linkedin.com/in/lucasbaldezzari/)*.

---

## Contenido del Módulo

- [TabletMessenger](#tabletmesenger)
  - [Inicialización](#inicialización-de-tabletmessenger)
  - [Métodos principales](#métodos-principales)
  - [Ejemplo de uso](#ejemplo-de-uso)
- [Dependencias y créditos](#dependencias-y-créditos)

---

## `TabletMessenger`

Clase para gestionar la comunicación con tablets Android mediante **Android Debug Bridge (ADB)**.  
Permite enviar mensajes estructurados, leer archivos JSON generados por la tablet y descargar datos de ensayos.

---

### Inicialización de `TabletMessenger`

```python
TabletMessenger(
    max_messages: int = 200,
    serial: str = "R52W70ATD1W",
    log_level: int = logging.INFO
)
```

**Parámetros:**

| Parámetro | Tipo | Descripción |
|------------|------|-------------|
| `max_messages` | `int` | Tamaño máximo del historial de mensajes (cola interna `deque`). |
| `serial` | `str` | Número de serie del dispositivo Android (visible en `adb devices`). |
| `log_level` | `int` | Nivel de registro del logger (`logging.INFO`, `logging.DEBUG`, etc.). |

---

### Atributos automáticos

| Atributo | Descripción |
|-----------|-------------|
| `history` | Cola circular (`deque`) con el historial de mensajes enviados o recibidos. |
| `serial` | Número de serie del dispositivo conectado. |
| `logger` | Instancia de `logging.Logger` configurada internamente. |
| `max_messages` | Límite de tamaño del historial. |

---

## Métodos principales

### `.make_message(...)`
Crea un mensaje JSON estructurado con los campos necesarios para identificar sesión, ensayo y fase.

```python
make_message(
    sesionStatus: str,
    sesion_id: int,
    run_id: int,
    subject_id: str,
    trialID: int,
    trialPhase: str,
    letter: str,
    duration: float,
    **extra
) -> dict
```

**Retorna:**  
Un diccionario con la estructura:
```json
{
  "sesionStatus": "on",
  "session_id": 1,
  "run_id": 1,
  "subject_id": "subject01",
  "trialInfo": {
    "trialID": 1,
    "trialPhase": "start",
    "letter": "A",
    "duration": 4.0
  }
}
```

---

### `.send_message(message, tabletID)`
Envía un mensaje JSON a la tablet Android mediante **broadcast de ADB**.

**Parámetros:**

| Parámetro | Tipo | Descripción |
|------------|------|-------------|
| `message` | `dict` | Estructura del mensaje (se serializa a JSON). |
| `tabletID` | `str` | Acción de broadcast registrada en la tablet (p. ej. `"com.handwriting.ACTION_MSG"`). |

**Ejemplo:**
```python
tablet = TabletMessenger(serial="R52W70ATD1W")
msg = tablet.make_message("on", 1, 1, "subject01", 1, "start", "A", 4.0)
tablet.send_message(msg, "com.handwriting.ACTION_MSG")
```

---

### `.read_trial_json(subject, session, run, trial_id)`
Lee el archivo `trial_*.json` almacenado en la tablet (carpeta `/Documents/...`) y lo devuelve como `dict`.

**Retorna:**  
`dict` con los datos del ensayo o `None` si no se encuentra el archivo.

---

### `.pull_trial_json(subject, session, run, trial_id, local_dir="./")`
Descarga un archivo `trial_*.json` desde la tablet al computador mediante `adb pull`.

**Parámetros:**

| Parámetro | Tipo | Descripción |
|------------|------|-------------|
| `subject` | `str` | Nombre del sujeto o participante. |
| `session` | `str` | Identificador de sesión. |
| `run` | `str` | Identificador de ejecución. |
| `trial_id` | `int` | Número del ensayo a descargar. |
| `local_dir` | `str | Path` | Carpeta local donde guardar el archivo. |

**Retorna:**  
Ruta local (`Path`) del archivo descargado.

---

### `.list_trials(subject, session, run)`
Lista todos los archivos `trial_*.json` disponibles en la ruta remota del dispositivo.

**Ejemplo:**
```python
ids = tablet.list_trials("subject01", "session1", "runA")
print(ids)
# ➜ [1, 2, 3, 4]
```

---

### `.enable_logging(enabled=True)`
Activa o desactiva la salida por consola del logger interno.

---

## Ejemplo de uso

```python
from TabletMessenger import TabletMessenger
import logging

logging.basicConfig(level=logging.INFO)
tablet = TabletMessenger(serial="R52W70ATD1W")

# Crear mensaje
msg = tablet.make_message(
    sesionStatus="on",
    sesion_id=1,
    run_id=1,
    subject_id="subject01",
    trialID=1,
    trialPhase="start",
    letter="B",
    duration=4.0
)

# Enviar mensaje
tablet.send_message(msg, "com.handwriting.ACTION_MSG")

# Leer datos de un trial
trial_data = tablet.read_trial_json("subject01", "1", "runA", 1)
print(trial_data)

# Descargar el archivo localmente
tablet.pull_trial_json("subject01", "1", "runA", 1, local_dir="./downloads")
```

---

## Dependencias y créditos

**Dependencias:**
```bash
adb (Android SDK Platform Tools)
```

**Módulos estándar utilizados:**
- `subprocess`, `json`, `pathlib`, `logging`, `re`, `time`, `collections`

**Desarrollado por:**  
Equipo de Investigación — *Interfaces Cerebro-Computadora (BCI)*  
Laboratorio de Neurotecnología Aplicada

---

📅 **Última actualización:** 2025-11-03  
🧩 **Versión compatible:** Python 3.9+
