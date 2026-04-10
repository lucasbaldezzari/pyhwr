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
print("Nombre de los marcadores:", gmanager.markers_info.keys())
print("Tiempos de los marcadores:", gmanager.markers_info.values())
gmanager.changeMarkersNames({1: "inicioSesión", 2: "trialTablet", 3: "penDown", 4: "trialLaptop"})
markers_info = gmanager.markers_info

trials_tablet = np.array(markers_info["trialTablet"])
trials_laptop = np.array(markers_info["trialLaptop"])
pen_down = np.array(markers_info["penDown"])

##concateno trials_tablet y pen_down y sorteo
trials_tablet_pen_down = np.concatenate((trials_tablet, pen_down))
trials_tablet_pen_down.sort()

##LSL
letras = [lsl_manager.trials_info["Tablet_Markers"][i]["letter"] for i in range(1,len(lsl_manager.trials_info["Tablet_Markers"])+1)]
##genero una lista que tenga letra, pendown, letra, pen down, etc
letras_pen_down = []
for letra, pen in zip(letras, pen_down):
    letras_pen_down.append(letra)
    letras_pen_down.append("pd")

data = gmanager.raw_data.swapaxes(1,0)
print(data.shape)

len(trials_tablet), len(letras), len(trials_tablet_pen_down), len(letras_pen_down)

sfreq = gmanager.sample_rate #frecuencia de muestreo del ampli
chanels_names = [f"C{i}" for i in range(1,data.shape[0]+1)]
channels_types = {canal:"eeg" for canal in chanels_names}
info = mne.create_info(chanels_names,sfreq)
raw_signal = mne.io.RawArray(data, info)
times_trialtablet = gmanager.markers_info["trialTablet"]
anotaciones = mne.Annotations(onset = trials_tablet_pen_down,
                              duration = [0]*trials_tablet_pen_down,
                              description=letras_pen_down)
raw_signal.set_annotations(anotaciones)
raw_signal.set_channel_types(channels_types)
raw_signal.get_channel_types()
raw_signal.filter(l_freq=5.0, h_freq=30, fir_design='firwin')
raw_signal.notch_filter([50])
raw_signal.plot(scalings=200, duration = 15, start = 242)