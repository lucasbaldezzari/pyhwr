import time
import numpy as np
import logging
import json
from pylsl import local_clock
from pyhwr.managers.TabletMessenger import TabletMessenger
from pyhwr.managers.MarkerManager import MarkerManager
from pyhwr.widgets import SquareWidget
from PyQt5.QtWidgets import QWidget, QApplication, QVBoxLayout, QLabel, QHBoxLayout
from PyQt5.QtCore import QTimer, Qt
import sys

class SessionManager(QWidget):

    PHASES = {
        "first_jump": {"next": "start", "duration": 0.1},
        "start": {"next": "precue", "duration": 3.0},
        "precue": {"next": "cue", "duration": 1.0},
        "cue": {"next": "fadeoff", "duration": 5.0},
        "fadeoff": {"next": "rest", "duration": 1.0},
        "rest": {"next": "trialInfo", "duration": 3.0},
        "trialInfo": {"next": "sendMarkers", "duration": 0.5},
        "sendMarkers": {"next": "start", "duration": 0.2},
    }

    def __init__(self, sessioninfo, mainTimerDuration=50,
                 tabid="com.handwriting.ACTION_MSG",
                 n_runs=1,
                 letters=None,
                 randomize_per_run=True,
                 seed=None,
                 cue_base_duration=4.5,
                 cue_tmin_random=1.0,
                 cue_tmax_random=2.0,
                 randomize_cue_duration=True):
        """
        Gestor de sesión para controlar fases, runs, trials y comunicación con tablet.
        
        Parámetros:
        - sessioninfo: Objeto SessionInfo con detalles de la sesión.
        - mainTimerDuration: Intervalo del timer principal en ms.
        - tabid: ID de la aplicación de la tablet para mensajes.
        - n_runs: Número de runs en la sesión.
        - letters: Lista de letras para trials. Si es None, se usa una lista por defecto.
        - randomize_per_run: Si es True, se randomiza el orden de letras por run.
        - seed: Semilla para el generador de números aleatorios (reproducibilidad).
        - cue_base_duration: Duración base del cue en segundos.
        - cue_tmin: Duración mínima del cue en segundos. Se suma a cue_base_duration.
        - cue_tmax: Duración máxima del cue en segundos. Se suma a cue_base_duration.
        - randomize_cue_duration: Si es True, se randomiza la duración del cue entre cue_tmin y cue_tmax.
        """
        super().__init__()

        self.phases = self.PHASES.copy()

        self.in_phase = list(self.phases.keys())[0]
        self.last_phase = ""
        self.session_status = "standby"
        self.sessioninfo = sessioninfo
        self.next_transition = -1

        # --- configuración de sesión/runs/trials/letras ---
        self.letters = letters or ['e', 'a', 'o', 's', 'n', 'r', 'u', 'l', 'd','t']
        self.trials_per_run = len(self.letters)
        self.n_runs = n_runs
        self.randomize_per_run = randomize_per_run

        self.current_run = 0
        self.current_trial = -1
        self.current_letter = None
        self.session_finished = False

        self.rng = np.random.default_rng(seed) # para reproducibilidad
        self.run_orders = [self._make_run_order() for _ in range(self.n_runs)]

        self.cue_base_duration = cue_base_duration
        self.cue_tmin_random = cue_tmin_random
        self.cue_tmax_random = cue_tmax_random
        self.randomize_cue_duration = randomize_cue_duration
        if self.randomize_cue_duration:
            self._set_random_cue_duration()
        else:
            self.phases["cue"]["duration"] = self.cue_base_duration

        # ----------------------------------------------------------
        # Objeto para enviar mensajes a la tablet
        self.tabmanager = TabletMessenger(serial="R52W70ATD1W")
        self.tabid = tabid

        # ----------------------------------------------------------
        # Atributos para control del main
        self.mainTimer = QTimer(self)
        self.mainTimer.setInterval(mainTimerDuration)
        self.mainTimer.timeout.connect(self.update_main)

        # Timer para actualizar interfaz de usuario
        self.uiTimer = QTimer(self)
        self.uiTimer.setInterval(100)  # 100ms
        self.uiTimer.timeout.connect(self._update_information_label)

        # ----------------------------------------------------------
        # Atributos temporales
        self.creation_time = False #time.time()*1000
        self.accumulated_time = 0
        self._last_phase_time = self.creation_time
        self.sessionStartTime = None #variable para guardar el tiempo que comienza la sesión
        self.trialStartTime = None #varibale para guardar el momento en que inicia el trial
        self.precueTime = None #variable para indicar el momento en que inicia el precue
        self.trialCueTime = None #variable para indicar el inicio del cue
        self.trialFadeOffTime = None #variable para indicar el momento en que inicia el FadeLOut
        self.trialRestTime = None #variable para indicar el momento en que inicia el período rest
        self.sessionFinalTime = None #variable para guardar el momento en que finaliza la sessión

        # --------------------------------------------------------
        # Marcadores de eventos de tablet
        self.laptop_marker = MarkerManager(stream_name="Laptop_Markers",
                                            stream_type="Markers",
                                            source_id="Laptop",
                                            channel_count=1,
                                            channel_format="string",
                                            nominal_srate=0)
        
        self.laptop_marker_dict = dict(trialID="", letter="", runID="",
                                   sessionStartTime=0.0, trialStartTime=0.0,
                                   trialPrecueTime=0.0, trialCueTime=0.0,
                                   trialFadeOffTime=0.0, trialRestTime=0.0,
                                   sessionFinalTime=0.0,)

        # --------------------------------------------------------
        # Marcadores de eventos de tablet
        self.tablet_marker = MarkerManager(stream_name="Tablet_Markers",
                                            stream_type="Markers",
                                            source_id="Tablet",
                                            channel_count=1,
                                            channel_format="string",
                                            nominal_srate=0)

        self.initUI()

    def _advance_phase(self):
        """
        Función para avanzar a la siguiente fase
        """
        
        now = time.time() #local_clock()
        # self.accumulated_time += now - self._last_phase_time
        self._last_phase_time = now

        self.last_phase = self.in_phase
        self.in_phase = self.phases[self.in_phase]["next"]
        self.next_transition = now + self.phases[self.in_phase]["duration"]
        logging.info(f"Tiempo de la fase {self.in_phase}: {self.phases[self.in_phase]['duration']} seg")

    def _prepare_next_trial(self) -> bool:
        """Avanza a (run, trial) siguiente y fija current_letter. False si ya no hay más."""
        if self.session_finished:
            return False

        # ¿Final del trial?
        if self.current_trial + 1 >= self.trials_per_run:
            # pasar al siguiente run
            if self.current_run + 1 >= self.n_runs:
                # no hay más runs -> terminamos
                self.session_finished = True
                return False
            self.current_run += 1
            self.current_trial = -1  # para que pase a 0 abajo

        # avanzar al próximo trial dentro del run
        self.current_trial += 1
        self.current_letter = self.run_orders[self.current_run][self.current_trial]
        return True
    
    def _set_random_cue_duration(self):
        """Asigna una duración aleatoria entre 5 y 6 segundos al cue."""
        # base = 5.0
        #chequeo que tmin y tmax sean válidos
        if self.cue_tmin_random < 0 or self.cue_tmax_random < 0 or self.cue_tmin_random >= self.cue_tmax_random:
            raise ValueError("Parámetros tmin y tmax inválidos para duración aleatoria del cue.")
        extra = np.random.uniform(self.cue_tmin_random, self.cue_tmax_random)
        self.phases["cue"]["duration"] = self.cue_base_duration + extra
        logging.info(f"Nueva duración del CUE: {self.phases['cue']['duration']:.2f} s")

    def update_main(self):
        """
        Método para avanzar de fase solamente cuando se superen los tiempos de cada una.
        """
        now = time.time()#local_clock()
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
            self._last_phase_time = local_clock()
            self.next_transition = local_clock() + self.phases[phase_name]["duration"]
        else:
            logging.error(f"Fase '{phase_name}' no encontrada en las fases definidas.")

    def handle_phase_transition(self):
        logging.info(f"Fase actual: {self.in_phase}")
        if self.randomize_cue_duration and self.in_phase == "cue":
            self._set_random_cue_duration()

        # --- Enviar mensaje a tablet ---
        mensaje = self.tabmanager.make_message(
            "on",
            self.sessioninfo.session_id,
            self.current_run + 1,
            self.sessioninfo.subject_id,
            self.current_trial + 1,
            self.in_phase,
            self.current_letter or "",
            self.phases[self.in_phase]["duration"])
        self.tabmanager.send_message(mensaje, self.tabid)

        # --- Actualizar información común ---
        self.laptop_marker_dict.update({
            "runID": self.current_run + 1,
            "trialID": self.current_trial + 1,
            "letter": self.current_letter
        })

        # --- Acciones por fase ---
        phase_actions = {
            "start": lambda: self._on_phase("trialStartTime", "#000000"),
            "precue": lambda: self._on_phase("trialPrecueTime", "#000000"),
            "cue": lambda: self._on_phase("trialCueTime", "#ffffff"),
            "fadeoff": lambda: self._on_phase("trialFadeOffTime", "#000000"),
            "rest": lambda: self._on_phase("trialRestTime", "#000000", log="Fase rest"),
            "trialInfo": lambda: logging.debug("Fase trialInfo"),
            "sendMarkers": self._send_markers_phase
        }

        action = phase_actions.get(self.in_phase)
        if action:
            action()

    def _on_phase(self, time_key, color, extra_action=None, log=None):
        """Aplica color, guarda tiempo y ejecuta acción opcional.
        
        Parámetros:
        - time_key: Clave en laptop_marker_dict para guardar el tiempo.
        - color: Color para el marcador visual.
        - extra_action: Función opcional a ejecutar.
        - log: Mensaje de log opcional.
        """
        self.laptop_marker_dict[time_key] = time.time() * 1000
        self.marcador_cue.change_color(color)
        if log:
            logging.debug(log)
        if extra_action:
            extra_action()

    def _update_information_label(self):
        """Actualiza continuamente el tiempo de sesión mostrado (cada 100 ms)."""
        if not self.creation_time:
            return  # aún no comenzó la sesión

        # {self.in_phase}: {self.phases[self.in_phase]['duration']} seg")
        if self.in_phase == "cue":
            cue_duration = self.phases[self.in_phase]['duration']
        else:
            cue_duration = 0.00
        texto = (
                f"<div style='font-size:30px; text-align:center;'>"
                f"<span style='color:#de0000; font-size:34px; font-style:italic; text-decoration:underline;'>"
                f"Información del Bloque"
                f"</span><br><br>"

                f"<span style='color:#2200ff; font-style:italic;'>Run:</span> "
                f"{self.current_run+1} de {self.n_runs}<br>"

                f"<span style='color:#2200ff; font-style:italic;'>Trial:</span> "
                f"{self.current_trial+1} de {self.trials_per_run}<br>"

                f"<span style='color:#2200ff; font-style:italic;'>Letra actual:</span> "
                f"{self.current_letter or '-'}<br><br>"

                f"<span style='color:#2200ff; font-style:italic;'>Duración fase (cue): </span> "
                f"{cue_duration:.2f}s<br><br>"

                f"<span style='color:#2200ff; font-style:italic;'>Tiempo transcurrido:</span> "
                f"{self.get_elapsed_time()/1000:.1f}s"
                f"</div>"
            )

        self.information_label.change_text(texto)

    def _send_markers_phase(self):
        """Maneja la fase 'sendMarkers': envía marcadores a tablet y laptop."""
        logging.debug("Fase sendMarkers")

        # --- Leer datos del trial desde la tablet ---
        try:
            tab_trial_data = self.tabmanager.read_trial_json(
                subject=self.sessioninfo.subject_id,
                session=self.sessioninfo.session_id,
                run=self.current_run + 1,
                trial_id=self.current_trial + 1
            )
            logging.debug("Marcadores de Tablet:")
            logging.debug(tab_trial_data)
            self.tablet_marker.sendMarker(tab_trial_data)
        except Exception as e:
            logging.error(f"Error al leer marcadores de la tablet: {e}")

        # --- Enviar marcadores de laptop ---
        try:
            laptop_markers_msg = json.dumps(self.laptop_marker_dict)
            logging.debug("Marcadores de Laptop:")
            logging.debug(self.laptop_marker_dict)
            self.laptop_marker.sendMarker(laptop_markers_msg)
        except Exception as e:
            logging.error(f"Error al enviar marcadores de laptop: {e}")

        # --- Preparar el siguiente trial ---
        has_next = self._prepare_next_trial()
        if not has_next:
            self._finish_session()

    def get_elapsed_time(self):
        return (time.time() * 1000) - self.creation_time

    # def get_accumulated_time(self):
    #     return self.accumulated_time
    
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
        text = (
                f"<div style='font-size:34px; text-align:center;'>"
                    f"<b><span style='color:#2200ff;'>INFORMACIÓN DE LA SESIÓN</span></b><br>"
                f"</div>"
            )

        self.information_label = SquareWidget(x=200, y=200, width=650, height=400, color="#ebebeb",
                                              text = text)
        
        text = (
                f"<div style='font-size:24px; text-align:center;'>"
                    f"<b><span style='color:#ffffff;'>CUE</span></b><br>"
                f"</div>"
            )
        
        self.marcador_cue = SquareWidget(x=200, y=650, width=250, height=250, color="black",
                                        text=text, text_color="white")
        
        text = (
                f"<div style='font-size:24px; text-align:center;'>"
                    f"<b><span style='color:#000000;'>Para calibrar\nsensores</span></b><br>"
                f"</div>"
            )
        
        self.marcador_calibration = SquareWidget(x=200, y=950 , width=250, height=250, color="white",
                                                text=text, text_color="black")
        
        # Agregar widgets al layout horizontal        # Aplicar layout
        self.setLayout(layout_vertical)
        self.show()

    def keyPressEvent(self, event):
        """Maneja las teclas Enter (inicia) y Escape (detiene la sesión)."""
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            logging.info("Iniciando...")
            self.startSession()
        elif event.key() == Qt.Key_Escape:
            logging.info("Deteniendo...")
            self.stop()
            QApplication.quit()

    def startSession(self):
        self.creation_time = time.time()*1000
        t0_abs = time.time()*1000
        self.laptop_marker_dict["sessionStartTime"] = t0_abs
        logging.info("Sesión iniciada")
        if not self._prepare_next_trial():
            self._finish_session()
            return
        ##envío mensaje a la tablet para avisar el inicio de la sesión

        mensaje = self.tabmanager.make_message(
                "on",
                self.sessioninfo.session_id,
                self.current_run + 1,
                self.sessioninfo.subject_id,
                self.current_trial + 1,
                self.in_phase,
                self.current_letter or "",
                self.phases[self.in_phase]["duration"],
                sessionStartTime = t0_abs
                )
        
        self.tabmanager.send_message(mensaje, self.tabid)

        # salto de  first_jump a start
        self._advance_phase()          # entra a "start"
        self.handle_phase_transition() # envía "start" 1 sola vez
        self.mainTimer.start()
        self.uiTimer.start()

    def _finish_session(self):
        """
        Función para finalizar la sesión.
        """
        self.laptop_marker_dict["sessionFinalTime"] = time.time()*1000
        self.laptop_marker_dict["letter"] = "fin" #se replica lo que se hace en la tablet
        self.laptop_marker_dict["trialID"] = "fin"
        logging.info("Sesión completada. Cerrando.")


        ##IMPORTANTE: Si se quisiera enviar los marcadores de laptop al finalizar la sesión,
        ##se debe descomentar el bloque siguiente

        # Mensaje a labrecorder con los marcadores de laptop
        # laptop_markers_msg = json.dumps(self.laptop_marker_dict)
        # self.laptop_marker.sendMarker(laptop_markers_msg)

        ## ---***** El siguiente bloque de try-except debe enviarse si se quiere avisar
        ## a la tablet que el bloque ha finalizado *****---
        try:
            #envío mensaje a la tablet para avisar el final de la sesión
            #la tablet recibe y guarda el tiempo en que cierra la app
            mensaje = self.tabmanager.make_message(
                "final",
                self.sessioninfo.session_id,
                "final",
                self.sessioninfo.subject_id,
                0,
                "final", "fin", self.get_elapsed_time()/1000)
            self.tabmanager.send_message(mensaje, self.tabid)
        except Exception:
            logging.error("No se pudo enviar mensaje de final de sesión")

        ##IMPORTANTE: Si se quisiera leer y enviar el último JSON de la tablet,
        ##se debe descomentar el bloque siguiente
            
        # final_json = self._read_final_with_retry(
        #     subject=self.sessioninfo.subject_id,
        #     session=self.sessioninfo.session_id,
        #     timeout=5.0,
        #     interval=0.5)

        # if final_json is None:
        #     logging.error("No se pudo leer el JSON final desde la tablet dentro del timeout.")
        # else:
        #     # reenviá por LSL el JSON final de tablet
        #     logging.debug("JSON final de la tablet:")
        #     logging.debug(final_json)
        #     # self.tablet_marker.sendMarker(final_json)

        logging.info(f"Tiempo total de sesión: {self.get_elapsed_time()/1000:.2f} s")
        self.stop()

    def _read_final_with_retry(self, subject, session, timeout=3.0, interval=0.1):
        """Intenta leer el último JSON de la tablet con reintentos exponenciales."""
        t0 = time.time()
        wait = interval
        while time.time() - t0 < timeout:
            try:
                return self.tabmanager.read_trial_json(
                    subject=subject, session=session, run="final", trial_id=0)
            except Exception:
                time.sleep(wait)
                wait = min(wait * 1.5, 0.5)
        return None

    def stop(self):
        self.mainTimer.stop()
        self.uiTimer.stop()
        logging.info("Sesión detenida")
        self.close()

    def _make_run_order(self):
            base = list(self.letters)
            if self.randomize_per_run:
                self.rng.shuffle(base)
            return base

if __name__ == "__main__":
    from pyhwr.utils import SessionInfo
    logging.basicConfig(level=logging.ERROR)

    app = QApplication(sys.argv)

    session_info = SessionInfo(
        session_id="1",
        subject_id="test_v0.0.5",
        session_name="test_v0.0.5",
        session_date=time.strftime("%Y-%m-%d"),)

    manager = SessionManager(
    session_info,
    n_runs = 1,
    letters = ["ta","a","ta","n","ta"],#None,
    randomize_per_run = True,  # False para siempre el mismo orden o True caso contrario
    seed = None, # fijo el seed para reproducibilidad
    cue_base_duration = 6.,
    cue_tmin_random = 1.0,
    cue_tmax_random = 2.5,
    randomize_cue_duration = True,
    )                 

    exit_code = app.exec_()
    sys.exit(exit_code)