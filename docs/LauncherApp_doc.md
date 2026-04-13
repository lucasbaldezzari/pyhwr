# `LauncherApp`

## Descripción general

`LauncherApp` es el panel local de control operativo que se utiliza inmediatamente antes y durante la ejecución de una sesión. Su función consiste en mostrar la metadata relevante de la ronda, mantener un checklist de preparación previa y emitir señales Qt de inicio, detención y cierre consumidas por el manager activo.

A diferencia de `InitAPP` y `RunConfigurationApp`, esta clase no edita la configuración experimental de base. Su rol es el de **superficie de control de ejecución** para operadores, una vez que la sesión ya ha sido parametrizada.

---

## Rol dentro de la arquitectura

`LauncherApp` aparece en la etapa de ejecución y se integra principalmente con `SessionManager` y `PreExperimentManager`.

```text
InitAPP -> RunConfigurationApp -> SessionManager / PreExperimentManager -> LauncherApp
```

El manager correspondiente instancia esta ventana en `initUI()`, actualiza su metadata visible y conecta sus señales a métodos como `startSession()`, `stopSession()` y `quitSession()`.

---

## Responsabilidades principales

La clase concentra las siguientes responsabilidades:

1. **Mostrar metadata operativa de la sesión**
   - sujeto,
   - tarea,
   - número de runs,
   - sesión,
   - run,
   - nombre BIDS,
   - ruta raíz.

2. **Mantener un checklist previo al inicio**
   - widget generator,
   - posición de widgets,
   - posición de sensores,
   - calibración,
   - triggers,
   - archivo de g.tec,
   - impedancias,
   - recording,
   - LSL iniciado,
   - streamers disponibles.

3. **Bloquear o habilitar el inicio**
   - el botón `Iniciar` sólo se habilita cuando todos los checkboxes requeridos están activos.

4. **Emitir señales de ciclo de vida**
   - `start_session_signal`
   - `stop_session_signal`
   - `quit_session_signal`

5. **Proporcionar utilidades de copia y edición condicional de rutas**
   - copiar BIDS XDF,
   - copiar BIDS HDF5,
   - copiar raíz,
   - habilitar edición manual de esos campos visibles.

---

## Dependencias principales

### PyQt5

La clase hereda de `QMainWindow`, define señales con `pyqtSignal` y carga una interfaz `.ui` junto con una hoja de estilos CSS.

### `SessionManager` y `PreExperimentManager`

Estos managers utilizan `LauncherApp` como panel frontal de control durante la ejecución.

### `RunConfigurationApp`

La navegación hacia atrás intenta reconstruir `RunConfigurationApp` desde `_volver_config()`.

---

## Señales Qt expuestas

```python
start_session_signal = pyqtSignal()
stop_session_signal = pyqtSignal()
quit_session_signal = pyqtSignal()
```

Estas señales se conectan externamente a los métodos del manager activo.

---

## Firma del constructor

```python
LauncherApp()
```

No recibe parámetros. La metadata visible se actualiza posteriormente con `update_session_info(...)`.

---

## Comportamiento de inicialización

Durante la construcción, la clase realiza estas acciones:

1. carga `launcherApp.ui`;
2. carga `styles/launcherapp_styles.css`;
3. fija el título de ventana;
4. deshabilita inicialmente `iniciar_btn` y `parar_btn`;
5. conecta los botones principales a sus handlers internos;
6. llama a `update_session_info()` con valores de respaldo;
7. conecta todos los checkboxes relevantes a `_update_start_button()`;
8. conecta `check_all_btn` a `check_all()`;
9. conecta los botones de copia al portapapeles;
10. conecta los checkboxes que habilitan edición manual de rutas;
11. agrupa los checkboxes requeridos en `self.checkboxes`.

---

## Checklist de preparación

El botón `Iniciar` depende del estado conjunto de estos checkboxes:

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

La lógica es puramente de interfaz:

```python
all_checked = all(cb.isChecked() for cb in self.checkboxes)
```

Por tanto, `LauncherApp` no verifica por sí mismo el estado real del hardware o de los streams. Sólo refleja la confirmación manual realizada en la UI.

---

## Actualización de metadata visible

La función `update_session_info(...)` escribe en la interfaz los datos visibles de la sesión.

### Firma

```python
update_session_info(
    sub="01",
    task="basal",
    n_runs="1",
    ses="01",
    run="01",
    bids_file="sub-[sub]_ses-[ses]_task-[task]_run-[run]_[suffix]",
    root_folder="D:\\repos\\pyhwr\\"
)
```

### Comportamiento relevante

- `bids_label` recibe `bids_file + ".xdf"`
- `gtec_bids_label` recibe `bids_file + ".hdf5"`

Esto implica que el argumento `bids_file` debe entregarse **sin extensión**, ya que la clase añade ambas extensiones de manera automática.

---

## API pública relevante

### `update_session_info(...)`

Actualiza los labels de metadata de la sesión en la UI.

### `check_all()`

Marca todos los checkboxes del checklist como verificados. Resulta útil para pruebas o bypass rápido del gating manual.

### `_update_start_button()`

Habilita `iniciar_btn` sólo cuando todos los checkboxes requeridos están activos.

### `_on_start()`

Al presionar iniciar:

- imprime `"Iniciar"`;
- deshabilita `iniciar_btn`;
- habilita `parar_btn`;
- deshabilita `volver_btn`;
- emite `start_session_signal`.

### `_on_stop()`

Al presionar parar:

- imprime `"Parar"`;
- habilita `iniciar_btn`;
- deshabilita `parar_btn`;
- mantiene `volver_btn` deshabilitado;
- emite `stop_session_signal`.

### `_on_quit()`

Imprime `"Salir"` y emite `quit_session_signal`.

### `_volver_config()`

Cierra la ventana actual y reabre `RunConfigurationApp(config={})`.

### `_copy_bids()`

Copia `bids_label` al portapapeles.

### `_copy_gtecbids()`

Copia `gtec_bids_label` al portapapeles.

### `_copy_root()`

Copia `root_label` al portapapeles.

### `_toggle_bids_edit()`

Activa o desactiva la edición manual de `bids_label`.

### `_toggle_gtecbids_edit()`

Activa o desactiva la edición manual de `gtec_bids_label`.

### `_toggle_root_edit()`

Activa o desactiva la edición manual de `root_label`.

---

## Integración con los managers

Tanto `SessionManager` como `PreExperimentManager` utilizan esta ventana como panel de operación local.

El patrón de integración es:

```python
self.launcher = LauncherApp()
self.launcher.update_session_info(...)
self.launcher.start_session_signal.connect(self.startSession)
self.launcher.stop_session_signal.connect(self.stopSession)
self.launcher.quit_session_signal.connect(self.quitSession)
```

En consecuencia, `LauncherApp` no contiene lógica experimental propia, sino la interfaz que dispara el ciclo de vida del manager que la hospeda.

---

## Ejemplo de uso

```python
app = QApplication(sys.argv)
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
launcher.show()
sys.exit(app.exec_())
```

---

## Observaciones de diseño

### 1. El gating de inicio es sólo declarativo

La ventana no verifica impedancias, streams ni archivos. Sólo comprueba el estado de los checkboxes.

### 2. `volver_btn` deja de ser utilizable al entrar en ejecución

Tanto `_on_start()` como `_on_stop()` lo deshabilitan. Esto refleja la decisión actual de impedir el retorno a configuración desde este panel una vez iniciada la ronda.

### 3. `_volver_config()` no preserva el contexto original

La reconstrucción de `RunConfigurationApp` se hace con `config={}`. Por tanto, al volver no se conserva automáticamente la metadata previa de la sesión.

### 4. Los labels de rutas pueden divergir del `SessionInfo` original

La UI permite hacer editables ciertas rutas y nombres visibles. Si esas ediciones se usan operativamente, podrían quedar desalineadas con la metadata original si el resto del sistema no las vuelve a leer explícitamente.

### 5. Los mensajes operativos usan `print(...)`

La clase utiliza `print(...)` para acciones de inicio, parada y salida, en lugar de integrarse con el sistema de logging del resto del proyecto.

---

## Resumen

`LauncherApp` es el panel local de control de ejecución utilizado por los managers de sesión. Muestra metadata operativa, impone un checklist previo al inicio y emite las señales Qt que gobiernan el ciclo de vida de la ronda. No parametriza la sesión ni valida hardware de manera programática; su rol es el de interfaz operativa de control durante la ejecución.
