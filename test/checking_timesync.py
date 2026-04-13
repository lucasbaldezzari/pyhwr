import os
import numpy as np
from pyhwr.managers import GHiampDataManager, LSLDataManager

path = "D:\\repos\\pyhwr\\test\\data\\pruebas_piloto\\emgeog"
gtec_filename = "sub-emgeogtrazos_ses-01_task-ejecutada_run-03_emgeog.hdf5"
lsl_filename = "sub-emgeogtrazos_ses-01_task-ejecutada_run-03_emgeog.xdf"

gmanager = GHiampDataManager(os.path.join(path, gtec_filename), normalize_time=True)
gmanager.changeMarkersNames({1: "startRun", 2: "trialTablet", 3: "penDown", 4: "trialLaptop"})
lsl_manager = LSLDataManager(os.path.join(path, lsl_filename))

### ----- Tiempos de inicio de registro ------ ###
_, t_registro_gtec = gmanager.fecha_registro, gmanager.timestamp_registro
_, t_registro_lsl = lsl_manager.fecha_registro, lsl_manager.timestamp_registro
start_time_tablet = lsl_manager.trials_info["Tablet_Markers"][1]["sessionStartTime"]/1000
start_time_laptop = lsl_manager.trials_info["Laptop_Markers"][1]["sessionStartTime"]/1000
## NOTA:Los tiempos start_time_tablet y start_time_laptop son los mismos
## Recordar que los tiempos registrados en la tablet son relativos al inicio de SessionManager

print("Diferencia de tiempo entre inico de registro de gRecorder y LabRecorder:",
      round(t_registro_gtec-t_registro_lsl,2), "s")

print("Diferencia entre inicio de registro en LabRecorder y el inicio de la sesión",
      round(start_time_tablet - t_registro_lsl,2), "s")

delta_gtec_startrun = start_time_tablet - t_registro_gtec
print("Diferencia entre inicio de registro en gRecorder y el inicio de la sesión",
      round(delta_gtec_startrun,2), "s")

###-----------------------------------------------------------------------------------

### ----- Inicio de cada trial para tablet, laptop y gtec ------ ###

## El inicio de la ronda de gtec se marca relativo a cuando se da "record" en gRecorder
t0_gtec = gmanager.markers_info["startRun"][0] #inicio de la ronda marcado por gRecorder usando el trigger de inicio de ronda
ti_trials_tablet_gtec = np.array(gmanager.markers_info["trialTablet"])
ti_trials_tablet_lsl = np.array(lsl_manager["Tablet_Markers","trialStartTime",:])/1000 - start_time_tablet # + t0_gtec + 3
ti_trials_laptop_lsl = np.array(lsl_manager["Laptop_Markers","trialStartTime",:])/1000 - start_time_laptop
## El inico del registro de cada trial de gtec se hace respecto de cuando se inicia a grabar con grecorder

delta_starts = np.abs(t0_gtec - delta_gtec_startrun)
print("La diferencia entre el inicio del run en la tablet y el marcado del evento en gtec es",
      round(delta_starts,3),"segundos")

##NOTA: Es posible hacer que los tiempos registrados para cada trial por la tablet sean relativos
## a los registros realizados por los triggers digitales registrados por gtec.
## Para esto, se debe sumar a los tiempos obtenidos por lsl_manager el t0_gtec más los segundos de start+pre_cue
trials_tablet_relative_gtec = ti_trials_tablet_lsl + t0_gtec + 3
print("Las diferencias temporales entre los triggers digitales y los eventos mostrados en la pantalla de la tablet son:",
      np.round(np.abs(trials_tablet_relative_gtec - ti_trials_tablet_gtec),3),"seg")
print("Valor medio:", np.round(np.abs(trials_tablet_relative_gtec - ti_trials_tablet_gtec),3).mean())
print("Std:", np.round(trials_tablet_relative_gtec - ti_trials_tablet_gtec,3).std())

##Esta diferencia se puede atribuir al delay que hay entre lo que detecta el sensor y el registro
##del evento en el g.HIAMP dado por el g.Trigbox

###-----------------------------------------------------------------------------------