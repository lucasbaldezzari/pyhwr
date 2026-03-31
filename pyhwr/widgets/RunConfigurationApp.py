from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5 import uic
import sys
import os

class RunConfigurationApp(QMainWindow):
    def __init__(self, config: dict = None):
        super().__init__()
        # Cargar archivo .ui
        ui_path = os.path.join(os.path.dirname(__file__), 'runConfigurationApp.ui')
        uic.loadUi(ui_path, self)

        self.config = config
        texto = "ejecutada" if self.config is None or "task" not in self.config else self.config["task"]
        self.tipo_ronda_label.setText(texto)

        ##diccionario con tiempos y cantidad de runs por defecto según tipo de experimento
        self.experimento_defaults = {
            "basal": {
                "n_runs": 1,
                "cue_base_duration": 60.,
                "cue_tmin_random": 0.,
                "cue_tmax_random": 0.,
                "randomize_cue_duration": False,
                "rest_base_duration": 1.,
                "rest_tmin_random": 0.,
                "rest_tmax_random": 1.,
                "randomize_rest_duration": False,
            },
            "emg": {
                "n_runs": 1,
                "cue_base_duration": 2.,
                "cue_tmin_random": 0.1,
                "cue_tmax_random": 0.5,
                "randomize_cue_duration": True,
                "rest_base_duration": 2.,
                "rest_tmin_random": 0.5,
                "rest_tmax_random": 1.,
                "randomize_rest_duration": True,
                "randomize_per_run": False,
            },
            "eog": {
                "n_runs": 1,
                "cue_base_duration": 2.,
                "cue_tmin_random": 0.1,
                "cue_tmax_random": 0.5,
                "randomize_cue_duration": True,
                "rest_base_duration": 2.,
                "rest_tmin_random": 0.5,
                "rest_tmax_random": 1.,
                "randomize_rest_duration": True,
                "randomize_per_run": False,
            },
            "entrenamiento": {
                "n_runs": 1,
                "cue_base_duration": 4.,
                "cue_tmin_random": 1.,
                "cue_tmax_random": 2.,
                "randomize_cue_duration": True,
                "rest_base_duration": 1.,
                "rest_tmin_random": 0.,
                "rest_tmax_random": 1.,
                "randomize_rest_duration": True,
                "randomize_per_run": True,
            },
            "ejecutada": {
                "n_runs": 8,
                "cue_base_duration": 4.,
                "cue_tmin_random": 1.,
                "cue_tmax_random": 2.,
                "randomize_cue_duration": True,
                "rest_base_duration": 1.,
                "rest_tmin_random": 0.,
                "rest_tmax_random": 1.,
                "randomize_rest_duration": True,
                "randomize_per_run": True,
            },
            "imaginada": {
                "n_runs": 8,
                "cue_base_duration": 4.,
                "cue_tmin_random": 1.,
                "cue_tmax_random": 2.,
                "randomize_cue_duration": True,
                "rest_base_duration": 1.,
                "rest_tmin_random": 0.,
                "rest_tmax_random": 1.,
                "randomize_rest_duration": True,
                "randomize_per_run": True,
            },
        }

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
        self.comboBox_task.currentIndexChanged.connect(self.fill_form_with_defaults)
        self.comboBox_task.currentIndexChanged.connect(self.change_in_letters)
        self.fill_form_with_defaults()  # Llenar con valores por defecto al iniciar

        ##habilito randomize_per_run_box
        self.randomize_per_run_box.setEnabled(True)

        ##conecto toggle_tabletid a change_tabid_cbox
        self.change_tabid_cbox.stateChanged.connect(self.toggle_tabletid)

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

    def change_in_letters(self):
        """
        Habilita o deshabilita el campo de letras según el tipo de experimento.
        """
        texto = self.tipo_ronda_label.text().lower()
        enabled = texto in ["entrenamiento", "ejecutada", "imaginada"]
        self.in_letters.setEnabled(enabled)

    ##función para leer el estado de change_tabid_cbox y habilitar in_tabletid
    def toggle_tabletid(self):
        enabled = self.change_tabid_cbox.isChecked()
        self.in_tabletid.setEnabled(enabled)
    
    def fill_form_with_defaults(self):
        experimento = self.tipo_ronda_label.text().lower()
        defaults = self.experimento_defaults.get(experimento, {})
        self.in_nruns.setText(str(defaults["n_runs"]))
        self.in_cue_base_duration.setText(str(defaults["cue_base_duration"]))
        self.randomize_cue_duration.setChecked(defaults["randomize_cue_duration"])
        self.in_cue_tmin_random.setText(str(defaults["cue_tmin_random"]))
        self.in_cue_tmax_random.setText(str(defaults["cue_tmax_random"]))
        self.randomize_rest_duration.setChecked(defaults["randomize_rest_duration"])
        self.in_rest_base_duration.setText(str(defaults["rest_base_duration"]))
        self.in_rest_tmin_random.setText(str(defaults["rest_tmin_random"]))
        self.in_rest_tmax_random.setText(str(defaults["rest_tmax_random"]))
        self.randomize_per_run_box.setChecked(defaults.get("randomize_per_run", False))

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
                self.lanzar_experimento_completo()
            case "entrenamiento" | "ejecutada" | "imaginada":
                self.lanzar_experimento_completo()
            case _:
                print("Ninguna de las opciones es válida. No se hace nada.")
                return

        ## Cerramos launcher
        self.close()

    def make_SessionInfo(self):
        from pyhwr.utils import SessionInfo
        import time
        ### SessionInfo
        task = self.comboBox_task.currentText()
        bidsf_file = f"sub-01_ses-01_task-{task}_run-01_eeg.bdf"
        session_info = SessionInfo(
        sub = self.config.get("sub", 1),
        ses = self.config.get("ses", 1),
        task = self.config.get("task", "ejecutada"),
        run = self.config.get("run", 1),
        suffix = self.config.get("suffix", "eeg"),
        session_date=time.strftime("%Y-%m-%d"),
        bids_file=self.config.get("bids_file", bidsf_file),
        )
        del time
        del SessionInfo

        return session_info
    
    def lanzar_experimento_completo(self):
        """
        Función placeholder para lanzar experimento completo (entrenamiento, ejecutada o imaginada).
        """

        from pyhwr.managers import SessionManager

        ### SessionInfo
        session_info = self.make_SessionInfo()

        ## ***********************************************************
        ## tomando datos de la UI para ejecutar PreExperimentManager
        ## ***********************************************************
        task = self.comboBox_task.currentText().lower() ## pre-experimento a ejecutar

        n_runs= int(self.in_nruns.text())
        cue_base_duration = float(self.in_cue_base_duration.text())
        randomize_cue = self.randomize_cue_duration.isChecked()
        cue_tmin = float(self.in_cue_tmin_random.text())
        cue_tmax = float(self.in_cue_tmax_random.text())

        randomize_rest = self.randomize_rest_duration.isChecked()
        rest_base_duration = float(self.in_rest_base_duration.text())
        rest_tmin = float(self.in_rest_tmin_random.text())
        rest_tmax = float(self.in_rest_tmax_random.text())

        ##tomo las letras de in_letters que tienen el formato a,d,e,l,m,n,o,r,s,u y lo paso a lista
        letters_str = self.in_letters.text()
        letters = [letter.strip() for letter in letters_str.split(",") if letter.strip()]

        ##leo loglevel_comboBox para configurar el logging
        loglevel_str = self.loglevel_comboBox.currentText()
        import logging
        logging.basicConfig(level=getattr(logging, loglevel_str))

        self.manager = SessionManager(
            session_info,
            n_runs = n_runs,
            letters = letters,
            randomize_per_run= self.randomize_per_run_box.isChecked(),
            seed=self.get_semilla(),
            cue_base_duration=cue_base_duration,
            cue_tmin_random=cue_tmin,
            cue_tmax_random=cue_tmax,
            randomize_cue_duration=randomize_cue,
            rest_base_duration=rest_base_duration,
            rest_tmin_random=rest_tmin,
            rest_tmax_random=rest_tmax,
            randomize_rest_duration=randomize_rest,
            tabletID=self.in_tabletid.text()
        )
    
    def lanzar_preexperiment(self):
        from pyhwr.managers import PreExperimentManager

        ### SessionInfo
        session_info = self.make_SessionInfo()

        ## ***********************************************************
        ## tomando datos de la UI para ejecutar PreExperimentManager
        ## ***********************************************************
        task = self.comboBox_task.currentText().lower() ## pre-experimento a ejecutar

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
            pre_experiment=task,
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RunConfigurationApp(config={})
    window.show()
    sys.exit(app.exec_())