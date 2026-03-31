from pyhwr.managers import SessionManager
from pyhwr.utils import SessionInfo
import logging
import sys
import time
from PyQt5.QtWidgets import QApplication
## Configuro el logger para que solo muestre mensajes de error
logging.basicConfig(level=logging.INFO)

##variables/atributos globales
tipo_session = "ejecutada" #baseline, entrenamiento, ejecutada, imaginada
session_number = 1
session_run = 1
n_runs = 1
letters = ['e', 'a', 'o', 's', 'n', 'r', 'u', 'l', 'd', 'm']
session_id = f"{tipo_session}_s{session_number}_r{session_run}_noSignals"
subject_id = "testing"
cue_base_duration = 4.0  # duración base del cue en segundos
cue_tmin = 1.0
cue_tmax = 2.0
rest_base_duration = 1.
rest_tmin = 0.
rest_tmax = 1.
randomize_cue_duration = True
randomize_per_run = True
randomize_rest_duration = True
seed = None

##variables/atributos propios de cada sesión
if tipo_session == "baseline":
    cue_base_duration = 10. #cambio la duración del cue para baseline
    letters = ["a"]
    n_runs = 1
    randomize_per_run = False
    randomize_cue_duration = False
elif tipo_session == "entrenamiento":
    n_runs = 1
    randomize_per_run = False

app = QApplication(sys.argv)

session_info = SessionInfo(
    session_id=session_id,
    subject_id=subject_id,
    session_name=tipo_session,
    session_date=time.strftime("%Y-%m-%d"),)

manager = SessionManager(
session_info,
n_runs = n_runs,
letters = letters,
randomize_per_run = randomize_per_run,
seed = seed,
cue_base_duration = cue_base_duration,
cue_tmin_random = cue_tmin,
cue_tmax_random = cue_tmax,
randomize_cue_duration = randomize_cue_duration,
rest_base_duration=rest_base_duration,
rest_tmin_random=rest_tmin,
rest_tmax_random=rest_tmax,
randomize_rest_duration=True,
tabletID="R52Y50AG4FF"
)

exit_code = app.exec_()
sys.exit(exit_code)

