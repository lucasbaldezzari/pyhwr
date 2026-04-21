import os
from pyhwr.managers import LSLDataManager
import numpy as np

path = "test\\data\\pruebas_piloto\\emgeog\\"
lsl_filename = "sub-emgeogtrazos_ses-01_task-ejecutada_run-01_emgeog.xdf"

lsl_manager = LSLDataManager(os.path.join(path, lsl_filename))

print(lsl_manager.streamers_names)
fecha_registro, timestamp_registro = lsl_manager.fecha_registro, lsl_manager.timestamp_registro
start_time_tablet = lsl_manager.trials_info["Tablet_Markers"][1]["sessionStartTime"]/1000
start_time_laptop = lsl_manager.trials_info["Laptop_Markers"][1]["sessionStartTime"]/1000
print(lsl_manager.describe_trials())  
print(lsl_manager.pendown_delays)
print(lsl_manager.penDown_delays_resume())
print(lsl_manager.traces_duration)
print(lsl_manager.tracesDuration_resume())
lsl_manager.coordinates_info[1]["letter"] #"coordinates" o "letter"
lsl_manager.getTrialCoordinates(2)
np.array(lsl_manager.coordinates_info[1]["coordinates"])[0,2]

lsl_manager.trialsTimes()

lsl_manager.lettersTrials("a")    
lsl_manager.infoTrial(20)

fig, axes = lsl_manager.plot_traces(7,line_color = "#12259d", show=False)
# fig.show()
# del fig, axes
fig, axes = lsl_manager.plot_all_traces(figsize=(25, 10),
                                        line_color = "#040508", point_color="#ffffff", point_size=5,
                                        hide_title=True, hide_axes=True, hide_ticks=True,
                                        hide_labels=True, hide_spines=True, show=False)
fig.show()
del fig, axes


import numpy as np

from biosignals.info.info import Info
from biosignals.signals.raw import RawSignal

data = np.random.randn(3, 1000)
info = Info(
ch_names=["C3", "Cz", "C4"],
ch_types=["eeg", "eeg", "eeg"],
sfreq=250,
)
raw = RawSignal(data=data, info=info)
out = raw.get_data()

assert out.shape == (3, 1000)


data = np.random.randn(3, 1000)
info = Info(
ch_names=["C3", "Cz", "C4"],
ch_types=["eeg", "eeg", "eeg"],
sfreq=250,
)
raw = RawSignal(data=data, info=info)
raw.drop_channels(["Cz"])

assert raw.info["ch_names"] == ["C3", "C4"]
assert raw.get_data().shape == (2, 1000)