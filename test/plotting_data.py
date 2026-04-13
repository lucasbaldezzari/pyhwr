import os
import numpy as np
from pyhwr.managers import GHiampDataManager, LSLDataManager
import mne

path = "D:\\repos\\pyhwr\\test\\data\\pruebas_piloto\\emgeog"
gtec_filename = "sub-emgeogtrazos_ses-01_task-ejecutada_run-03_emgeog.hdf5"
lsl_filename = "sub-emgeogtrazos_ses-01_task-ejecutada_run-03_emgeog.xdf"

gmanager = GHiampDataManager(os.path.join(path, gtec_filename), normalize_time=True)
lsl_manager = LSLDataManager(os.path.join(path, lsl_filename))

### Gtec
data = gmanager.raw_data.swapaxes(1,0)
# print(data.shape)
print("Nombre de los marcadores:", gmanager.markers_info.keys())
print("Tiempos de los marcadores:", gmanager.markers_info.values())
gmanager.changeMarkersNames({1: "startRun", 2: "trialTablet", 3: "penDown", 4: "trialLaptop"})
t0_gtec = gmanager.markers_info["startRun"][0] #inicio de la ronda marcado por gRecorder usando el trigger de inicio de ronda
markers_info = gmanager.markers_info

trials_tablet = np.array(markers_info["trialTablet"])
trials_laptop = np.array(markers_info["trialLaptop"])
pen_down = np.array(markers_info["penDown"])

##LSL
letras = [lsl_manager.trials_info["Tablet_Markers"][i]["letter"] for i in range(1,len(lsl_manager.trials_info["Tablet_Markers"])+1)]

start_time_tablet = lsl_manager.trials_info["Tablet_Markers"][1]["sessionStartTime"]/1000
##tiempos de inicio de restTime
rest_times = np.array(lsl_manager["Tablet_Markers","trialRestTime",:])/1000 - start_time_tablet
rest_times_relative_gtec = rest_times + t0_gtec #+ 3

##concateno trials_tablet, pen_down y rest_times_relative_gtec y sorteo
times_markers = np.concatenate((trials_tablet, pen_down, rest_times_relative_gtec))
times_markers.sort()

labels = []
for letra, pen, rest in zip(letras, pen_down, rest_times_relative_gtec):
    labels.append(letra)
    labels.append("pd")
    labels.append("rest")

sfreq = gmanager.sample_rate #frecuencia de muestreo del ampli
chanels_names = [f"C{i}" for i in range(1,data.shape[0]+1)]
channels_types = {canal:"eeg" for canal in chanels_names}
info = mne.create_info(chanels_names,sfreq)
raw_signal = mne.io.RawArray(data, info)
times_trialtablet = gmanager.markers_info["trialTablet"]
anotaciones = mne.Annotations(onset = times_markers,
                              duration = [0]*times_markers,
                              description=labels)
raw_signal.set_annotations(anotaciones)
raw_signal.set_channel_types(channels_types)
raw_signal.get_channel_types()
raw_signal.filter(l_freq=5.0, h_freq=30, fir_design='firwin')
raw_signal.notch_filter([50])
raw_signal.plot(scalings=200, duration = 50, start = 242)