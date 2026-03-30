from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5 import uic
import sys
import os

from pyhwr.managers import PreExperimentManager

class LauncherAPP(QMainWindow):
    def __init__(self, config: dict = None):
        super().__init__()
        # Cargar archivo .ui
        ui_path = os.path.join(os.path.dirname(__file__), 'launcherAPP.ui')
        uic.loadUi(ui_path, self)

        self.config = config
        texto = "ejecutada" if self.config is None or "task" not in self.config else self.config["task"]
        self.tipo_ronda_label.setText(texto)

        ##cargo la task en comboBox_task
        index = self.comboBox_task.findText(texto)
        if index != -1:
            self.comboBox_task.setCurrentIndex(index)
    
        # Conexiones checkbox → lógica de habilitación
        self.forzar_ronda_box.stateChanged.connect(self.toggle_task_combo)
        self.randomize_cue_duration.stateChanged.connect(self.toggle_cue_random)
        self.randomize_rest_duration.stateChanged.connect(self.toggle_rest_random)
        self.semilla_box.stateChanged.connect(self.toggle_semilla)

        # Inicializar estados al arrancar
        self.toggle_task_combo()
        self.toggle_cue_random()
        self.toggle_rest_random()
        self.toggle_semilla()

        ## Conecto el botón lanzar a la función que instancia el manager y muestra la ventana de pre-experiment
        self.lanzar_btn.clicked.connect(self.lanzar_btn_clicked)

        self.comboBox_task.currentIndexChanged.connect(self.update_tipo_ronda_label)

        ##habilito randomize_per_run_box
        self.randomize_per_run_box.setEnabled(True)

    def update_tipo_ronda_label(self):
        texto = self.comboBox_task.currentText()
        self.tipo_ronda_label.setText(texto)

    def toggle_task_combo(self):
        enabled = self.forzar_ronda_box.isChecked()
        if enabled:
            self.update_tipo_ronda_label()
        self.comboBox_task.setEnabled(enabled)

    def toggle_cue_random(self):
        enabled = self.randomize_cue_duration.isChecked()
        self.in_cue_tmin_random.setEnabled(enabled)
        self.in_cue_tmax_random.setEnabled(enabled)


    def toggle_rest_random(self):
        enabled = self.randomize_rest_duration.isChecked()
        self.in_rest_tmin_random.setEnabled(enabled)
        self.in_rest_tmax_random.setEnabled(enabled)

    def toggle_semilla(self):
        enabled = self.semilla_box.isChecked()
        self.in_semilla.setEnabled(enabled)

    def safe_float(widget, default):
        try:
            return float(widget.text())
        except:
            return default
        
    def get_semilla(self):
        if self.semilla_box.isChecked():
            try:
                if self.semilla_box.isChecked():
                    return int(self.in_semilla.text())
            except ValueError:
                return None  ## si o si sacamos la semilla si el valor no es un entero válido
        return None
    
    def lanzar_preexperiment(self):
        from pyhwr.utils import SessionInfo
        from pyhwr.managers.PreExperimentManager import PreExperimentManager
        import time

        ### SessionInfo
        session_info = SessionInfo(
        sub = self.config.get("sub", 1),
        ses = self.config.get("ses", 1),
        task = self.config.get("task", "ejecutada"),
        run = self.config.get("run", 1),
        suffix = self.config.get("suffix", "eeg"),
        session_date=time.strftime("%Y-%m-%d"),)
        print(session_info)
        del time

        ## ***********************************************************
        ## tomando datos de la UI para ejecutar PreExperimentManager
        ## ***********************************************************
        pre_experiment = self.comboBox_task.currentText().lower() ## pre-experimento a ejecutar

        n_runs= int(self.in_nruns.text())
        cue_base_duration = float(self.in_cue_base_duration.text())
        randomize_cue = self.randomize_cue_duration.isChecked()
        cue_tmin = float(self.in_cue_tmin_random.text())
        cue_tmax = float(self.in_cue_tmax_random.text())

        randomize_rest = self.randomize_rest_duration.isChecked()
        rest_base_duration = float(self.in_rest_base_duration.text())
        rest_tmin = float(self.in_rest_tmin_random.text())
        rest_tmax = float(self.in_rest_tmax_random.text())

        ##leo loglevel_comboBox para configurar el logging
        loglevel_str = self.loglevel_comboBox.currentText()
        import logging
        logging.basicConfig(level=getattr(logging, loglevel_str))

        ## Manager de pre-experiment
        self.manager = PreExperimentManager(
            session_info,
            pre_experiment=pre_experiment,
            n_runs= n_runs,
            randomize_per_run= self.randomize_per_run_box.isChecked(),
            seed=self.get_semilla(),
            cue_base_duration=cue_base_duration,
            cue_tmin_random=cue_tmin,
            cue_tmax_random=cue_tmax,
            randomize_cue_duration=randomize_cue,
            rest_base_duration=rest_base_duration,
            rest_tmin_random=rest_tmin,
            rest_tmax_random=rest_tmax,
            randomize_rest_duration=randomize_rest
        )

        ## Mostramos ventana
        self.manager.show()
    
    def lanzar_btn_clicked(self):
        """
        Instancia PreExperimentManager con parámetros de la UI,
        muestra la nueva ventana y cierra el launcher.
        """

        tipo_experimento = self.comboBox_task.currentText()
        match tipo_experimento:
            case "basal" | "emg" | "eog":
                self.lanzar_preexperiment()
            case "entrenamiento":
                print("Lanzar entrenamiento (no implementado aún)")
            case "entrenamiento" | "ejecutada" | "imaginada":
                print("Lanzar experimento completo (no implementado aún)")
            case _:
                print("Seleccionar un tipo de ronda válido para lanzar el pre-experimento.")
                return

        ## Cerramos launcher
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LauncherAPP(config={})
    window.show()
    sys.exit(app.exec_())