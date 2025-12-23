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
session_run = 5
letters = ['e', 'a', 'o', 's', 'n', 'r', 'u', 'l', 'd','t'] #['e', 'a', 'o', 's', 'n', 'r', 'u', 'l', 'd','t']
n_runs = 2
session_id = f"{tipo_session}_s{session_number}_r{session_run}_noSignals"
subject_id = "piloto2"
cue_base_duration = 5.0  # duración base del cue en segundos
cue_tmin = 1.0
cue_tmax = 2.0
randomize_cue_duration = True
randomize_per_run = True
seed = None

##variables/atributos propios de cada sesión
if tipo_session == "baseline":
    cue_base_duration = 60. #cambio la duración del cue para baseline
    letters = ["ta"]
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
tabletID="R52Y50AG4FF"
)

exit_code = app.exec_()
sys.exit(exit_code)

