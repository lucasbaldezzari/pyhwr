# SessionInfo

## Descripción general

`SessionInfo` es una clase utilitaria orientada a concentrar la información descriptiva y operativa de una sesión experimental. Su función principal consiste en encapsular identificadores de sesión y sujeto, metadatos básicos de registro y campos relacionados con la convención de nombres tipo BIDS, de modo que otros componentes de la arquitectura dispongan de un objeto compacto y estable para consultar esa información. fileciteturn32file1

En la arquitectura actual, `SessionInfo` no se limita a actuar como un simple contenedor de atributos. También expone una interfaz de acceso tipo diccionario mediante `__getitem__()`, lo que permite que distintas clases consuman la misma información tanto por atributos (`sessioninfo.sub`, `sessioninfo.session_id`) como por indexación (`sessioninfo["bids_file"]`, `sessioninfo["root_folder"]`). Esta decisión resulta especialmente relevante porque `SessionManager` y `PreExperimentManager` utilizan ambos estilos de acceso dentro de su inicialización de interfaz y flujo de ejecución. fileciteturn32file1turn32file5turn32file13

## Rol dentro de la arquitectura

`SessionInfo` funciona como punto de paso entre la configuración de sesión definida por la interfaz de lanzamiento y los gestores que ejecutan la ronda experimental. En particular, `RunConfigurationApp.make_SessionInfo()` construye una instancia de esta clase y la entrega luego a `SessionManager` o `PreExperimentManager`, según el tipo de tarea seleccionada. fileciteturn32file8turn32file11

A partir de esa instancia, los gestores de sesión obtienen información como:

- sujeto (`sub`),
- sesión (`ses`),
- tarea (`task`),
- run (`run`),
- nombre de archivo BIDS (`bids_file`),
- carpeta raíz de salida (`root_folder`),
- identificador de sesión (`session_id`). fileciteturn32file1turn32file5turn32file14

La clase, por tanto, ocupa una posición intermedia entre la capa de configuración y la capa de ejecución.

## Constructor

```python
SessionInfo(
    sub=1,
    ses=1,
    task="ejecutada",
    run=1,
    suffix="eeg",
    session_id=None,
    subject_id=None,
    session_name=None,
    session_date=None,
    bids_file=None,
    root_folder=None,
    comments=None,
)
```

### Parámetros

- `sub`: identificador numérico o simbólico del sujeto.
- `ses`: identificador numérico o simbólico de la sesión.
- `task`: nombre de la tarea o condición experimental.
- `run`: índice del run.
- `suffix`: sufijo del archivo tipo BIDS, por ejemplo `eeg`.
- `session_id`: identificador explícito de sesión. Si no se especifica, toma el valor de `ses`.
- `subject_id`: identificador explícito de sujeto. Si no se especifica, toma el valor de `sub`.
- `session_name`: nombre descriptivo de la sesión. Si no se especifica, toma el valor de `task`.
- `session_date`: fecha de la sesión.
- `bids_file`: nombre de archivo asociado a la sesión.
- `root_folder`: carpeta raíz de almacenamiento.
- `comments`: observaciones adicionales. fileciteturn32file1

## Atributos principales

La clase almacena directamente los siguientes atributos públicos:

- `session_id`
- `subject_id`
- `session_name`
- `date`
- `comments`
- `sub`
- `ses`
- `task`
- `run`
- `suffix`
- `bids_file`
- `root_folder` fileciteturn32file1

### Reglas de fallback

La inicialización aplica tres reglas de fallback que conviene tener presentes:

- `session_id = ses` si no se proporciona `session_id`.
- `subject_id = sub` si no se proporciona `subject_id`.
- `session_name = task` si no se proporciona `session_name`. fileciteturn32file1

Estas reglas hacen que una instancia pueda construirse con muy pocos argumentos y seguir siendo utilizable por el resto del sistema.

## API pública

### `to_dict()`

Convierte el estado del objeto en un diccionario estándar.

```python
info = session_info.to_dict()
```

El diccionario contiene todos los campos relevantes de la sesión, incluidos identificadores, metadatos descriptivos y elementos de nomenclatura BIDS. Este método es también la base del acceso por indexación implementado en `__getitem__()`. fileciteturn32file1

### `__getitem__(key)`

Permite consultar valores mediante sintaxis de diccionario:

```python
session_info["bids_file"]
session_info["root_folder"]
session_info["ses"]
```

Internamente, esta operación delega en `to_dict().get(key)`, por lo que devuelve `None` si la clave no existe. No lanza `KeyError`. Este comportamiento conviene tenerlo presente porque reduce la verbosidad del consumo, pero también puede ocultar errores tipográficos en nombres de clave. fileciteturn32file1

### `__str__()` y `__repr__()`

Ambos métodos generan una representación resumida del objeto:

```python
SesionInfo(id=<session_id>, name=<session_name>, date=<date>)
```

Esta salida resulta útil para logging o inspección rápida durante depuración. fileciteturn32file1

## Ejemplos de uso

### Creación mínima

```python
from pyhwr.utils import SessionInfo

session_info = SessionInfo(
    sub=1,
    ses=1,
    task="ejecutada",
    run=1,
    session_date="2026-04-13",
)
```

En este caso:

- `session_id` tomará el valor `1`,
- `subject_id` tomará el valor `1`,
- `session_name` tomará el valor `"ejecutada"`. fileciteturn32file1

### Creación con nombre de archivo y carpeta raíz

```python
session_info = SessionInfo(
    sub=1,
    ses=1,
    task="imaginada",
    run=1,
    suffix="eeg",
    session_date="2026-04-13",
    bids_file="sub-01_ses-01_task-imaginada_run-01_eeg.bdf",
    root_folder="data/",
    session_id="imaginada",
)
```

Este patrón coincide con el flujo habitual de construcción desde `RunConfigurationApp.make_SessionInfo()`. fileciteturn32file8turn32file9

### Uso dentro de `SessionManager`

```python
self.launcher.update_session_info(
    sub=self.sessioninfo.sub,
    task=self.experimento,
    n_runs=self.n_runs,
    bids_file=self.sessioninfo["bids_file"],
    root_folder=self.sessioninfo["root_folder"],
    ses=self.sessioninfo["ses"],
    run=self.sessioninfo["run"],
)
```

Este ejemplo muestra el uso mixto atributo/diccionario que `SessionInfo` habilita y que constituye uno de sus principales aportes prácticos dentro de la arquitectura. fileciteturn32file5

### Uso dentro de `PreExperimentManager`

```python
self.launcher.update_session_info(
    sub=self.sessioninfo.sub,
    task=self.pre_experiment,
    n_runs=self.n_runs,
    bids_file=self.sessioninfo["bids_file"],
    root_folder=self.sessioninfo["root_folder"],
    ses=self.sessioninfo["ses"],
    run=self.sessioninfo["run"],
)
```

El mismo patrón se reutiliza en el gestor de preexperimentos. fileciteturn32file14

## Consideraciones de diseño

### 1. Interfaz híbrida

La combinación de atributos públicos con acceso tipo diccionario simplifica el consumo desde la UI y desde los gestores, pero también introduce cierta ambigüedad semántica. `SessionInfo` no es estrictamente un dataclass ni un diccionario; es un objeto mutable con una capa de compatibilidad adicional. fileciteturn32file1turn32file5turn32file14

### 2. `session_id` no siempre coincide con `ses`

Aunque el constructor utiliza `ses` como fallback para `session_id`, `RunConfigurationApp.make_SessionInfo()` sobrescribe ese campo con el valor de `task`. En consecuencia, el campo `session_id` puede terminar representando la tarea activa más que un identificador formal de sesión. Este detalle debe tenerse en cuenta al interpretar mensajes o nombres de carpeta derivados de ese valor. fileciteturn32file1turn32file8turn32file9

### 3. El acceso por clave no valida errores

Como `__getitem__()` usa `dict.get`, una clave mal escrita devuelve `None` en lugar de fallar inmediatamente. Esto facilita cierto consumo flexible, pero puede volver más difícil detectar errores de integración. fileciteturn32file1

### 4. La clase no genera automáticamente nombres BIDS

Aunque almacena `sub`, `ses`, `task`, `run` y `suffix`, la clase no construye por sí sola el nombre `bids_file`. Ese valor se entrega desde afuera, por ejemplo desde `RunConfigurationApp`. Por ello, `SessionInfo` debe entenderse como contenedor de metadatos y no como generador completo de nomenclatura BIDS. fileciteturn32file1turn32file8

## Limitaciones actuales

- No existe validación de tipos ni de formato para `sub`, `ses`, `run` o `session_date`.
- No se verifica consistencia entre `task`, `session_name` y `session_id`.
- No se construye automáticamente el nombre BIDS a partir de los campos base.
- El acceso por clave retorna `None` silenciosamente si la clave no existe. fileciteturn32file1turn32file8

## Recomendaciones de mejora

1. Incorporar validación explícita de campos.
2. Considerar una implementación con `dataclass` para hacer más claro el contrato del objeto.
3. Diferenciar formalmente entre identificador de sesión, nombre de tarea y nombre descriptivo.
4. Evaluar si `__getitem__()` debe mantener el retorno silencioso de `None` o lanzar una excepción ante claves inválidas.
5. Añadir un método opcional para construir `bids_file` automáticamente a partir de `sub`, `ses`, `task`, `run` y `suffix`.

## Relación con otros módulos

`SessionInfo` se integra directamente con:

- `RunConfigurationApp`, que construye la instancia; fileciteturn32file8turn32file11
- `SessionManager`, que la consume para configurar la ronda y poblar la UI; fileciteturn32file5turn32file6
- `PreExperimentManager`, que reutiliza la misma interfaz para la fase de calibración o preexperimento; fileciteturn32file13turn32file14
- `LauncherApp`, que muestra parte de sus campos en pantalla a través de `update_session_info(...)`. fileciteturn32file17turn32file5turn32file14

## Resumen

`SessionInfo` constituye la unidad básica de metadatos de sesión dentro de la arquitectura experimental. Su diseño sencillo y su interfaz híbrida permiten transportar información entre la configuración inicial, la UI de ejecución y los gestores de sesión con muy poco acoplamiento adicional. Al mismo tiempo, esa simplicidad deja abiertas varias mejoras posibles en validación, consistencia semántica y construcción automática de nombres de archivo.
