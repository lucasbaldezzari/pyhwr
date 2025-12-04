import numpy as np
np.set_printoptions(suppress=True)
import matplotlib.pyplot as plt
# import seaborn as sns
from pyhwr.managers import LSLDataManager, GHiampDataManager
import pandas as pd

path = "test\\data\\pilot_tests\\subject_0\\no_signals\\s3"
gtec_filename = "subject_0_s3_r1.hdf5"
lsl_filename = "sub-subject_0_ses-3_task-Default_run-001_no_signals.xdf"

lsl_manager = LSLDataManager(path + "\\" + lsl_filename)
print("Nombre de los marcadores:", lsl_manager.streamers_names)
print("Nombre de los keys por streamer:", lsl_manager.streamers_keys)
trial = 1
lsl_manager.trials_info["Laptop_Markers"][trial].keys()
letra = lsl_manager.trials_info["Tablet_Markers"][trial]["letter"]
coordenadas = np.array(lsl_manager.trials_info["Tablet_Markers"][trial]["coordinates"])
x,y,t = coordenadas[:,0], coordenadas[:,1], coordenadas[:,2]
t = t - t[0]  # Normalizar tiempo al inicio
##ploteo
plt.figure(figsize=(12, 6))
plt.plot(x, y, color="#35129d", linewidth = 10, zorder=1)   # Une los puntos en orden
plt.scatter(x, y, color="#11aa30", s=20, zorder = 2)  # Opcional: puntos de muestreo
plt.title(f"Coordenadas de la letra: {letra}")
plt.xlabel("X")
plt.ylabel("Y")
plt.gca().invert_yaxis()  # Si la tableta tiene origen en la esquina superior izquierda
plt.axis("equal")
plt.show()

ghiamp_manager = GHiampDataManager(path + "\\" + gtec_filename, normalize_time=True)
##cambio nombre de los marcadores
print("Nombre de los marcadores:", ghiamp_manager.markers_info.keys())
print("Tiempos de los marcadores:", ghiamp_manager.markers_info.values())
ghiamp_manager.changeMarkersNames({1: "inicioSesión", 2: "trialTablet", 3: "penDown", 4: "trialLaptop"})
print(ghiamp_manager.markers_info)