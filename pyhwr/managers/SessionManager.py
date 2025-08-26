import time
import numpy as np
import logging
from pylsl import local_clock
from pyhwr.managers import TabletMessenger
from pyhwr.utils import SesionInfo
from pyhwr.widgets import SquareWidget
from PyQt5.QtWidgets import QWidget, QApplication, QVBoxLayout, QLabel, QHBoxLayout
from PyQt5.QtCore import QTimer, Qt
import sys

class SessionManager(QWidget):

    def __init__(self, sesioninfo, mainTimerDuration=5,
                 tabid="com.handwriting.ACTION_MSG",
                 runs_per_session=1,
                 letters=None,
                 randomize_per_run=True,
                 seed=None):
        super().__init__()

        self.phases = {
                        "first_jump": {"next": "start", "duration": 0.01},
                        "start": {"next": "fadein", "duration": 3.0},
                        "fadein": {"next": "cue", "duration": 1.0},
                        "cue": {"next": "fadeout", "duration": 5.0},
                        "fadeout": {"next": "rest", "duration": 1.0},
                        "rest": {"next": "trialInfo", "duration": 3.0},
                        "trialInfo": {"next": "start", "duration": 0.1}, #probar luego tiempos más cortos
                    }

        self.in_phase = list(self.phases.keys())[0]
        self.last_phase = ""
        self.session_status = "standby"
        self.sesioninfo = sesioninfo
        self.next_transition = -1

        # --- NUEVO: configuración de sesión/runs/trials/letras ---
        self.letters = letters or ['e', 'a', 'o', 's', 'n', 'r', 'u', 'l', 'd', 't']
        self.trials_per_run = len(self.letters)
        self.runs_per_session = runs_per_session
        self.randomize_per_run = randomize_per_run
        self.rng = np.random.default_rng(seed)
        # estado
        self.current_run = 0            # 0-based
        self.current_trial = -1         # -1 para que al preparar pase a 0
        self.current_letter = None
        self.session_finished = False
        # orden por cada run
        
        self.run_orders = [self._make_run_order() for _ in range(self.runs_per_session)]
        # ----------------------------------------------------------

        self.tabmanager = TabletMessenger(serial="R52W70ATD1W")
        self.tabid = tabid

        self.mainTimer = QTimer(self)
        self.mainTimer.setInterval(mainTimerDuration)
        self.mainTimer.timeout.connect(self.update)

        self.creation_time = local_clock()
        self.accumulated_time = 0
        self._last_phase_time = self.creation_time

        self.initUI()

    def _advance_phase(self):
        """
        Función para avanzar a la siguiente fase
        """
        
        now = local_clock()
        self.accumulated_time += now - self._last_phase_time
        self._last_phase_time = now

        self.last_phase = self.in_phase
        self.in_phase = self.phases[self.in_phase]["next"]
        self.next_transition = now + self.phases[self.in_phase]["duration"]
        logging.info(f"Tiempo de la fase {self.in_phase}: {self.phases[self.in_phase]['duration']} segundos")

    def _prepare_next_trial(self) -> bool:
        """Avanza a (run, trial) siguiente y fija current_letter. False si ya no hay más."""
        if self.session_finished:
            return False

        # ¿Final del trial?
        if self.current_trial + 1 >= self.trials_per_run:
            # pasar al siguiente run
            if self.current_run + 1 >= self.runs_per_session:
                # no hay más runs -> terminamos
                self.session_finished = True
                return False
            self.current_run += 1
            self.current_trial = -1  # para que pase a 0 abajo

        # avanzar al próximo trial dentro del run
        self.current_trial += 1
        self.current_letter = self.run_orders[self.current_run][self.current_trial]
        return True
    
    def _finish_session(self):
        logging.info("Sesión completada. Cerrando.")
        try:
            mensaje = self.tabmanager.make_message(
                "off",
                self.sesioninfo.session_id,       # usa tu session_id
                self.current_run + 1,
                self.sesioninfo.subject_id,
                self.current_trial + 1 if self.current_trial >= 0 else 0,
                "end", "fin", 0.0)
            self.tabmanager.send_message(mensaje, self.tabid)
        except Exception:
            pass
        self.stop()
    
    def update(self):
        """
        Método para avanzar de fase solamente cuando se superen los tiempos de cada una.
        """
        now = local_clock()
        if now > self.next_transition:
            self._advance_phase()
            self.handle_phase_transition()
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
        mensaje = self.tabmanager.make_message(
                "on",
                self.sesioninfo.session_id,
                self.current_run + 1,
                self.sesioninfo.subject_id,
                self.current_trial + 1,
                self.in_phase,
                self.current_letter or "",
                self.phases[self.in_phase]["duration"])
        self.tabmanager.send_message(mensaje, self.tabid)

        if self.in_phase == "start":
            self.marcador_inicio.change_color("#ffffff")
            self.marcador_cue.change_color("#000000")
            self.marcador_inicio.change_text("")
            self.marcador_cue.change_text(f"Trial:{self.current_trial}\nLetra:{self.current_letter}"
                                          or "")
            return
        
        if self.in_phase == "fadein":
            self.marcador_cue.change_color("#000000")
            return
        
        if self.in_phase == "cue":
            self.marcador_cue.change_color("#ffffff")
            return
        
        if self.in_phase == "fadeout":
            self.marcador_cue.change_color("#000000")
            return
        
        if self.in_phase == "rest":
            self.marcador_cue.change_color("#000000")
            logging.debug("Fase rest")
            return
        
        if self.in_phase == "trialInfo":
            logging.debug("Fase trialInfo")
            has_next = self._prepare_next_trial()
            if not has_next:
                self._finish_session()
                return

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
        if not self._prepare_next_trial():
            self._finish_session()
            return
        # salto de  first_jump a start
        self._advance_phase()          # entra a "start"
        self.handle_phase_transition() # envía "start" 1 sola vez
        self.mainTimer.start()

    def stop(self):
        self.mainTimer.stop()
        logging.info("Sesión detenida")
        self.close()

    def _make_run_order(self):
            base = list(self.letters)
            if self.randomize_per_run:
                self.rng.shuffle(base)
            return base

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)  # Configuración básica del logger

    app = QApplication(sys.argv)

    # Ejemplo de uso

    sesion_info = SesionInfo(
        session_id="1",
        run_id="1",
        subject_id="test_subject",
        session_name="Test Session",
        session_date=time.strftime("%Y-%m-%d"),)

    manager = SessionManager(
    sesion_info,
    runs_per_session=2,
    letters=['e'],
    randomize_per_run=True,  # o False si querés siempre el mismo orden
    seed=42)                 # fija el shuffle por reproducibilidad

    exit_code = app.exec_()
    sys.exit(exit_code)