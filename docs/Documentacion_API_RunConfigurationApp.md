# API Documentation — `RunConfigurationApp`

## Overview

`RunConfigurationApp` is the second-stage configuration window of the desktop workflow. It receives the base metadata from `InitAPP`, exposes experiment-specific defaults, allows the operator to modify timing and randomization parameters, builds a `SessionInfo` object, and launches either `SessionManager` or `PreExperimentManager`.

It is therefore the bridge between:
- session metadata,
- experiment parameterization,
- actual execution.

## Class signature

```python
class RunConfigurationApp(QMainWindow):
```

## Main responsibilities

- Load the UI and stylesheet for run-level configuration.
- Populate the form with defaults according to the selected task.
- Enable/disable parameter fields based on checkboxes.
- Convert UI state into runtime parameters.
- Build a `SessionInfo` instance.
- Launch either:
  - `SessionManager`, or
  - `PreExperimentManager`.
- Allow returning to `InitAPP`.

## Constructor

```python
RunConfigurationApp(config: dict = None)
```

### `config` contract

The input configuration is expected to contain keys such as:

```python
{
    "sub": ...,
    "ses": ...,
    "task": ...,
    "run": ...,
    "suffix": ...,
    "root": ...,
    "bids_file": ...
}
```

This contract is produced upstream by `InitAPP`.

## Default experiment profiles

The class stores per-task defaults in `self.experimento_defaults`.

Supported keys include:

- `basal`
- `emg`
- `eog`
- `entrenamiento`
- `ejecutada`
- `imaginada`

Each profile may define:
- `n_runs`
- `cue_base_duration`
- `cue_tmin_random`
- `cue_tmax_random`
- `randomize_cue_duration`
- `rest_base_duration`
- `rest_tmin_random`
- `rest_tmax_random`
- `randomize_rest_duration`
- `randomize_per_run`

## Initialization behavior

During construction, the class:

1. Loads `runConfigurationApp.ui`.
2. Loads `styles/runconfiguration_styles.css`.
3. Sets the window title.
4. Stores `config`.
5. Initializes `tipo_ronda_label` from `config["task"]` or falls back to `"ejecutada"`.
6. Loads defaults for the current task.
7. Connects stateful widgets to helper methods.
8. Enables or disables fields according to checkbox state.
9. Connects:
   - launch button,
   - round-type updates,
   - return-to-start behavior,
   - tablet ID field toggling.

## Public API

### `update_tipo_ronda_label()`

Copies the current combo box text into `tipo_ronda_label`.

### `toggle_task_combo()`

Enables or disables the task combo box according to `forzar_ronda_box`.

If enabled, it also refreshes the visible round label.

### `toggle_cue_random()`

Enables or disables the cue randomization min/max inputs based on the state of `randomize_cue_duration`.

### `toggle_rest_random()`

Enables or disables the rest randomization min/max inputs based on the state of `randomize_rest_duration`.

### `toggle_semilla()`

Enables or disables the seed input according to `semilla_box`.

### `get_semilla() -> int | None`

Returns:
- an integer seed if the checkbox is enabled and the input is a valid integer,
- `None` otherwise.

This makes the seed optional and safely suppresses invalid values.

### `change_in_letters()`

Enables `in_letters` only for:
- `entrenamiento`
- `ejecutada`
- `imaginada`

This reflects the fact that those paradigms require an explicit letter set.

### `toggle_tabletid()`

Enables or disables the tablet ID field depending on `change_tabid_cbox`.

### `fill_form_with_defaults()`

Loads the current task profile from `self.experimento_defaults` and populates the timing/randomization fields.

### `lanzar_btn_clicked()`

Dispatches execution according to the selected task:

- `basal`, `emg`, `eog` → `lanzar_preexperiment()`
- `entrenamiento`, `ejecutada`, `imaginada` → `lanzar_experimento_completo()`

If the task is not recognized, the method prints a warning and returns.

The window is closed after a valid launch path.

### `make_SessionInfo() -> SessionInfo`

Builds a `SessionInfo` instance from the stored configuration and the current task context.

Generated fields include:
- `sub`
- `ses`
- `task`
- `run`
- `suffix`
- `session_date`
- `bids_file`
- `root_folder`
- `session_id`

### `lanzar_experimento_completo()`

Builds a `SessionInfo`, parses all runtime parameters from the UI, and instantiates `SessionManager`.

It extracts:
- run count,
- cue timing and randomization,
- rest timing and randomization,
- letter list,
- optional seed,
- tablet ID,
- logging level.

### `lanzar_preexperiment()`

Builds a `SessionInfo`, parses shared runtime parameters, and instantiates `PreExperimentManager`.

### `volver_inicio()`

Closes the current window and reopens `InitAPP`.

## Example usage

### Typical lifecycle

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

window = RunConfigurationApp(config=config)
window.show()
```

### Letter list parsing

If `in_letters` contains:

```text
a,d,e,l,m,n,o,r,s,u
```

then the launch method converts it into:

```python
["a", "d", "e", "l", "m", "n", "o", "r", "s", "u"]
```

## Design observations

### 1. This window is the parameterization hub

It is the first component that translates UI state into actual manager constructor arguments.

### 2. `safe_float` is currently unused

The method exists as a helper idea but is not wired into the current parsing path.

### 3. There is a task consistency risk in `make_SessionInfo()`

`session_id` is built from the current combo selection, but `task` inside `SessionInfo` is read from the original `config` dictionary. If the operator forces a different round through the UI, `SessionInfo.task` and `SessionInfo.session_id` can diverge.

### 4. The `match` in `lanzar_btn_clicked()` contains a redundant branch

There is one branch for `"entrenamiento"` and another for `"entrenamiento" | "ejecutada" | "imaginada"`. The second one still works, but `"entrenamiento"` is already handled earlier.

### 5. Manager instances are created but not explicitly shown here

The code assumes manager construction is sufficient to bootstrap the next execution stage.

## Recommendations

- Make `make_SessionInfo()` derive both `task` and `session_id` from the same current UI source.
- Replace manual parsing with robust helper functions or validator-backed widgets.
- Remove or use `safe_float`.
- Simplify the `match` statement to avoid redundancy.
- Consider validating that the letters list is non-empty for paradigms that require it.

## Summary

`RunConfigurationApp` is the run-time configuration hub of the application. It transforms a simple session descriptor into a fully parameterized experiment or pre-experiment execution request. In the current desktop workflow, it is the most important UI bridge between configuration and execution.
