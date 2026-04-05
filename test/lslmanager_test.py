import os
from pyhwr.managers import LSLDataManager

path = "test\\data\\pruebas_piloto\\testeo_marcadores\\"
lsl_filename = "sub-test_eventos_ses-test_eventos_task-ejecutada_run-01_eeg.xdf"

lsl_manager = LSLDataManager(os.path.join(path, lsl_filename))

print(lsl_manager.streamers_names)
print(lsl_manager.describe_trials())  
print(lsl_manager.pendown_delays)
lsl_manager.coordinates_info[1]["letter"] #"coordinates" o "letter"
lsl_manager.getTrialCoordinates(2)

lsl_manager.trialsTimes()

lsl_manager.lettersTrials("a")    
lsl_manager.infoTrial(40)

# fig, axes = lsl_manager.plot_traces(2,line_color = "#12259d", show=False)
# fig.show()
# del fig, axes
fig, axes = lsl_manager.plot_all_traces(figsize=(25, 10),
                                        line_color = "#12259d", point_color="#ffffff", point_size=5,
                                        hide_title=True, hide_axes=True, hide_ticks=True,
                                        hide_labels=True, hide_spines=True, show=False)
fig.show()
del fig, axes