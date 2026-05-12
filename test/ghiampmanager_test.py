import os
import numpy as np
from pyhwr.managers import GHiampDataManager

path = "D:\\dataset\\s2"
gtec_filename = "sub-02_ses-01_task-imaginada_run-03_eeg.hdf5"

gmanager = GHiampDataManager(os.path.join(path, gtec_filename), normalize_time=True)

fecha_registro, timestamp_registro = gmanager.fecha_registro, gmanager.timestamp_registro

print("Nombre de los marcadores:", gmanager.markers_info.keys())
print("Tiempos de los marcadores:", gmanager.markers_info.values())
gmanager.changeMarkersNames({1: "inicioSesión", 2: "trialTablet", 3: "penDown", 4: "trialLaptop"})
markers_info = gmanager.markers_info
print(markers_info)

trials_tablet = np.array(markers_info["trialTablet"]) if markers_info.get("trialTablet") else None
trials_laptop = np.array(markers_info["trialLaptop"]) if markers_info.get("trialLaptop") else None
penDown_markers = np.array(markers_info["penDown"]) if markers_info.get("penDown") else None

print(len(trials_tablet)) if trials_tablet is not None else print("No hay triggers de tablet")
print(len(trials_laptop)) if trials_laptop is not None else print("No hay triggers de laptop")
print(len(penDown_markers)) if penDown_markers is not None else print("No hay marcadores de pendown")

if (trials_tablet is not None) and (trials_laptop is not None):
    print(np.abs(trials_tablet-trials_laptop))
    print(np.abs(trials_tablet-trials_laptop).mean()*1000, "ms")
    print(np.abs(trials_tablet-trials_laptop).std()*1000, "ms")