# `RunConfigurationApp`

## Descripción general

`RunConfigurationApp` es la ventana de parametrización operativa de una ronda experimental. Su función consiste en tomar la metadata base entregada por `InitAPP`, completar los parámetros de ejecución y lanzar el manager correspondiente: `SessionManager` para rondas principales de escritura o `PreExperimentManager` para rondas de preexperimento.

Dentro de la arquitectura, esta clase actúa como **hub de configuración de runtime**. Es el punto donde el estado de la interfaz deja de ser solamente metadata descriptiva y se transforma en argumentos concretos de construcción para los managers de ejecución.

---

## Rol dentro de la arquitectura

`RunConfigurationApp` ocupa la segunda etapa del pipeline de interfaz:

```text
InitAPP -> RunConfigurationApp -> SessionManager / PreExperimentManager -> LauncherApp
```

Recibe un diccionario `config` generado por `InitAPP`, expone valores por defecto según el tipo de ronda y, una vez confirmados los parámetros, crea el `SessionInfo` y el manager que tomará el control de la sesión.

---

## Responsabilidades principales

La clase concentra las siguientes responsabilidades:

1. **Mostrar el tipo de ronda activo**
   - ya sea tomado del `config` inicial o forzado desde la propia UI.

2. **Cargar parámetros por defecto por paradigma**
   - número de runs,
   - duración base de `cue`,
   - rango aleatorio de `cue`,
   - duración base de `rest`,
   - rango aleatorio de `rest`,
   - aleatorización por run.

3. **Habilitar o deshabilitar campos según el estado de checkboxes**
   - fuerza de tipo de ronda,
   - aleatorización,
   - uso de semilla,
   - edición del tablet ID.

4. **Construir `SessionInfo`**
   - a partir de `config` y del contexto de ronda seleccionado.

5. **Instanciar el manager adecuado**
   - `SessionManager` para `entrenamiento`, `ejecutada` e `imaginada`;
   - `PreExperimentManager` para `basal`, `emg` y `eog`.

---

## Dependencias principales

### `SessionInfo`

La clase construye un objeto `SessionInfo` mediante `make_SessionInfo()` para encapsular la metadata de la sesión.

### `SessionManager`

Se utiliza para lanzar rondas principales de escritura y entrenamiento.

### `PreExperimentManager`

Se utiliza para lanzar rondas de preexperimento, como `basal`, `emg` y `eog`.

### `InitAPP`

La navegación hacia atrás se resuelve reabriendo `InitAPP` desde `volver_inicio()`.

---

## Firma del constructor

```python
RunConfigurationApp(config: dict = None)
```

### Parámetro de entrada

- `config`: diccionario con metadata base de la ronda, normalmente generado por `InitAPP`.

Si `config` es `None` o no contiene la clave `task`, la ventana asume `ejecutada` como valor inicial de referencia.

---

## Configuración por defecto por paradigma

La clase mantiene un diccionario `experimento_defaults` que define perfiles de ejecución para distintos tipos de ronda.

### Rondas de preexperimento

- `basal`
- `emg`
- `eog`

### Rondas principales

- `entrenamiento`
- `ejecutada`
- `imaginada`

Cada perfil define, al menos:

- `n_runs`
- `cue_base_duration`
- `cue_tmin_random`
- `cue_tmax_random`
- `randomize_cue_duration`
- `rest_base_duration`
- `rest_tmin_random`
- `rest_tmax_random`
- `randomize_rest_duration`
- y, cuando corresponde, `randomize_per_run`.

---

## Comportamiento de inicialización

Durante la construcción, la clase realiza estas acciones:

1. carga `runConfigurationApp.ui`;
2. carga `styles/runconfiguration_styles.css`;
3. fija el título de ventana;
4. conserva el `config` recibido;
5. actualiza `tipo_ronda_label` según `config["task"]` o un valor por defecto;
6. inicializa `experimento_defaults`;
7. posiciona `comboBox_task` en el tipo de ronda visible;
8. conecta los checkboxes a la lógica de habilitación dinámica;
9. conecta el botón de lanzamiento al dispatcher principal;
10. sincroniza cambios de `comboBox_task` con el label, los defaults y el campo de letras;
11. habilita por defecto `randomize_per_run_box`;
12. conecta la lógica de edición opcional de tablet ID;
13. conecta la navegación de vuelta a `InitAPP`.

---

## Lógica de habilitación dinámica

### `toggle_task_combo()`

Habilita `comboBox_task` sólo si `forzar_ronda_box` está activo. Esto permite bloquear o liberar el cambio manual del tipo de ronda respecto al `config` inicial.

### `toggle_cue_random()`

Activa o desactiva los campos `in_cue_tmin_random` e `in_cue_tmax_random` según el estado de `randomize_cue_duration`.

### `toggle_rest_random()`

Activa o desactiva los campos `in_rest_tmin_random` e `in_rest_tmax_random` según el estado de `randomize_rest_duration`.

### `toggle_semilla()`

Activa o desactiva `in_semilla` según el estado de `semilla_box`.

### `change_in_letters()`

Habilita `in_letters` únicamente para paradigmas que requieren conjunto explícito de letras:

- `entrenamiento`
- `ejecutada`
- `imaginada`

### `toggle_tabletid()`

Activa o desactiva el campo `in_tabletid` según `change_tabid_cbox`.

---

## Construcción de `SessionInfo`

`make_SessionInfo()` crea un objeto `SessionInfo` con los datos disponibles en `self.config` y con `session_id` derivado del tipo de ronda actualmente visible en `comboBox_task`.

Los campos construidos incluyen:

- `sub`
- `ses`
- `task`
- `run`
- `suffix`
- `session_date`
- `bids_file`
- `root_folder`
- `session_id`

La fecha se obtiene con:

```python
time.strftime("%Y-%m-%d")
```

---

## Dispatch de lanzamiento

La función `lanzar_btn_clicked()` decide qué manager instanciar en función del contenido de `comboBox_task`.

### Se lanza `PreExperimentManager` para:

- `basal`
- `emg`
- `eog`

### Se lanza `SessionManager` para:

- `entrenamiento`
- `ejecutada`
- `imaginada`

Una vez creado el manager, la ventana se cierra.

---

## Lanzamiento de `SessionManager`

`lanzar_experimento_completo()` realiza las siguientes tareas:

1. crea `SessionInfo`;
2. lee desde la UI:
   - `n_runs`,
   - tiempos de `cue`,
   - tiempos de `rest`,
   - flags de aleatorización,
   - lista de letras,
   - semilla,
   - tablet ID,
   - nivel de logging;
3. convierte el campo `in_letters` desde texto CSV a lista de strings;
4. configura `logging.basicConfig(...)`;
5. instancia `SessionManager` con los argumentos de runtime.

### Formato esperado para letras

`in_letters` debe contener una lista separada por comas, por ejemplo:

```text
a,d,e,l,m,n,o,r,s,u
```

que se convierte en:

```python
["a", "d", "e", "l", "m", "n", "o", "r", "s", "u"]
```

---

## Lanzamiento de `PreExperimentManager`

`lanzar_preexperiment()` realiza una secuencia análoga, pero orientada a rondas de preexperimento:

1. crea `SessionInfo`;
2. obtiene `task = comboBox_task.currentText().lower()`;
3. lee runs, tiempos, aleatorización y logging;
4. instancia `PreExperimentManager` con `pre_experiment=task`.

A diferencia del flujo principal, aquí no se leen letras ni tablet ID para la lógica de sesión.

---

## API pública relevante

### `update_tipo_ronda_label()`

Copia el texto actual de `comboBox_task` hacia `tipo_ronda_label`.

### `toggle_task_combo()`

Controla si el combo de tareas puede editarse manualmente.

### `toggle_cue_random()`

Controla la habilitación de los parámetros aleatorios de `cue`.

### `toggle_rest_random()`

Controla la habilitación de los parámetros aleatorios de `rest`.

### `toggle_semilla()`

Controla la habilitación del campo de semilla.

### `get_semilla()`

Devuelve:

- un entero, si `semilla_box` está activo y el valor es válido;
- `None`, en cualquier otro caso.

### `change_in_letters()`

Habilita o deshabilita el campo de letras según el tipo de ronda.

### `toggle_tabletid()`

Controla la edición del ID de la tablet.

### `fill_form_with_defaults()`

Carga en la UI el perfil temporal y de aleatorización correspondiente al tipo de ronda actual.

### `lanzar_btn_clicked()`

Despacha la ejecución hacia `lanzar_preexperiment()` o `lanzar_experimento_completo()`.

### `make_SessionInfo()`

Construye la instancia de `SessionInfo` a partir del `config` y del contexto actual.

### `lanzar_experimento_completo()`

Instancia `SessionManager` con parámetros tomados desde la UI.

### `lanzar_preexperiment()`

Instancia `PreExperimentManager` con parámetros tomados desde la UI.

### `volver_inicio()`

Cierra la ventana actual y reabre `InitAPP`.

---

## Ejemplo de uso

```python
config = {
    "sub": "01",
    "ses": "01",
    "task": "ejecutada",
    "run": "01",
    "suffix": "eeg",
    "root": "D:/data",
    "bids_file": "sub-01_ses-01_task-ejecutada_run-01_eeg",
}

app = QApplication(sys.argv)
window = RunConfigurationApp(config=config)
window.show()
sys.exit(app.exec_())
```

---

## Observaciones de diseño

### 1. Esta clase es el puente real entre UI y ejecución

Es el primer componente que traduce el estado de la interfaz en argumentos concretos para los managers.

### 2. `safe_float` está declarado pero no se usa

El método existe como helper potencial, pero actualmente no participa en la lectura de parámetros.

### 3. Puede existir desalineación entre `task` y `session_id`

`make_SessionInfo()` construye `session_id` a partir del tipo de ronda visible en el combo, pero `task` se toma desde `self.config`. Si el operador fuerza una ronda distinta desde la UI, ambos campos pueden divergir.

### 4. El `match` de `lanzar_btn_clicked()` contiene una rama redundante

La rama `case "entrenamiento":` aparece antes de `case "entrenamiento" | "ejecutada" | "imaginada":`, por lo que la primera queda absorbida por la lógica general del mismo destino.

### 5. El lanzador no valida semánticamente los rangos temporales

La clase convierte textos a `float` e `int`, pero no verifica consistencia experimental adicional, como mínimos, máximos o relaciones entre duraciones.

---

## Resumen

`RunConfigurationApp` es la ventana de configuración operativa del sistema. Recibe la metadata base desde `InitAPP`, carga perfiles por defecto según el tipo de ronda, permite ajustar parámetros de runtime y lanza el manager adecuado (`SessionManager` o `PreExperimentManager`). Se trata del componente que transforma una configuración de interfaz en una sesión ejecutable.
