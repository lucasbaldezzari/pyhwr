import sys
from PyQt5.QtWidgets import QApplication

# Importa tus ventanas
from pyhwr.widgets import InitAPP
from pyhwr.widgets import RunConfigurationApp


class AppManager:
    def __init__(self):
        # Crear QApplication (UNA sola en toda la app)
        self.app = QApplication(sys.argv)

        # Referencias a ventanas
        self.init_window = None
        self.configuration_window = None

    # -----------------------------
    # START APP
    # -----------------------------
    def start(self):
        self.init_window = InitAPP()

        # Inyectar referencia del manager en la ventana
        self.init_window.manager = self

        self.init_window.show()
        sys.exit(self.app.exec_())

    # -----------------------------
    # TRANSICIÓN: Init → Launcher
    # -----------------------------
    def start_configurator(self, config: dict):
        """
        Recibe el diccionario de parámetros desde InitAPP
        y lanza RunConfigurationApp
        """

        # Crear launcher con config
        self.configuration_window = RunConfigurationApp(config)

        # Mostrar launcher
        self.configuration_window.show()

        # Cerrar init (si existe)
        if self.init_window is not None:
            self.init_window.close()
            self.init_window = None

    # -----------------------------
    # OPCIONAL: volver a InitAPP
    # -----------------------------
    def restart_init(self):
        self.init_window = InitAPP()
        self.init_window.manager = self
        self.init_window.show()

        if self.configuration_window is not None:
            self.configuration_window.close()
            self.configuration_window = None


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    manager = AppManager()
    manager.start()