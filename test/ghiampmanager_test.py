import os
import numpy as np
from pyhwr.managers import GHiampDataManager

path = "test\\data\\pruebas_piloto\\emgeog\\"
gtec_filename = "sub-emgeogtrazos_ses-01_task-ejecutada_run-01_emgeog.hdf5"

gmanager = GHiampDataManager(os.path.join(path, gtec_filename), normalize_time=True)

fecha_registro, timestamp_registro = gmanager.fecha_registro, gmanager.timestamp_registro

print("Nombre de los marcadores:", gmanager.markers_info.keys())
print("Tiempos de los marcadores:", gmanager.markers_info.values())
gmanager.changeMarkersNames({1: "inicioSesión", 2: "trialTablet", 3: "penDown", 4: "trialLaptop"})
markers_info = gmanager.markers_info

trials_tablet = np.array(markers_info["trialTablet"])
trials_laptop = np.array(markers_info["trialLaptop"])

print(np.abs(trials_tablet-trials_laptop))
print(np.abs(trials_tablet-trials_laptop).mean()*1000, "ms")
print(np.abs(trials_tablet-trials_laptop).std()*1000, "ms")