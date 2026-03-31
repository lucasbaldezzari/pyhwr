import time
import numpy as np
import logging
import json
from pylsl import local_clock
# from pyhwr.managers.TabletMessenger import TabletMessenger
from pyhwr.managers.MarkerManager import MarkerManager
from pyhwr.widgets import SquareWidget, StimuliWindow
from pyhwr.widgets import LauncherApp
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, QObject
import sys

class PreExperimentManager(QObject):

    PHASES = {
        "first_jump": {"next": "start", "duration": 4.},
        "start": {"next": "precue", "duration": 1.0},
        "precue": {"next": "cue", "duration": 0.1},
        "cue": {"next": "rest", "duration": 5.0},
        "rest": {"next": "trialInfo", "duration": 4.0},
        "trialInfo": {"next": "sendMarkers", "duration": 0.1},
        "sendMarkers": {"next": "start", "duration": 0.1},
    }

    def __init__(self, sessioninfo, pre_experiment,
                 mainTimerDuration=50,
                 n_runs=1,
                 randomize_per_run=True,
                 seed=None,
                 cue_base_duration=4.5,
                 cue_tmin_random=1.0,
                 cue_tmax_random=2.0,
                 rest_base_duration = 4,
                 rest_tmin_random = 0.,
                 rest_tmax_random = 1.0,
                 randomize_cue_duration=False,
                 randomize_rest_duration=False,
                 emg_actions = None):
        """
        Gestor de sesión para controlar fases, runs, trials y comunicación con tablet.
        
        Parámetros:
        - sessioninfo: Objeto SessionInfo con detalles de la sesión.
        - pre_experiment: string con el tipo de pre-experimento ("emg", "eog", "basal")
        - mainTimerDuration: Intervalo del timer principal en ms.
        - n_runs: Número de runs en la sesión.
        - actions: Lista de acciones para trials. Si es None, se usa una lista por defecto.
        - randomize_per_run: Si es True, se randomiza el orden de acciones por run.
        - seed: Semilla para el generador de números aleatorios (reproducibilidad).
        - cue_base_duration: Duración base del cue en segundos.
        - cue_tmin: Duración mínima del cue en segundos. Se suma a cue_base_duration.
        - cue_tmax: Duración máxima del cue en segundos. Se suma a cue_base_duration.
        - randomize_cue_duration: Si es True, se randomiza la duración del cue entre cue_tmin y cue_tmax.
        """
        super().__init__()

        self.pre_experiment = pre_experiment.lower()
        self.emg_actions = emg_actions or ["cerrar las manos",
                                           "mover brazos",
                                           "morder y contraer músculos del cuello"]
        
        self.eog_actions = ["cruz_arriba","cruz_abajo","cruz_izquierda","cruz_derecha"]

        self.phases = self.PHASES.copy()

        self.in_phase = list(self.phases.keys())[0]
        self.last_phase = ""
        self.session_status = "standby"
        self.sessioninfo = sessioninfo
        self.next_transition = -1

        # --- configuración de sesión/runs/trials/letras ---
        if self.pre_experiment == "emg":
            self.actions = self.emg_actions

        elif self.pre_experiment == "eog":
            self.actions = self.eog_actions

        elif self.pre_experiment == "basal":
            self.actions = ["basal"]
        else:
            raise ValueError(f"Tipo de pre-experimento '{self.pre_experiment}' no reconocido para actualizar estímulos.")
            

        self.trials_per_run = len(self.actions)
        self.n_runs = n_runs
        self.randomize_per_run = randomize_per_run

        self.current_run = 0
        self.current_trial = -1
        self.current_action = None
        self.session_finished = False

        self.rng = np.random.default_rng(seed) # para reproducibilidad
        self.run_orders = [self._make_run_order() for _ in range(self.n_runs)]

        self.cue_base_duration = cue_base_duration
        self.cue_tmin_random = cue_tmin_random
        self.cue_tmax_random = cue_tmax_random
        self.rest_base_duration = rest_base_duration
        self.rest_tmin_random = rest_tmin_random
        self.rest_tmax_random = rest_tmax_random
        self.randomize_cue_duration = randomize_cue_duration

        if self.randomize_cue_duration:
            self._set_random_cue_duration()
        else:
            self.phases["cue"]["duration"] = self.cue_base_duration

        self.randomize_rest_duration = randomize_rest_duration
        if self.randomize_rest_duration:
            self._set_random_rest_duration()
        else:
            self.phases["rest"]["duration"] = self.rest_base_duration

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
        self.current_action = self.run_orders[self.current_run][self.current_trial]
        return True
    
    def _set_random_cue_duration(self):
        """Asigna una duración aleatoria entre un tmin y tmax segundos al cue."""
        #chequeo que tmin y tmax sean válidos
        if self.cue_tmin_random < 0 or self.cue_tmax_random < 0 or self.cue_tmin_random >= self.cue_tmax_random:
            raise ValueError("Parámetros tmin y tmax inválidos para duración aleatoria del cue.")
        extra = np.random.uniform(self.cue_tmin_random, self.cue_tmax_random)
        self.phases["cue"]["duration"] = self.cue_base_duration + extra
        logging.info(f"Nueva duración del CUE: {self.phases['cue']['duration']:.2f} s")

    def _set_random_rest_duration(self):
        """Asigna una duración aleatoria entre un tmin y tmax segundos al rest time."""
        #chequeo que tmin y tmax sean válidos
        if self.rest_tmin_random < 0 or self.rest_tmax_random < 0 or self.rest_tmin_random >= self.rest_tmax_random:
            raise ValueError("Parámetros tmin y tmax inválidos para duración aleatoria del rest time.")
        extra = np.random.uniform(self.rest_tmin_random, self.rest_tmax_random)
        self.phases["rest"]["duration"] = self.rest_base_duration + extra
        logging.info(f"Nueva duración de REST: {self.phases['rest']['duration']:.2f} s")

    def update_main(self):
        """
        Método para avanzar de fase solamente cuando se superen los tiempos de cada una.
        """
        if self.session_finished:
            return False
        
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
        if self.randomize_rest_duration and self.in_phase == "rest":
            self._set_random_rest_duration()

        # --- Actualizar información común ---
        self.laptop_marker_dict.update({
            "runID": self.current_run + 1,
            "trialID": self.current_trial + 1,
            "letter": self.current_action
        })

        # --- Acciones por fase ---
        phase_actions = {
            "first_jump": self._on_first_jump,
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

        self._update_stimuli()

    def _update_stimuli(self):
        """
        Método para actualizar los estímulos visuales en la ventana
        de estímulos según la fase actual y el tipo de pre-experimento.
        """

        if self.session_finished:
            return

        if self.stimuli_window is None:
            return
        
        if self.in_phase == "first_jump":
            return

        phase = self.in_phase
        action = self.current_action

        ## Ronda EMG
        if self.pre_experiment == "emg":

            if phase == "cue":
                self.stimuli_window.label_orden.setVisible(True)
                self.stimuli_window.cruz.setVisible(False)

                self.stimuli_window.update_order(action)

            else:
                self.stimuli_window.label_orden.setVisible(False)

        ## Ronda EOG
        elif self.pre_experiment == "eog":

            if phase == "cue":
                self.stimuli_window.label_orden.setVisible(False)
                self.stimuli_window.cruz.setVisible(True)

                # mover cruz según acción
                self.stimuli_window.current_state = action
                self.stimuli_window.update_positions()

            else:
                # volver al centro
                self.stimuli_window.current_state = "cruz_centrada"
                self.stimuli_window.update_positions()

        ## Ronda BASAL
        elif self.pre_experiment == "basal":

            self.stimuli_window.label_orden.setVisible(False)
            self.stimuli_window.cruz.setVisible(True)

            self.stimuli_window.current_state = "cruz_centrada"
            self.stimuli_window.update_positions()

        else:
            logging.warning(f"Tipo de pre-experimento '{self.pre_experiment}' no reconocido para actualizar estímulos.")
            ##cerramos app
            self.stopSession()

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
                f"Información de la ronda"
                f"</span><br><br>"

                f"<span style='color:#2200ff; font-style:italic;'>Ronda:</span> "
                f"{self.current_run+1} de {self.n_runs}<br>"

                f"<span style='color:#2200ff; font-style:italic;'>Trial:</span> "
                f"{self.current_trial+1} de {self.trials_per_run}<br>"

                f"<span style='color:#2200ff; font-style:italic;'>Acción actual:</span> "
                f"{self.current_action or '-'}<br><br>"

                f"<span style='color:#2200ff; font-style:italic;'>Duración fase (cue): </span> "
                f"{cue_duration:.2f}s<br><br>"

                f"<span style='color:#2200ff; font-style:italic;'>Tiempo transcurrido:</span> "
                f"{self.get_elapsed_time()/1000:.1f}s"
                f"</div>"
            )

        self.information_label.change_text(texto)

    def _on_first_jump(self):

        if self.stimuli_window:
            self.stimuli_window.label_orden.setVisible(True)
            self.stimuli_window.cruz.setVisible(False)

            self.stimuli_window.update_order(
                "Prepárate...",
                fontsize=48,
                font_color="#ff6600"
            )

            self.stimuli_window.current_state = "orden_centrada"
            self.stimuli_window.update()

    def _send_markers_phase(self):
        """Maneja la fase 'sendMarkers': envía marcadores a tablet y laptop."""
        logging.debug("Fase sendMarkers")

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
    
    def runSession(self):
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

    def initUI(self):
        """
        Inicializa la interfaz gráfica del gestor de sesión."""

        ## Launcher para iniciar el registro
        self.launcher = LauncherApp()
        # -------- Actualizo labels del launcher --------
        self.launcher.update_session_info(
            sub=self.sessioninfo.sub,
            task=self.pre_experiment,
            n_runs=self.n_runs,
            bids_file=self.sessioninfo["bids_file"],
            root_folder=self.sessioninfo["root_folder"],
            ses=self.sessioninfo["ses"],
            run=self.sessioninfo["run"],
        )

        ## Conecto las señales del launcher a los métodos correspondientes
        self.launcher.start_session_signal.connect(self.startSession)
        self.launcher.stop_session_signal.connect(self.stopSession)
        self.launcher.quit_session_signal.connect(self.quitSession)

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
                    f"<b><span style='color:#ffffff;'>INICIO RONDA</span></b><br>"
                f"</div>"
            )
        
        self.marcador_inicio = SquareWidget(x=600, y=650, width=250, height=250, color="black",
                                        text=text, text_color="white")
        
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
        
        self.stimuli_window = StimuliWindow()
        self.stimuli_window.show()
        self.stimuli_window.raise_()
        self.stimuli_window.activateWindow()
        self.launcher.show()

    def stopSession(self):
        logging.info("Parando sesión...")
        self.session_finished = True
        self._show_end_message()
        self.mainTimer.stop()
        self.uiTimer.stop()

    def quitSession(self):
        logging.info("Saliendo de la sesión...")
        self._show_end_message()
        self.mainTimer.stop()
        self.uiTimer.stop()
        self.launcher.close()
        QApplication.quit()

    def startSession(self):
        self.marcador_inicio.change_color("#FFFFFF")
        self.creation_time = time.time()*1000
        t0_abs = time.time()*1000
        self.laptop_marker_dict["sessionStartTime"] = t0_abs
        logging.info("Sesión iniciada")
        if not self._prepare_next_trial():
            self._finish_session()
            return

        # salto de  first_jump a start
        # self._advance_phase()          # entra a "start"
        # self.handle_phase_transition() # envía "start" 1 sola vez
        self.next_transition = time.time() + self.phases[self.in_phase]["duration"]
        self.handle_phase_transition()
        self.mainTimer.start()
        self.uiTimer.start()

    def _finish_session(self):

        self.session_finished = True

        self.laptop_marker_dict["sessionFinalTime"] = time.time()*1000
        self.laptop_marker_dict["letter"] = "fin"
        self.laptop_marker_dict["trialID"] = "fin"

        logging.info("Sesión completada.")

        # detener timers
        self.mainTimer.stop()
        self.uiTimer.stop()

        # mostrar mensaje final
        self._show_end_message()

        # cierre opcional (comentado)
        # QTimer.singleShot(3000, self.stop)

    def _make_run_order(self):
            base = list(self.actions)
            if self.randomize_per_run:
                self.rng.shuffle(base)
            return base
    
    def _show_end_message(self):
        # -------- StimuliWindow --------
        if self.stimuli_window:
            self.stimuli_window.label_orden.setVisible(True)
            self.stimuli_window.cruz.setVisible(False)

            self.stimuli_window.update_order(
                "Podes descansar...",
                fontsize=42,
                font_color="#008000"
            )

            self.stimuli_window.current_state = "orden_centrada"
            self.stimuli_window.repaint()
            self.stimuli_window.update()
            
        # -------- Estado (SquareWidget) --------
        texto = (
            f"<div style='font-size:30px; text-align:center;'>"
            f"<span style='color:#de0000; font-size:34px; font-style:italic; text-decoration:underline;'>"
            f"Información de la ronda"
            f"</span><br><br>"

            f"<span style='color:#2200ff; font-style:italic;'>Ronda:</span> "
            f"{self.current_run+1} de {self.n_runs}<br>"

            f"<span style='color:#2200ff; font-style:italic;'>Acción actual:</span> "
            f"<b>Fin de ronda</b><br><br>"

            f"<span style='color:#2200ff; font-style:italic;'>Tiempo total:</span> "
            f"{self.get_elapsed_time()/1000:.1f}s"
            f"</div>"
        )

        self.information_label.change_text(texto)

if __name__ == "__main__":
    from pyhwr.utils import SessionInfo
    logging.basicConfig(level=logging.INFO)

    app = QApplication(sys.argv)

    ### SessionInfo
    task = "basal"
    bidsf_file = f"sub-01_ses-01_task-{task}_run-01_eeg.bdf"
    session_info = SessionInfo(
    sub = 1,
    ses = 1,
    task = task,
    run = 1,
    suffix = "eeg",
    session_date=time.strftime("%Y-%m-%d"),
    bids_file=bidsf_file,
    )

    manager = PreExperimentManager(
    session_info,
    pre_experiment=task,
    n_runs = 1,
    randomize_per_run = True,  # False para siempre el mismo orden o True caso contrario
    seed = None, # fijo el seed para reproducibilidad
    cue_base_duration = 1.,
    cue_tmin_random = 0.1,
    cue_tmax_random =  0.5,
    randomize_cue_duration = True,
    rest_base_duration=2.,
    rest_tmin_random=0.1,
    rest_tmax_random=1.,
    randomize_rest_duration=True
    )                 

    exit_code = app.exec_()
    sys.exit(exit_code)