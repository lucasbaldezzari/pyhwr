import numpy as np
np.set_printoptions(suppress=True)
import matplotlib.pyplot as plt
import seaborn as sns
from pyhwr.managers import LSLDataManager, GHiampDataManager
import pandas as pd

path = "test\\data\\gtec_recordings\\pilot_tests\\subject_0\\no_signals"
gtec_filename = "subject_0_noSignals2025.11.20_18.59.32.hdf5"
lsl_filename = "sub-subject_0_ses-1_task-Default_run-001_no_signals.xdf"

lsl_manager = LSLDataManager(path + "\\" + lsl_filename)
print("Nombre de los marcadores:", lsl_manager.streamers_names)
print("Nombre de los keys por streamer:", lsl_manager.streamers_keys)
lsl_manager.trials_info["Laptop_Markers"][1].keys()

ghiamp_manager = GHiampDataManager(path + "\\" + gtec_filename, normalize_time=True)
##cambio nombre de los marcadores
print("Nombre de los marcadores:", ghiamp_manager.markers_info.keys())
print("Tiempos de los marcadores:", ghiamp_manager.markers_info.values())
ghiamp_manager.changeMarkersNames({1: "inicioSesión", 2: "trialTablet", 3: "penDown", 4: "trialLaptop"})
print(ghiamp_manager.markers_info)
