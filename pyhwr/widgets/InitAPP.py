from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWidgets import QFileDialog
from PyQt5 import uic
import sys
import os

class InitAPP(QMainWindow):
    def __init__(self):
        super().__init__()
        ui_path = os.path.join(os.path.dirname(__file__), 'initAPP.ui')
        uic.loadUi(ui_path, self)

        with open("pyhwr\\widgets\\styles\\initapp_styles.css", "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())

        self.setWindowTitle("Selección de tipo de ronda - Proyecto Handwratting - NeuroIA LAB")

        current_dir = os.getcwd()
        self.input_rootfolder.setText(current_dir)

        self.combo_tipo_task.clear()
        self.update_combo_tipo_task()

        ##conecto inputs a update_filename para actualizar el nombre del archivo en tiempo real
        self.input_sub.textChanged.connect(self.update_filename)
        self.input_ses.textChanged.connect(self.update_filename)
        self.input_task.textChanged.connect(self.update_filename)
        self.input_run.textChanged.connect(self.update_filename)
        self.input_suffix.textChanged.connect(self.update_filename)

        ##por defecto dejo eeg en input_suffix
        self.input_suffix.setText("eeg")

        ##conecto inputs a validate_form para habilitar el botón de continuar solo cuando todos los campos estén completos
        self.input_sub.textChanged.connect(self.validate_form)
        self.input_ses.textChanged.connect(self.validate_form)
        self.input_task.textChanged.connect(self.validate_form)
        self.input_run.textChanged.connect(self.validate_form)
        self.input_suffix.textChanged.connect(self.validate_form)
        self.combo_tipo_task.currentIndexChanged.connect(self.validate_form)

        ##conecto el boton browse a la función para seleccionar el directorio raíz
        self.browseBtn.clicked.connect(self.select_root_folder)

        self.combo_tipo_task.currentTextChanged.connect(self.update_task_from_combo)
        self.combo_experimento.currentTextChanged.connect(self.update_combo_tipo_task)

        ##conecto botones
        self.btn_continue.clicked.connect(self.continuar)
        self.btn_reset.clicked.connect(self.resetear)
        self.btn_continue.setEnabled(False)

    def update_combo_tipo_task(self):
        experimento = self.combo_experimento.currentText()

        self.combo_tipo_task.clear()

        if experimento == "pre-experimento":
            self.combo_tipo_task.addItems([
                "Seleccionar tipo de ronda",
                "Ronda EMG",
                "Ronda EOG",
                "Ronda BASAL",
                "Ronda ENTRENAMIENTO",
            ])

        elif experimento == "experimento":
            self.combo_tipo_task.addItems([
                "Seleccionar tipo de ronda",
                "Ronda EJECUTADA",
                "Ronda IMAGINADA"
            ])

        # Reset selección
        self.combo_tipo_task.setCurrentIndex(0)

        # Re-validar formulario
        self.validate_form()

    def continuar(self):
        if self.combo_tipo_task.currentIndex() == 0:
            print("Debe seleccionar un tipo de ronda")
            return

        if self.crearBIDSCheck.isChecked():
            self.create_bids_structure()

        ## diccionario de parámetros para pasar a LauncherAPP
        config = {
            "tipo_ronda": self.combo_tipo_task.currentText(),
            "sub": self.input_sub.text(),
            "ses": self.input_ses.text(),
            "task": self.input_task.text(),
            "run": self.input_run.text(),
            "suffix": self.input_suffix.text(),
            "root": self.input_rootfolder.text(),
            "bids_file": self.fileName.text(),
        }

        from pyhwr.widgets import RunConfigurationApp
        ## Creamos una nueva ventana
        self.launcher = RunConfigurationApp(config)
        self.launcher.show()
        self.close()

    def resetear(self):
        self.input_sub.clear()
        self.input_ses.clear()
        self.input_task.clear()
        self.input_run.clear()
        self.input_suffix.setText("eeg")
        self.input_rootfolder.clear()
        self.combo_tipo_task.setCurrentIndex(0)
        current_dir = os.getcwd()
        self.input_rootfolder.setText(current_dir)
    
    def update_filename(self):
        sub = self.input_sub.text()
        ses = self.input_ses.text()
        task = self.input_task.text()
        run = self.input_run.text()
        suffix = self.input_suffix.text()

        # Formato: padding para números
        if sub.isdigit():
            sub = f"{int(sub):02d}"
        else:
            sub = "[sub]"

        if ses.isdigit():
            ses = f"{int(ses):02d}"
        else:
            ses = "[ses]"

        if run.isdigit():
            run = f"{int(run):02d}"
        else:
            run = "[run]"

        # Campos libres
        task = task if task else "[task]"
        suffix = suffix if suffix else "[suffix]"

        filename = f"sub-{sub}_ses-{ses}_task-{task}_run-{run}_{suffix}"

        self.fileName.setText(filename)

    def update_task_from_combo(self, text):
        if text == "Seleccionar tipo de ronda":
            return  # no hacer nada

        mapping = {
            "Ronda EMG": "emg",
            "Ronda EOG": "eog",
            "Ronda BASAL": "basal",
            "Ronda ENTRENAMIENTO": "entrenamiento",
            "Ronda EJECUTADA": "ejecutada",
            "Ronda IMAGINADA": "imaginada"
        }

        task_value = mapping.get(text, "")

        ##para evitar loops innecesarios
        if self.input_task.text() != task_value:
            self.input_task.setText(task_value)

    def validate_form(self):
        """
        Función para validar que todos los campos estén completos y el combo tenga una selección válida.
        """
        # Validar combo
        tipo_valido = self.combo_tipo_task.currentIndex() != 0

        # Validar inputs (no vacíos)
        sub_ok = self.input_sub.text().strip() != ""
        ses_ok = self.input_ses.text().strip() != ""
        task_ok = self.input_task.text().strip() != ""
        run_ok = self.input_run.text().strip() != ""
        suffix_ok = self.input_suffix.text().strip() != ""

        root_ok = os.path.isdir(self.input_rootfolder.text())

        all_valid = tipo_valido and sub_ok and ses_ok and task_ok and run_ok and suffix_ok and root_ok

        self.btn_continue.setEnabled(all_valid)

    def select_root_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar directorio raíz")
        if folder:
            self.input_rootfolder.setText(folder)

    def create_bids_structure(self):
        root = self.input_rootfolder.text().strip()

        sub = self.input_sub.text().strip()
        ses = self.input_ses.text().strip()

        if sub.isdigit():
            sub = f"{int(sub):02d}"
        if ses.isdigit():
            ses = f"{int(ses):02d}"

        sub_label = f"sub-{sub}"
        ses_label = f"ses-{ses}"

        modality = "eeg"

        # Construcción de paths
        sub_path = os.path.join(root, sub_label)
        ses_path = os.path.join(sub_path, ses_label)
        modality_path = os.path.join(ses_path, modality)

        # Crear carpetas (idempotente)
        os.makedirs(modality_path, exist_ok=True)

        print(f"Estructura creada/verificada en: {modality_path}")

if __name__ == "__main__":

    app = QApplication(sys.argv)
    initapp = InitAPP()
    initapp.show()
    sys.exit(app.exec_())