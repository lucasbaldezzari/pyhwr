# API Documentation — `LauncherApp`

## Overview

`LauncherApp` is the operational pre-run control panel used by `SessionManager`. It exposes a checklist of readiness conditions, displays current session metadata, and emits start/stop/quit signals that drive the session lifecycle.

Unlike `InitAPP` and `RunConfigurationApp`, this class is not a metadata editor. It is an execution control surface.

## Class signature

```python
class LauncherApp(QMainWindow):
```

## Qt signals

```python
start_session_signal = pyqtSignal()
stop_session_signal = pyqtSignal()
quit_session_signal = pyqtSignal()
```

These signals are connected by `SessionManager` to:
- `startSession`
- `stopSession`
- `quitSession`

## Main responsibilities

- Load and display the launcher UI.
- Show session metadata such as subject, task, runs, BIDS file, and root folder.
- Maintain a checklist of pre-run conditions.
- Enable Start only when all checklist items are marked.
- Emit lifecycle signals.
- Offer copy-to-clipboard helpers.
- Optionally reopen `RunConfigurationApp`.

## Constructor

```python
LauncherApp()
```

## Initialization behavior

During construction, the class:

1. Loads `launcherApp.ui`.
2. Loads `styles/launcherapp_styles.css`.
3. Sets the window title.
4. Disables Start and Stop initially.
5. Connects:
   - start button,
   - stop button,
   - quit button,
   - return button.
6. Calls `update_session_info()` with safe defaults.
7. Connects all readiness checkboxes to `_update_start_button()`.
8. Connects copy buttons and edit-toggle checkboxes.
9. Stores all required readiness checkboxes in `self.checkboxes`.

## Readiness checklist

The launcher requires all of these to be checked before enabling Start:

- `wigen_cbox`
- `widpos_cbox`
- `senspos_cbox`
- `senscali_cbox`
- `triggersok_cbox`
- `gtecfile_cbox`
- `gtec_impe_cbox`
- `gtecrecord_cbox`
- `lslstarted_cbox`
- `lslstreamers_cbox`

This is a purely UI-level gating mechanism.

## Public API

### `update_session_info(...)`

```python
update_session_info(
    sub="01",
    task="basal",
    n_runs="1",
    ses="01",
    run="01",
    bids_file="sub-[sub]_ses-[ses]_task-[task]_run-[run]_[suffix]",
    root_folder="D:\repos\pyhwr\"
)
```

Writes the provided values into the session information labels.

Important behavior:
- `bids_label` receives `bids_file + ".xdf"`
- `gtec_bids_label` receives `bids_file + ".hdf5"`

This assumes `bids_file` is passed without extension.

### `check_all()`

Marks every readiness checkbox as checked.

Useful for testing or fast bypass of manual checklist interaction.

### `_update_start_button()`

Enables Start only when all required checkboxes are checked.

### `_on_start()`

UI behavior:
- prints `"Iniciar"`,
- disables Start,
- enables Stop,
- disables `volver_btn`,
- emits `start_session_signal`.

### `_on_stop()`

UI behavior:
- prints `"Parar"`,
- enables Start,
- disables Stop,
- keeps `volver_btn` disabled,
- emits `stop_session_signal`.

### `_on_quit()`

Prints `"Salir"` and emits `quit_session_signal`.

### `_volver_config()`

Instantiates `RunConfigurationApp(config={})`, shows it, and closes the current launcher window.

### `_copy_bids()`

Copies the BIDS XDF path label to the clipboard.

### `_copy_gtecbids()`

Copies the g.HIAMP HDF5 path label to the clipboard.

### `_copy_root()`

Copies the root folder label to the clipboard.

### `_toggle_bids_edit()`

Makes the BIDS label editable or read-only according to `changebids_cbox`.

### `_toggle_gtecbids_edit()`

Makes the g.HIAMP BIDS label editable or read-only according to `changegbids_cbox`.

### `_toggle_root_edit()`

Makes the root folder label editable or read-only according to `changeroot_cbox`.

## Integration with `SessionManager`

`SessionManager.initUI()` uses this class as follows:

```python
self.launcher = LauncherApp()
self.launcher.update_session_info(
    sub=self.sessioninfo.sub,
    task=self.experimento,
    n_runs=self.n_runs,
    bids_file=self.sessioninfo["bids_file"],
    root_folder=self.sessioninfo["root_folder"],
    ses=self.sessioninfo["ses"],
    run=self.sessioninfo["run"],
)

self.launcher.start_session_signal.connect(self.startSession)
self.launcher.stop_session_signal.connect(self.stopSession)
self.launcher.quit_session_signal.connect(self.quitSession)
```

So `LauncherApp` is the direct operator-facing frontend for the session lifecycle.

## Example usage

### Standalone

```python
app = QApplication(sys.argv)
launcher = LauncherApp()
launcher.show()
sys.exit(app.exec_())
```

### SessionManager-driven use

```python
launcher = LauncherApp()
launcher.update_session_info(
    sub="01",
    task="ejecutada",
    n_runs=8,
    ses="01",
    run="01",
    bids_file="sub-01_ses-01_task-ejecutada_run-01_eeg",
    root_folder="D:/data"
)
```

## Design observations

### 1. Start gating is UI-only

The launcher does not verify hardware or stream state itself. It only checks whether the operator marked the checklist.

### 2. `volver_btn` becomes unusable once the session starts

Both `_on_start()` and `_on_stop()` disable it, reflecting the current design that once acquisition enters execution mode, the operator should not return to configuration through this window.

### 3. `_volver_config()` reconstructs configuration incompletely

It reopens `RunConfigurationApp(config={})` with an almost empty configuration dictionary. That means the original session context is not preserved when navigating back.

### 4. The path labels are editable conditionally

This is useful operationally, but it means the UI can diverge from the original `SessionInfo` values unless downstream code re-reads these edited labels intentionally.

## Recommendations

- If back-navigation should preserve context, `_volver_config()` should rebuild the original config instead of passing `{}`.
- Consider replacing `print(...)` calls with logging for consistency with the rest of the project.
- Consider separating displayed labels from editable path inputs if user edits are intended to affect execution.
- If the readiness checklist is safety-critical, add optional programmatic validation hooks.

## Summary

`LauncherApp` is the operator control panel that sits immediately before and during session execution. It exposes readiness gating, displays session metadata, and emits the start/stop/quit signals consumed by `SessionManager`.
