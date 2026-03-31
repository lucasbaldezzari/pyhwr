from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import pyqtSignal
import sys
import os


class LauncherApp(QMainWindow):

    start_session_signal = pyqtSignal()
    stop_session_signal = pyqtSignal()
    quit_session_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        ui_path = os.path.join(os.path.dirname(__file__), 'launcherApp.ui')
        uic.loadUi(ui_path, self)

        with open("pyhwr\\widgets\\styles\\launcherapp_styles.css", "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())

        self.setWindowTitle("Launcher APP - Proyecto Handwratting - NeuroIA LAB")

        self.iniciar_btn.setEnabled(False)
        self.parar_btn.setEnabled(False)

        # conexiones de botones y checkboxes
        self.iniciar_btn.clicked.connect(self._on_start)
        self.parar_btn.clicked.connect(self._on_stop)
        self.salir_btn.clicked.connect(self._on_quit)
        self.volver_btn.clicked.connect(self._volver_config)
        self.update_session_info()

        # conectar checkboxes
        self.wigen_cbox.stateChanged.connect(self._update_start_button)
        self.widpos_cbox.stateChanged.connect(self._update_start_button)
        self.senspos_cbox.stateChanged.connect(self._update_start_button)
        self.senscali_cbox.stateChanged.connect(self._update_start_button)
        self.triggersok_cbox.stateChanged.connect(self._update_start_button)
        self.gtecfile_cbox.stateChanged.connect(self._update_start_button)
        self.gtec_impe_cbox.stateChanged.connect(self._update_start_button)
        self.gtecrecord_cbox.stateChanged.connect(self._update_start_button)
        self.lslstarted_cbox.stateChanged.connect(self._update_start_button)
        self.lslstreamers_cbox.stateChanged.connect(self._update_start_button)
        self.check_all_btn.clicked.connect(self.check_all)

        ##botones para copiar
        self.copybids_btn.clicked.connect(self._copy_bids)
        self.copyroot_btn.clicked.connect(self._copy_root)

        ##conecto a funciones para habilitar cambio de bids y root
        self.changebids_cbox.stateChanged.connect(self._toggle_bids_edit)
        self.changeroot_cbox.stateChanged.connect(self._toggle_root_edit)

        self.checkboxes = [
            self.wigen_cbox,
            self.widpos_cbox,
            self.senspos_cbox,
            self.senscali_cbox,
            self.triggersok_cbox,
            self.gtecfile_cbox,
            self.gtec_impe_cbox,
            self.gtecrecord_cbox,
            self.lslstarted_cbox,
            self.lslstreamers_cbox,
        ]

    def update_session_info(self, sub="01", task="basal", n_runs="1",
                            bids_file="sub-[sub]_ses-[ses]_task-[task]_run-[run]_[suffix]",
                            root_folder="D:\\repos\\pyhwr\\"):
        """
        Actualiza los labels de la UI con información de la sesión.
        Todos los parámetros tienen valores por defecto para robustez.
        """

        self.sub_label.setText(str(sub))
        self.task_label.setText(str(task))
        self.nruns_label.setText(str(n_runs))
        self.bids_label.setText(str(bids_file))
        self.root_label.setText(str(root_folder))

    def check_all(self):
        """
        Marca todos los checkboxes como verificados.
        """
        for cb in self.checkboxes:
            cb.setChecked(True)

    def _update_start_button(self):
        """
        Habilita el botón 'Iniciar' solo si todos los checkboxes requeridos están activos.
        """

        all_checked = all(cb.isChecked() for cb in self.checkboxes)
        self.iniciar_btn.setEnabled(all_checked)

    def _on_start(self):
        """Inicia la sesión, emitiendo la señal correspondiente."""
        print("Iniciar")
        self.iniciar_btn.setEnabled(False)
        self.parar_btn.setEnabled(True)
        self.start_session_signal.emit()

    def _on_stop(self):
        """Detiene la sesión, emitiendo la señal correspondiente."""
        print("Parar")
        self.iniciar_btn.setEnabled(True)
        self.parar_btn.setEnabled(False)
        self.stop_session_signal.emit()

    def _on_quit(self):
        """Sale de la aplicación, emitiendo la señal correspondiente."""
        print("Salir")
        self.quit_session_signal.emit()

    def _volver_config(self):
            """
            Cierra la ventana actual y vuelve a RunConfigurationApp.
            """
            from pyhwr.widgets import RunConfigurationApp  # ajusta si la ruta es distinta

            self.run_config_window = RunConfigurationApp()
            self.run_config_window.show()

            del RunConfigurationApp

            self.close()

    def _copy_bids(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.bids_label.text())

    def _copy_root(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.root_label.text())

    def _toggle_bids_edit(self, state):
        self.bids_label.setReadOnly(not self.changebids_cbox.isChecked())

    def _toggle_root_edit(self, state):
        self.root_label.setReadOnly(not self.changeroot_cbox.isChecked())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    launcher = LauncherApp()
    launcher.show()
    sys.exit(app.exec_())