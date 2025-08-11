import time
import numpy as np
import keyboard
import logging
from pylsl import local_clock
from pyhwr.utils import SesionInfo
from pyhwr.widgets import SquareWidget
from functools import partial
from PyQt5.QtWidgets import QWidget, QApplication, QVBoxLayout, QLabel, QHBoxLayout
from PyQt5.QtCore import QTimer, Qt
import sys

class SessionManager(QWidget):

    def __init__(self, sesioninfo, mainTimerDuration=5):
        super().__init__()
        self.phases = {
                        "first_jump": {"next": "startSession", "duration": 0.01},
                        "startSession": {"next": "rest", "duration": 5.0},
                        "rest": {"next": "precue", "duration": 2.0},
                        "precue": {"next": "cue", "duration": 1.0},
                        "cue": {"next": "end", "duration": 3.0},
                        "end": {"next": "rest", "duration": 3.0},}
        
        self.in_phase = list(self.phases.keys())[0] # Comienza en la primera fase
        self.sesioninfo = sesioninfo
        self.next_transition = -1

        self.creation_time = local_clock()
        self.accumulated_time = 0
        self._last_phase_time = self.creation_time

        self.mainTimer = QTimer(self)
        self.mainTimer.setInterval(mainTimerDuration) #en milisegundos

        self.mainTimer.timeout.connect(self.update)

        self.initUI()

    def _advance_phase(self):
        """
        Función para avanzar a la siguiente fase
        """
        now = local_clock()
        self.accumulated_time += now - self._last_phase_time
        self._last_phase_time = now

        self.in_phase = self.phases[self.in_phase]["next"]
        self.next_transition = now + self.phases[self.in_phase]["duration"]

    def update(self):
        """
        Método para avanzar de fase solamente cuando se superen los tiempos de cada una.
        """
        now = local_clock()
        if now > self.next_transition:
            self.handle_phase_transition()
            self._advance_phase()
            return True
        return False

    def nextPhase(self):
        """
        Usar este método si se necesita pasar a una nueva fase de manera asíncrona.
        """
        self._advance_phase()

    def moveTo(self, phase_name):
        """
        Método para mover manualmente a una fase específica.
        Útil para situaciones donde se necesita un control más preciso sobre las fases.
        """
        if phase_name in self.phases:
            self.in_phase = phase_name
            self.next_transition = local_clock() + self.phases[phase_name]["duration"]
            self._last_phase_time = local_clock()
        else:
            logging.error(f"Fase '{phase_name}' no encontrada en las fases definidas.")

    def handle_phase_transition(self):
        """
        Aquí podés definir qué hacer en cada fase.
        """
        logging.info(f"Fase actual: {self.in_phase}")
        if self.in_phase == "startSession":
            self.marcador_inicio.change_color("#ffffff")
            self.marcador_cue.change_color("#000000")
            self.marcador_inicio.change_text("")
            self.marcador_cue.change_text("")
        elif self.in_phase == "precue":
            self.marcador_cue.change_color("#000000")
        elif self.in_phase == "cue":
            self.marcador_cue.change_color("#ffffff")
        elif self.in_phase == "end":
            self.marcador_cue.change_color("#000000")

    def get_elapsed_time(self):
        return local_clock() - self.creation_time

    def get_accumulated_time(self):
        return self.accumulated_time
    
    def runSession(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

    def initUI(self):
        """
        Inicializa la interfaz gráfica del gestor de sesión."""
        # Layouts principales
        layout_vertical = QVBoxLayout()
        layout_horizontal = QHBoxLayout()

        # Label principal
        label = QLabel("Presione Enter para iniciar o Escape para salir")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 16px; color: black;")
        layout_vertical.addWidget(label)

        # Widgets de marcadores
        self.marcador_inicio = SquareWidget(x=200, y=200, size=150, color="black",
                                            text="Inicio Sesión", text_color="white")
        self.marcador_cue = SquareWidget(x=400, y=200, size=150, color="black",
                                        text="Cue", text_color="white")
        self.marcador_calibration = SquareWidget(x=800, y=200, size=150, color="white",
                                                text="Para calibrar\nsensores", text_color="black")
        
        # Agregar widgets al layout horizontal        # Aplicar layout
        self.setLayout(layout_vertical)
        self.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            logging.info("Iniciando...")
            self.startSession()
        ##si se presiona Escape, se detiene el test
        elif event.key() == Qt.Key_Escape:
            logging.info("Deteniendo...")
            self.stop()
            app.quit()

    def startSession(self):
        logging.info("Sesión iniciada")
        self.mainTimer.start()

    def stop(self):
        self.mainTimer.stop()
        logging.info("Sesión detenida")
        self.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)  # Configuración básica del logger

    app = QApplication(sys.argv)

    # Ejemplo de uso

    sesion_info = SesionInfo(
        session_id="12345",
        session_name="Test Session",
        session_date=time.strftime("%Y-%m-%d"),
        run_number=1,
        subject_name="Test Subject"
    )

    manager = SessionManager(sesion_info)

    exit_code = app.exec_()
    sys.exit(exit_code)