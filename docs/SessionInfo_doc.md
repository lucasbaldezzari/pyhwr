# Documentación API — `SessionInfo`

## Resumen

`SessionInfo` es una clase contenedora liviana para centralizar metadatos de una sesión experimental. Su objetivo principal es transportar, en un único objeto, la información mínima necesaria para:

- identificar sesión y sujeto,
- conservar campos BIDS (`sub`, `ses`, `task`, `run`, `suffix`),
- exponer rutas/nombres auxiliares como `bids_file` y `root_folder`,
- y servir como interfaz mixta **tipo objeto** y **tipo diccionario** frente a otros componentes del sistema.

En la arquitectura actual, `SessionInfo` no implementa validación, persistencia ni generación automática del nombre BIDS. Su función es puramente estructural.

---

## Definición

```python
class SessionInfo():
    def __init__(self, sub=1, ses=1, task="ejecutada", run=1, suffix="eeg",
                 session_id=None, subject_id=None, session_name=None,
                 session_date=None, bids_file=None, root_folder=None, comments=None):
```

---

## Responsabilidad dentro de la arquitectura

`SessionInfo` ocupa una posición de frontera entre la configuración del experimento y los módulos que ejecutan o muestran la sesión.

### En `SessionManager`

`SessionManager` consume `SessionInfo` de dos maneras distintas:

1. **como objeto con atributos**, por ejemplo:
   - `sessioninfo.session_id`
   - `sessioninfo.subject_id`
   - `sessioninfo.sub`

2. **como objeto indexable**, por ejemplo:
   - `sessioninfo["bids_file"]`
   - `sessioninfo["root_folder"]`
   - `sessioninfo["ses"]`
   - `sessioninfo["run"]`

Esto implica que `SessionInfo` fue diseñado explícitamente para soportar ambos estilos de acceso. Si esa compatibilidad se rompe, `SessionManager` deja de funcionar correctamente.

---

## Constructor

### Firma

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

#### `sub`
Identificador BIDS del sujeto.

- Tipo esperado: `str | int`
- Valor por defecto: `1`
- Se almacena en `self.sub`
- Si `subject_id` no se especifica, también se reutiliza como `self.subject_id`

#### `ses`
Identificador BIDS de sesión.

- Tipo esperado: `str | int`
- Valor por defecto: `1`
- Se almacena en `self.ses`
- Si `session_id` no se especifica, también se reutiliza como `self.session_id`

#### `task`
Nombre BIDS de tarea o condición experimental.

- Tipo esperado: `str`
- Valor por defecto: `"ejecutada"`
- Se almacena en `self.task`
- Si `session_name` no se especifica, también se reutiliza como `self.session_name`

#### `run`
Identificador BIDS de run.

- Tipo esperado: `str | int`
- Valor por defecto: `1`
- Se almacena en `self.run`

#### `suffix`
Sufijo BIDS del archivo de salida.

- Tipo esperado: `str`
- Valor por defecto: `"eeg"`
- Se almacena en `self.suffix`

#### `session_id`
Identificador lógico de sesión utilizado por otros módulos.

- Tipo esperado: `str | int | None`
- Valor por defecto: `None`
- Si no se especifica, toma el valor de `ses`

#### `subject_id`
Identificador lógico del sujeto utilizado por otros módulos.

- Tipo esperado: `str | int | None`
- Valor por defecto: `None`
- Si no se especifica, toma el valor de `sub`

#### `session_name`
Nombre descriptivo de la sesión.

- Tipo esperado: `str | None`
- Valor por defecto: `None`
- Si no se especifica, toma el valor de `task`

#### `session_date`
Fecha de la sesión.

- Tipo esperado: `str | None`
- Valor por defecto: `None`
- Se almacena en el atributo `self.date`

#### `bids_file`
Plantilla o nombre base del archivo BIDS.

- Tipo esperado: `str | None`
- Valor por defecto: `None`
- Se almacena en `self.bids_file`

#### `root_folder`
Ruta raíz del proyecto o del dataset.

- Tipo esperado: `str | None`
- Valor por defecto: `None`
- Se almacena en `self.root_folder`

#### `comments`
Comentarios libres asociados a la sesión.

- Tipo esperado: `str | None`
- Valor por defecto: `None`
- Se almacena en `self.comments`

---

## Reglas internas de asignación

El constructor aplica tres reglas de fallback importantes:

```python
self.session_id   = ses  if session_id   is None else session_id
self.subject_id   = sub  if subject_id   is None else subject_id
self.session_name = task if session_name is None else session_name
```

Esto significa que la clase distingue entre:

- **campos BIDS**: `sub`, `ses`, `task`, `run`, `suffix`
- **campos lógicos o de presentación**: `session_id`, `subject_id`, `session_name`

pero, si no se le indica lo contrario, los empareja automáticamente.

### Consecuencia práctica

Puedes usarla de manera mínima:

```python
info = SessionInfo(sub="01", ses="01", task="imaginada", run="01")
```

Y obtendrás automáticamente:

- `info.subject_id == "01"`
- `info.session_id == "01"`
- `info.session_name == "imaginada"`

---

## Atributos públicos

Una instancia de `SessionInfo` expone, al menos, estos atributos:

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
- `root_folder`

No existen propiedades calculadas ni validaciones de tipo/rango.

---

## Métodos

### `__str__()`

```python
def __str__(self):
    return f"SesionInfo(id={self.session_id}, name={self.session_name}, date={self.date})"
```

Retorna una representación breve pensada para inspección humana.

#### Ejemplo

```python
info = SessionInfo(session_id="ses-01", session_name="baseline", session_date="2026-04-05")
print(info)
```

Salida esperada:

```python
SesionInfo(id=ses-01, name=baseline, date=2026-04-05)
```

---

### `__repr__()`

```python
def __repr__(self):
    return self.__str__()
```

Devuelve exactamente la misma representación que `__str__()`.

---

### `to_dict()`

```python
def to_dict(self):
    return {
        "session_id": self.session_id,
        "session_name": self.session_name,
        "date": self.date,
        "subject_id": self.subject_id,
        "comments": self.comments,
        "sub": self.sub,
        "ses": self.ses,
        "task": self.task,
        "run": self.run,
        "suffix": self.suffix,
        "bids_file": self.bids_file,
        "root_folder": self.root_folder,
    }
```

Convierte la instancia a un diccionario plano.

#### Observaciones

- La clave temporal es `"date"`, no `"session_date"`.
- El diccionario se reconstruye en cada llamada.
- No hay copia profunda, aunque en esta clase eso no suele ser problemático porque sólo contiene escalares o strings.

#### Uso típico

```python
payload = info.to_dict()
```

Útil para logging, serialización simple o debugging.

---

### `__getitem__(key)`

```python
def __getitem__(self, key):
    return self.to_dict().get(key)
```

Permite acceder a la instancia como si fuera un diccionario.

#### Ejemplos

```python
info["sub"]
info["bids_file"]
info["root_folder"]
```

#### Comportamiento importante

A diferencia de un `dict` estándar, este método **no lanza `KeyError`** cuando la clave no existe. En su lugar devuelve `None`.

```python
info["clave_inexistente"]  # -> None
```

Esto hace a la API más tolerante, pero también puede ocultar errores de tipeo.

---

## Ejemplos de uso

### 1. Uso mínimo

```python
info = SessionInfo(
    sub="01",
    ses="01",
    task="ejecutada",
    run="01"
)
```

Resultado conceptual:

```python
info.subject_id   == "01"
info.session_id   == "01"
info.session_name == "ejecutada"
```

---

### 2. Uso explícito con IDs lógicos independientes de BIDS

```python
info = SessionInfo(
    sub="01",
    ses="01",
    task="imaginada",
    run="02",
    suffix="eeg",
    session_id="session_alpha",
    subject_id="S001",
    session_name="Imagined handwriting",
    session_date="2026-04-05",
    bids_file="sub-01_ses-01_task-imaginada_run-02_eeg",
    root_folder=r"D:\repos\pyhwr",
    comments="Bloque de entrenamiento"
)
```

Este patrón es útil cuando:

- BIDS exige una codificación compacta (`sub`, `ses`, `task`, `run`),
- pero la lógica del experimento o la interfaz necesita nombres más expresivos (`subject_id`, `session_name`, `session_id`).

---

### 3. Uso real con `SessionManager`

```python
session_info = SessionInfo(
    session_id="1",
    subject_id="test_v0.0.5",
    session_name="test_v0.0.5",
    session_date=time.strftime("%Y-%m-%d"),
)

manager = SessionManager(session_info, n_runs=1, letters=["a"])
```

En este escenario, `SessionManager` utiliza `SessionInfo` para:

- poblar mensajes enviados a la tablet,
- actualizar la UI del launcher,
- identificar sujeto/sesión/run,
- y resolver campos como `bids_file`, `root_folder`, `ses` y `run` por indexación.

---

## Interacción con otros componentes

### `SessionManager`

`SessionManager` depende de que `SessionInfo` exponga simultáneamente:

- atributos como `session_id`, `subject_id`, `sub`,
- y acceso indexado mediante `__getitem__()`.

Eso ocurre, por ejemplo, cuando inicializa la ventana de launcher y le pasa:

- `sub=self.sessioninfo.sub`
- `task=self.experimento`
- `n_runs=self.n_runs`
- `bids_file=self.sessioninfo["bids_file"]`
- `root_folder=self.sessioninfo["root_folder"]`
- `ses=self.sessioninfo["ses"]`
- `run=self.sessioninfo["run"]`

---

### `LauncherApp`

`LauncherApp.update_session_info()` toma esos datos y actualiza labels de interfaz. En particular, concatena extensiones a `bids_file` para mostrar nombres `.xdf` y `.hdf5`.

Esto implica que, si `bids_file` es `None`, en la UI terminarán apareciendo strings como:

- `None.xdf`
- `None.hdf5`

No rompe necesariamente el flujo, pero sí degrada la presentación.

---

## Comportamiento esperado de la clase

### Lo que sí hace bien

- Centraliza metadatos dispersos en un único objeto.
- Es fácil de instanciar.
- Soporta acceso por atributo y por índice.
- Encaja bien con un pipeline experimental pequeño o mediano.

### Lo que no hace

- No valida tipos.
- No valida formato BIDS.
- No construye automáticamente `bids_file`.
- No normaliza `sub`, `ses` o `run` a strings con ceros a la izquierda.
- No implementa persistencia a JSON/YAML.
- No protege contra claves mal escritas al usar `__getitem__()`.

---

## Riesgos y decisiones de diseño que conviene conocer

### 1. `session_date` se almacena como `date`

El parámetro del constructor se llama `session_date`, pero internamente el atributo pasa a llamarse `date`.

Eso es válido, pero puede confundir si se espera simetría entre nombre de parámetro, atributo y clave serializada.

---

### 2. `__getitem__()` devuelve `None` ante claves inválidas

Esto hace que la clase sea tolerante, pero también vuelve silenciosos ciertos bugs.

Ejemplo:

```python
info["bidsfile"]   # typo
```

no lanza excepción: simplemente devuelve `None`.

---

### 3. No hay generación automática del nombre BIDS

Aunque la docstring menciona campos destinados a generar un nombre BIDS, la clase no implementa actualmente esa lógica.

Por tanto, `bids_file` debe venir calculado desde afuera si se necesita un nombre final consistente.

---

### 4. Tipado flexible, pero no controlado

Puedes mezclar `int` y `str` en campos como `sub`, `ses` y `run`. Eso facilita el uso, pero puede introducir inconsistencias si otra parte del sistema espera siempre strings como `"01"`.

---

## Recomendaciones de mejora

### Mejora 1 — usar `dataclass`

La clase sería una candidata natural a `@dataclass`, ya que es esencialmente un contenedor de datos.

### Mejora 2 — agregar validación

Sería recomendable validar:

- que `sub`, `ses`, `run` no sean vacíos,
- que `suffix` pertenezca a un conjunto conocido,
- que `session_date` tenga formato consistente,
- y que `bids_file` no sea `None` cuando la UI lo requiera.

### Mejora 3 — separar campos BIDS de campos lógicos

Podría convenir distinguir más explícitamente:

- identidad BIDS (`sub`, `ses`, `task`, `run`, `suffix`)
- identidad experimental/lógica (`session_id`, `subject_id`, `session_name`)

Hoy ambas capas coexisten, pero sin un contrato fuerte.

### Mejora 4 — soportar generación automática de nombre BIDS

Por ejemplo, con un método tipo:

```python
def build_bids_filename(self) -> str:
    ...
```

---

## Ejemplo de uso recomendado

```python
info = SessionInfo(
    sub="01",
    ses="01",
    task="imaginada",
    run="01",
    suffix="eeg",
    session_id="ses-01",
    subject_id="sub-01",
    session_name="Imagined handwriting block",
    session_date="2026-04-05",
    bids_file="sub-01_ses-01_task-imaginada_run-01_eeg",
    root_folder=r"D:\repos\pyhwr",
    comments="Registro con tablet + LSL + g.HIAMP"
)
```

Este patrón evita depender demasiado de los fallbacks implícitos y deja la semántica de cada campo mucho más clara.

---

## Resumen final

`SessionInfo` es una clase pequeña pero estructuralmente importante. No implementa lógica sofisticada, pero define el contrato básico de metadatos que luego consumen `SessionManager` y la UI del launcher. Su mayor fortaleza es la simplicidad; su principal debilidad es la ausencia de validación y el carácter implícito de varios comportamientos, especialmente los fallbacks y el acceso por índice que devuelve `None` silenciosamente.
