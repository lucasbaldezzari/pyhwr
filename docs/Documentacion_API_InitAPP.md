# API Documentation — `InitAPP`

## Overview

`InitAPP` is the entry-point configuration window for the experimental GUI workflow. It collects the base session metadata, derives a BIDS-style filename, validates the form, optionally creates the directory structure, and hands control to `RunConfigurationApp`.

This class does not launch acquisition directly. Its role is to gather the minimal run-independent metadata required to define the session context.

## Class signature

```python
class InitAPP(QMainWindow):
```

## Main responsibilities

- Load the initial Qt Designer UI and stylesheet.
- Initialize the default root folder.
- Constrain the task selector according to experiment type.
- Keep the filename preview synchronized with the form.
- Validate that the form is complete before enabling continuation.
- Optionally create a minimal BIDS-like folder structure.
- Create and open `RunConfigurationApp` with a `config` dictionary.

## Constructor

```python
InitAPP()
```

## Initialization behavior

During construction, the class:

1. Loads `initAPP.ui`.
2. Loads `styles/initapp_styles.css`.
3. Sets the window title.
4. Sets the current working directory as the default root folder.
5. Clears and repopulates `combo_tipo_task` according to `combo_experimento`.
6. Connects text fields to `update_filename()`.
7. Forces `input_suffix` to `"eeg"` by default.
8. Connects validation callbacks to all relevant fields.
9. Connects:
   - `browseBtn` → `select_root_folder`
   - `btn_continue` → `continuar`
   - `btn_reset` → `resetear`
10. Disables the continue button until the form is valid.

## User-facing workflow

The window guides the user through these steps:

1. Choose whether the workflow is for `pre-experimento` or `experimento`.
2. Select the type of round.
3. Enter `sub`, `ses`, `task`, `run`, and `suffix`.
4. Choose or keep a root folder.
5. Optionally request creation of the BIDS directory structure.
6. Continue to `RunConfigurationApp`.

## Public API

### `update_combo_tipo_task()`

Rebuilds the task selector according to `combo_experimento.currentText()`.

Supported modes:

- `pre-experimento`
  - `Ronda EMG`
  - `Ronda EOG`
  - `Ronda BASAL`
  - `Ronda ENTRENAMIENTO`

- `experimento`
  - `Ronda EJECUTADA`
  - `Ronda IMAGINADA`

After reloading the combo box:
- the selection is reset to index `0`,
- the form is revalidated.

### `continuar()`

Validates that a round type was selected and, if requested, creates the directory structure.

Then it builds a configuration dictionary with keys:

```python
{
    "tipo_ronda": ...,
    "sub": ...,
    "ses": ...,
    "task": ...,
    "run": ...,
    "suffix": ...,
    "root": ...,
    "bids_file": ...
}
```

That dictionary is passed to:

```python
RunConfigurationApp(config)
```

The new window is shown and the current window is closed.

### `resetear()`

Resets all editable fields to a clean state:
- clears `sub`, `ses`, `task`, `run`,
- resets `suffix` to `"eeg"`,
- clears the root folder and restores the current working directory,
- resets the round selector.

### `update_filename()`

Builds the filename preview in BIDS-like style:

```python
sub-XX_ses-YY_task-<task>_run-ZZ_<suffix>
```

Behavior:
- numeric `sub`, `ses`, and `run` are padded to two digits,
- empty `task` and `suffix` are replaced with placeholders.

This method writes the result into `self.fileName`.

### `update_task_from_combo(text)`

Maps human-readable combo values to internal task labels:

- `Ronda EMG` → `emg`
- `Ronda EOG` → `eog`
- `Ronda BASAL` → `basal`
- `Ronda ENTRENAMIENTO` → `entrenamiento`
- `Ronda EJECUTADA` → `ejecutada`
- `Ronda IMAGINADA` → `imaginada`

It updates `input_task` only if the current value differs, preventing unnecessary signal loops.

### `validate_form()`

Enables the Continue button only when:
- a valid round type is selected,
- all required text fields are non-empty,
- the root folder points to an existing directory.

### `select_root_folder()`

Opens a `QFileDialog` and writes the selected directory to `input_rootfolder`.

### `create_bids_structure()`

Creates the directory tree:

```text
<root>/
  sub-XX/
    ses-YY/
      eeg/
```

The operation is idempotent because it uses `os.makedirs(..., exist_ok=True)`.

## Example usage

### Start the GUI

```python
app = QApplication(sys.argv)
window = InitAPP()
window.show()
sys.exit(app.exec_())
```

### What `continuar()` effectively produces

```python
config = {
    "tipo_ronda": "ejecutada",
    "sub": "01",
    "ses": "01",
    "task": "ejecutada",
    "run": "01",
    "suffix": "eeg",
    "root": "D:/data",
    "bids_file": "sub-01_ses-01_task-ejecutada_run-01_eeg",
}
```

## Design observations

### 1. This class defines the first formal contract of the workflow

`InitAPP` produces the `config` dictionary later consumed by `RunConfigurationApp`.

### 2. Validation is UI-centric, not domain-centric

The validation checks:
- completeness,
- existing root directory,
- combo selection.

It does not validate:
- semantic correctness of `task`,
- positive integer constraints for `sub`, `ses`, `run`,
- compatibility between experiment mode and task if the text fields are edited manually.

### 3. Filename generation is a preview, not a filesystem write

`update_filename()` only updates a visible label or line edit. The actual filesystem effect happens only in `create_bids_structure()`.

### 4. The root folder defaults to `os.getcwd()`

This is practical, but it means the default storage path depends on where the process is launched from.

## Recommendations

- Add stronger domain validation for `sub`, `ses`, and `run`.
- Consider making `input_task` read-only if task selection should come exclusively from the combo box.
- Consider splitting BIDS filename generation into a pure helper function for easier testing.
- Consider validating that `suffix` belongs to an allowed set when appropriate.

## Summary

`InitAPP` is the metadata bootstrap window of the desktop workflow. It is intentionally simple and mainly serves to:
- collect session metadata,
- derive a standardized filename,
- create the next-step configuration payload,
- hand control to `RunConfigurationApp`.
