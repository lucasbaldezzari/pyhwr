import os
import numpy as np
from pyhwr.managers import GHiampDataManager

path = "D:\\repos\\pyhwr\\test\\data\\gtec_recordings\\full_steup"
lsl_filename = "full_setup_2.hdf5"

gmanager = GHiampDataManager(os.path.join(path, lsl_filename), normalize_time=True)

print("Nombre de los marcadores:", gmanager.markers_info.keys())
print("Tiempos de los marcadores:", gmanager.markers_info.values())
gmanager.changeMarkersNames({1: "inicioSesión", 2: "trialTablet", 3: "penDown", 4: "trialLaptop"})
markers_info = gmanager.markers_info

trials_tablet = np.array(markers_info["trialTablet"])
trials_laptop = np.array(markers_info["trialLaptop"])