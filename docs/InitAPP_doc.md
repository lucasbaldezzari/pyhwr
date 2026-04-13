# `InitAPP`

## Descripción general

`InitAPP` es la ventana de entrada al flujo de configuración del proyecto. Su función consiste en recoger la metadata mínima de una ronda experimental, construir un identificador BIDS preliminar y derivar el control hacia `RunConfigurationApp`, donde se definen los parámetros operativos de la sesión.

Dentro de la arquitectura general, esta clase cumple el rol de **punto de arranque de la interfaz de escritorio**. No ejecuta sesiones, no administra timers ni se comunica con hardware; su responsabilidad se limita a validar datos iniciales, preparar la estructura de salida y abrir la siguiente ventana del pipeline.

---

## Rol dentro de la arquitectura

`InitAPP` ocupa la primera etapa del flujo de interfaz:

```text
InitAPP -> RunConfigurationApp -> SessionManager / PreExperimentManager -> LauncherApp
```

Desde esta ventana se definen los campos base que luego serán consumidos por `RunConfigurationApp` para construir un `SessionInfo` y lanzar el manager correspondiente.

---

## Responsabilidades principales

`InitAPP` concentra las siguientes responsabilidades:

1. **Seleccionar el tipo general de experimento**
   - `pre-experimento`
   - `experimento`

2. **Seleccionar el tipo de ronda compatible con ese experimento**
   - por ejemplo `EMG`, `EOG`, `BASAL`, `ENTRENAMIENTO`, `EJECUTADA` o `IMAGINADA`.

3. **Recoger metadata inicial de sesión**
   - sujeto (`sub`),
   - sesión (`ses`),
   - tarea (`task`),
   - run (`run`),
   - sufijo (`suffix`),
   - directorio raíz (`root`).

4. **Construir un nombre BIDS preliminar en tiempo real**
   - siguiendo el patrón `sub-XX_ses-YY_task-Z_run-AA_suffix`.

5. **Validar el formulario antes de permitir avanzar**
   - todos los campos requeridos deben estar completos,
   - el tipo de ronda debe ser válido,
   - y el directorio raíz debe existir.

6. **Crear opcionalmente la estructura mínima de carpetas BIDS**
   - `sub-<id>/ses-<id>/eeg/`.

---

## Dependencias principales

### PyQt5

La clase hereda de `QMainWindow`, carga una interfaz `.ui` y aplica una hoja de estilos CSS desde disco.

### `RunConfigurationApp`

Una vez validado el formulario, `InitAPP` construye un diccionario `config` y delega el flujo a `RunConfigurationApp`, que será el encargado de parametrizar la ejecución real.

### Sistema de archivos local

La clase utiliza `os.path.isdir(...)` para validar el directorio raíz y `os.makedirs(..., exist_ok=True)` para crear la estructura BIDS cuando se solicita.

---

## Firma del constructor

```python
InitAPP()
```

No recibe parámetros externos. Toda la configuración inicial se obtiene desde los widgets cargados en `initAPP.ui`.

---

## Comportamiento de inicialización

Durante la construcción, la clase realiza estas acciones:

1. carga `initAPP.ui`;
2. carga `styles/initapp_styles.css`;
3. establece el título de ventana;
4. fija `os.getcwd()` como directorio raíz por defecto;
5. inicializa `combo_tipo_task` según el experimento seleccionado;
6. conecta cambios de texto al generador de nombre BIDS;
7. fija `eeg` como sufijo por defecto;
8. conecta la validación del formulario a todos los campos relevantes;
9. conecta el selector de carpeta raíz;
10. conecta la lógica de continuidad, reinicio y sincronización entre combos;
11. deja deshabilitado el botón de continuar hasta que el formulario sea válido.

---

## Lógica de selección de tipo de ronda

El contenido de `combo_tipo_task` depende de `combo_experimento`.

### Para `pre-experimento`

Se ofrecen las opciones:

- `Ronda EMG`
- `Ronda EOG`
- `Ronda BASAL`
- `Ronda ENTRENAMIENTO`

### Para `experimento`

Se ofrecen las opciones:

- `Ronda EJECUTADA`
- `Ronda IMAGINADA`

La opción índice `0` se reserva para el placeholder `Seleccionar tipo de ronda` y se considera inválida para avanzar.

---

## Construcción del nombre BIDS

La función `update_filename()` actualiza automáticamente `self.fileName` a partir de los campos del formulario.

### Formato aplicado

```text
sub-<sub>_ses-<ses>_task-<task>_run-<run>_<suffix>
```

### Reglas relevantes

- `sub`, `ses` y `run` se normalizan con padding de dos dígitos cuando contienen enteros.
- si `task` está vacío, se usa `[task]`.
- si `suffix` está vacío, se usa `[suffix]`.

Este nombre se utiliza luego como valor inicial de `bids_file` en el diccionario `config` entregado a la ventana siguiente.

---

## Validación del formulario

La función `validate_form()` habilita el botón `btn_continue` únicamente cuando se cumplen simultáneamente las siguientes condiciones:

- `combo_tipo_task` no está en el índice `0`;
- `sub`, `ses`, `task`, `run` y `suffix` no están vacíos;
- `input_rootfolder` apunta a un directorio existente.

La validación se ejecuta de forma reactiva frente a cambios en campos de texto, cambios de combo y cambios del directorio raíz.

---

## Creación de estructura BIDS

Si `crearBIDSCheck` está activo, `continuar()` invoca `create_bids_structure()` antes de abrir `RunConfigurationApp`.

La estructura creada es:

```text
<root>/sub-<sub>/ses-<ses>/eeg/
```

La operación es idempotente, ya que se utiliza:

```python
os.makedirs(modality_path, exist_ok=True)
```

---

## Flujo de continuación

Cuando el formulario es válido y se presiona continuar, la clase construye un diccionario `config` con las claves:

- `tipo_ronda`
- `sub`
- `ses`
- `task`
- `run`
- `suffix`
- `root`
- `bids_file`

Ese diccionario se entrega a `RunConfigurationApp`, se muestra la nueva ventana y `InitAPP` se cierra.

---

## API pública relevante

### `update_combo_tipo_task()`

Actualiza el contenido de `combo_tipo_task` según el experimento seleccionado y revalida el formulario.

### `continuar()`

Valida la selección de tipo de ronda, crea opcionalmente la estructura BIDS, construye `config`, abre `RunConfigurationApp` y cierra la ventana actual.

### `resetear()`

Restaura el formulario a un estado inicial razonable:

- limpia `sub`, `ses`, `task` y `run`;
- restablece `suffix = "eeg"`;
- vuelve a fijar el directorio de trabajo actual como raíz;
- reinicia la selección de tipo de ronda.

### `update_filename()`

Reconstruye en tiempo real el nombre BIDS preliminar.

### `update_task_from_combo(text)`

Mapea el texto legible de `combo_tipo_task` a la representación interna de `task`:

- `Ronda EMG` -> `emg`
- `Ronda EOG` -> `eog`
- `Ronda BASAL` -> `basal`
- `Ronda ENTRENAMIENTO` -> `entrenamiento`
- `Ronda EJECUTADA` -> `ejecutada`
- `Ronda IMAGINADA` -> `imaginada`

### `validate_form()`

Habilita o deshabilita el botón de avance según la validez global del formulario.

### `select_root_folder()`

Abre un `QFileDialog` para seleccionar el directorio raíz.

### `create_bids_structure()`

Crea la estructura mínima `sub/ses/eeg` bajo la raíz indicada.

---

## Ejemplo de uso

```python
app = QApplication(sys.argv)
window = InitAPP()
window.show()
sys.exit(app.exec_())
```

Uso esperado en el flujo:

1. se completa la metadata base;
2. se selecciona el tipo de ronda;
3. se valida el formulario;
4. se abre `RunConfigurationApp` con el `config` generado.

---

## Observaciones de diseño

### 1. `InitAPP` no construye `SessionInfo`

La clase sólo produce un diccionario intermedio. La creación formal de `SessionInfo` ocurre en `RunConfigurationApp`.

### 2. La UI sincroniza el tipo de ronda con `input_task`

El campo `task` no se rellena manualmente en el flujo nominal, sino que se deriva del texto legible de `combo_tipo_task`.

### 3. La estructura BIDS creada es mínima

Sólo se crea el árbol `sub/ses/eeg`. No se generan archivos BIDS auxiliares ni validaciones adicionales del estándar.

### 4. El directorio raíz por defecto depende del directorio de ejecución

`input_rootfolder` se inicializa con `os.getcwd()`. Esto resulta práctico para desarrollo, pero implica que el valor por defecto cambia según desde dónde se lance la aplicación.

---

## Resumen

`InitAPP` es la ventana de entrada del flujo de escritorio. Su propósito es recoger la metadata mínima de una ronda, construir un nombre BIDS preliminar, validar el formulario y derivar la ejecución hacia `RunConfigurationApp`. Se trata de un componente de preparación y navegación, no de un gestor de sesión ni de adquisición.
