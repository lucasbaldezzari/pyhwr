import numpy as np
np.set_printoptions(suppress=True)
import matplotlib.pyplot as plt
import seaborn as sns
from pyhwr.managers import LSLDataManager, GHiampDataManager
import pandas as pd

runs = [*range(1,6)]

softLaptop_trialStartTimes = []
softTablet_trialStartTimes = []
softLaptop_trialStartTimesDiff = []
softTablet_trialStartTimesDiff = []
softLaptop_cueDuration = []
softTablet_cueDuration = []
softLaptop_sessionStartTimes = []
softTablet_sessionStartTimes = []

trigLaptop_trialStartTimesDiff = []
trigTablet_trialStartTimesDiff = []
trigLaptop_trialStartTimes = []
trigTablet_trialStartTimes = []
trigLaptop_trialDuration = []
trigTablet_trialDuration = []
trigLaptop_sessionStartTimes = []

for run in runs:
    print(f"Procesando run {run}...")
    path = f"test\\data\\pilot_tests\\subject_0\\no_signals\\s3"
    gtec_filename = f"subject_0_noSignals_s3_r{run}.hdf5"
    lsl_filename = f"sub-subject_0_ses-3_task-Default_run-00{run}_no_signals.xdf"

    lsl_manager = LSLDataManager(path + "\\" + lsl_filename)
    ghiamp_manager = GHiampDataManager(path + "\\" + gtec_filename, normalize_time=True)
    ghiamp_manager.changeMarkersNames({1: "inicioSesión", 2: "trialTablet", 3: "penDown", 4: "trialLaptop"})

    gtec_trialLaptop = np.array(ghiamp_manager["trialLaptop", :]).reshape(-1)
    gtec_trialTablet = np.array(ghiamp_manager["trialTablet", :]).reshape(-1)
    gtec_sessionStart = np.array(ghiamp_manager["inicioSesión", :]).reshape(-1)[0]

    ##los datos de la tablet tienen un dato menos correspondiente al cierre de sesión. Debo corregir esto.
    lsl_trialLaptop = np.array(lsl_manager["Laptop_Markers", "trialStartTime", :]).reshape(-1)
    lsl_trialTablet = np.array(lsl_manager["Tablet_Markers", "trialStartTime", :]).reshape(-1)
    lsl_fadeOffLaptop = np.array(lsl_manager["Laptop_Markers", "trialFadeOffTime", :]).reshape(-1)
    lsl_fadeOffTablet = np.array(lsl_manager["Tablet_Markers", "trialFadeOffTime", :]).reshape(-1)
    lsl_cueTimeLaptop = np.array(lsl_manager["Laptop_Markers", "trialCueTime", :]).reshape(-1)
    lsl_cueTimeTablet = np.array(lsl_manager["Tablet_Markers", "trialCueTime", :]).reshape(-1)
    lsl_sessionStartLaptop = np.array(lsl_manager["Laptop_Markers", "sessionStartTime", :]).reshape(-1)[0]
    lsl_sessionStartTablet = np.array(lsl_manager["Tablet_Markers", "sessionStartTime", :]).reshape(-1)[0]

    ##chequeo que las longitudes de los arrays sean correctas. Sino, quito tantos datos del final como sea necesario en
    ##en base a cual es más corto
    min_len_trials = min(len(lsl_trialLaptop), len(lsl_trialTablet), len(gtec_trialLaptop), len(gtec_trialTablet))
    lsl_trialLaptop = lsl_trialLaptop[:min_len_trials]
    lsl_trialTablet = lsl_trialTablet[:min_len_trials]
    gtec_trialLaptop = gtec_trialLaptop[:min_len_trials]
    gtec_trialTablet = gtec_trialTablet[:min_len_trials]

    min_len_fadeoff = min(len(lsl_fadeOffLaptop), len(lsl_fadeOffTablet))
    lsl_fadeOffLaptop = lsl_fadeOffLaptop[:min_len_fadeoff]
    lsl_fadeOffTablet = lsl_fadeOffTablet[:min_len_fadeoff]

    min_len_cue = min(len(lsl_cueTimeLaptop), len(lsl_cueTimeTablet))
    lsl_cueTimeLaptop = lsl_cueTimeLaptop[:min_len_cue]
    lsl_cueTimeTablet = lsl_cueTimeTablet[:min_len_cue]

    #guardo los tiempos de los trials de laptop
    ##chequeo que gtec_trialLaptop y gtec_trialTablet no sean None
    if gtec_trialLaptop is not None and gtec_trialTablet is not None:
        trigLaptop_trialStartTimes.append(gtec_trialLaptop)
        trigTablet_trialStartTimes.append(gtec_trialTablet)
        trigLaptop_trialStartTimesDiff.append(np.diff(gtec_trialLaptop))
        trigTablet_trialStartTimesDiff.append(np.diff(gtec_trialTablet))
        trigLaptop_sessionStartTimes.append(gtec_sessionStart)

    if lsl_trialLaptop is not None and lsl_trialTablet is not None:
        softLaptop_trialStartTimes.append(lsl_trialLaptop)
        softTablet_trialStartTimes.append(lsl_trialTablet)
        softLaptop_trialStartTimesDiff.append(np.diff(lsl_trialLaptop))
        softTablet_trialStartTimesDiff.append(np.diff(lsl_trialTablet)/1000)#pasa a segundos
        softLaptop_cueDuration.append(np.abs(lsl_fadeOffLaptop - lsl_cueTimeLaptop))
        softTablet_cueDuration.append(np.abs(lsl_fadeOffTablet - lsl_cueTimeTablet)/1000)#pasa a segundos
        softLaptop_sessionStartTimes.append(lsl_sessionStartLaptop)
        softTablet_sessionStartTimes.append(lsl_sessionStartTablet)

#paso a array las listas de trialStartTimes
softLaptop_trialStartTimes = np.array(softLaptop_trialStartTimes)
softTablet_trialStartTimes = np.array(softTablet_trialStartTimes).astype(float)
#si hay algún valor en 0 dentro de softTablet_trialStartTimes, lo cambio por nan para evitar errores en cálculos posteriores
# softTablet_trialStartTimes[softTablet_trialStartTimes == 0] = np.nan
trigLaptop_trialStartTimes = np.array(trigLaptop_trialStartTimes)
trigTablet_trialStartTimes = np.array(trigTablet_trialStartTimes)

#genero diccionarios y almaceno cada lista con un key correspondiente a la sesión
trigLaptop_tst_dict = {run: trigLaptop_trialStartTimesDiff[i] for i, run in enumerate(runs)}
trigTablet_tst_dict = {run: trigTablet_trialStartTimesDiff[i] for i, run in enumerate(runs)}
softLaptop_tst_dict = {run: softLaptop_trialStartTimesDiff[i] for i, run in enumerate(runs)}
softTablet_tst_dict = {run: softTablet_trialStartTimesDiff[i] for i, run in enumerate(runs)}
softLaptop_cd_dict = {run: softLaptop_cueDuration[i] for i, run in enumerate(runs)} #cue duration 
softTablet_cd_dict = {run: softTablet_cueDuration[i] for i, run in enumerate(runs)} #cue duration

##los datos son lista con listas. La idea es convertir todo a un array de numpy de una dimensión
softLaptop_trialStartTimesDiff = np.concatenate(softLaptop_trialStartTimesDiff)/1000
softTablet_trialStartTimesDiff = np.concatenate(softTablet_trialStartTimesDiff)
##si hay algún valor por encima de +20 o  por debajo de -20 reemplazo por nan para evitar errores en cálculos posteriores
softTablet_trialStartTimesDiff[np.abs(softTablet_trialStartTimesDiff) > 20] = np.nan
softLaptop_cueDuration = np.concatenate(softLaptop_cueDuration)/1000
softTablet_cueDuration = np.concatenate(softTablet_cueDuration)

trigLaptop_trialStartTimesDiff = np.concatenate(trigLaptop_trialStartTimesDiff)
trigTablet_trialStartTimesDiff = np.concatenate(trigTablet_trialStartTimesDiff)


### df resumen0
trials_duration_soft = pd.DataFrame({
    "soft_laptop": softLaptop_trialStartTimesDiff,
    "soft_tablet": softTablet_trialStartTimesDiff,
    "diferencias_soft": np.abs(softLaptop_trialStartTimesDiff - softTablet_trialStartTimesDiff)})

##repito para los cues qué solo tengo soft
cue_durations = pd.DataFrame({
    "soft_laptop": softLaptop_cueDuration,
    "soft_tablet": softTablet_cueDuration,
    "diferencias_soft": np.abs(softLaptop_cueDuration - softTablet_cueDuration)
})

trials_duration_trig = pd.DataFrame({
    "trig_laptop": trigLaptop_trialStartTimesDiff,
    "trig_tablet": trigTablet_trialStartTimesDiff,
    "diferencias_trig": np.abs(trigLaptop_trialStartTimesDiff - trigTablet_trialStartTimesDiff)
})

#******** GRAFICOS PARA ANALISIS VISUAL DE DURACIONES DE TRIALS ********#
## Graficos de barras con kde usando seaborn para trials de laptop y tablet en trials_duration_trig


media_laptop_trig = trials_duration_trig["trig_laptop"].mean().round(2).round(2)
media_tablet_trig = trials_duration_trig["trig_tablet"].mean().round(2)
std_laptop_trig = trials_duration_trig["trig_laptop"].std().round(2)
std_tablet_trig = trials_duration_trig["trig_tablet"].std().round(2)
media_diferencias_trig = trials_duration_trig["diferencias_trig"].mean().round(2)
std_diferencias_trig = trials_duration_trig["diferencias_trig"].std().round(2)

plt.figure(figsize=(10, 12))
plt.subplot(3, 1, 1)
sns.histplot(trials_duration_trig["trig_laptop"], kde=True, color="#ffee2f", stat="density",bins=30,
             label=f"laptop: ({media_laptop_trig}, {std_laptop_trig})s")
sns.histplot(trials_duration_trig["trig_tablet"], kde=True, color="#F64040", stat="density",bins=30,
             label=f"tablet: ({media_tablet_trig}, {std_tablet_trig})s")
plt.title('Distribución de Duraciones de Trials (Triggers)')
plt.xlabel('Duración (s)')
plt.ylabel('Densidad')
plt.legend()
##diferencias
plt.subplot(3, 1, 2)
sns.histplot(trials_duration_trig["diferencias_trig"], kde=True, color="#1a53ff", stat="density",bins=30,
             label=f"diff: ({media_diferencias_trig}, {std_diferencias_trig})s")
plt.title('Distribución de Diferencias en Duraciones de Trials (Triggers)')
plt.xlabel('Diferencia de Duración (s)')
plt.ylabel('Densidad')
plt.legend()
##boxplot de trials_duration_trig para laptop y tablet
plt.subplot(3, 1, 3)
sns.boxplot(data=trials_duration_trig[["trig_laptop", "trig_tablet"]], palette=["#ffee2f", "#F64040"])
plt.title('Boxplot de Duraciones de Trials (Triggers)')
plt.ylabel('Duración (s)')
plt.legend()
plt.tight_layout()
plt.show()

##repito para soft
media_laptop_soft = trials_duration_soft["soft_laptop"].mean().round(4)
media_tablet_soft = trials_duration_soft["soft_tablet"].mean().round(4)
std_laptop_soft = trials_duration_soft["soft_laptop"].std().round(4)
std_tablet_soft = trials_duration_soft["soft_tablet"].std().round(4)
media_diferencias_soft = trials_duration_soft["diferencias_soft"].mean().round(4)
std_diferencias_soft = trials_duration_soft["diferencias_soft"].std().round(4)

plt.figure(figsize=(10, 12))
plt.subplot(3, 1, 1)
sns.histplot(trials_duration_soft["soft_laptop"], kde=True, color="#30d8bc", stat="density",bins=30,
             label=f"laptop: ({media_laptop_soft}, {std_laptop_soft})s")
sns.histplot(trials_duration_soft["soft_tablet"], kde=True, color="#1f39ca", stat="density",bins=30,
                label=f"tablet: ({media_tablet_soft}, {std_tablet_soft})s")
plt.title('Distribución de Duraciones de Trials (Software)')
plt.xlabel('Duración (s)')
plt.ylabel('Densidad')
plt.legend()
##diferencias
plt.subplot(3, 1, 2)
sns.histplot(trials_duration_soft["diferencias_soft"], kde=True, color="#3013d8", stat="density",bins=30,
             label=f"diff: ({media_diferencias_soft}, {std_diferencias_soft})s")
plt.title('Distribución de Diferencias en Duraciones de Trials (Software)')
plt.xlabel('Diferencia de Duración (s)')
plt.ylabel('Densidad')
plt.legend()
##boxplot de trials_duration_soft para laptop y tablet
plt.subplot(3, 1, 3)
sns.boxplot(data=trials_duration_soft[["soft_laptop", "soft_tablet"]], palette=["#30d8bc", "#1f39ca"])
plt.title('Boxplot de Duraciones de Trials (Software)')
plt.ylabel('Duración (s)')
plt.legend()
plt.tight_layout()
plt.show()

fig, axes = plt.subplots(2, 5, figsize=(16, 6))
for i, trial in enumerate(list(lsl_manager.trials_info["Tablet_Markers"].keys())[:-11]):
    
    ##grafico las letras usando las coordenadas
    letra = lsl_manager.trials_info["Tablet_Markers"][trial]["letter"]
    coordenadas = np.array(lsl_manager.trials_info["Tablet_Markers"][trial]["coordinates"])
    x,y,t = coordenadas[:,0], coordenadas[:,1], coordenadas[:,2]
    axes[i//5, i%5].plot(x, y, color="#22129d", linewidth = 10, zorder=1)   # Une los puntos en orden
    axes[i//5, i%5].scatter(x, y, color="#ffffff", s=20, zorder = 2)  # Opcional: puntos de muestreo
    # axes[i//5, i%5].set_title(f"Coordenadas de la letra: {letra}")
    axes[i//5, i%5].set_xlabel("X")
    axes[i//5, i%5].set_ylabel("Y")
    axes[i//5, i%5].invert_yaxis()  # Si la tableta tiene origen en la esquina superior izquierda
    #desactivo axis
    axes[i//5, i%5].axis("off")
    axes[i//5, i%5].axis("equal")
plt.show()