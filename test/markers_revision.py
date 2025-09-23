import numpy as np
np.set_printoptions(suppress=True)
import matplotlib.pyplot as plt
import seaborn as sns
from pyhwr.managers import LSLDataManager, GHiampDataManager
import pandas as pd

runs = list(range(1,2))
ghiamp_sfreq = 256.
save = False
show = False

gtec_folder = "test\\markers_test_data\\gtec_recordings\\"
gtec_filetemplate = "full_setup_*.hdf5"
lsl_folder = "test\\markers_test_data\\sub-full_setup\\ses-S00*\\full_setup\\"
lsl_filetemplate = "sub-full_setup_ses-S00*_task-Default_run-001_full_setup.xdf"

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
    gtec_filename = gtec_folder + gtec_filetemplate.replace("*", f"{run}")
    ghiamp_manager = GHiampDataManager(gtec_filename, normalize_time=True, sfreq=ghiamp_sfreq)
    ghiamp_manager.changeMarkersNames({1: "inicioSesión", 2: "trialLaptop", 3: "trialTablet", 4: "penDown"})

    lsl_filename = lsl_folder.replace("*", f"{run}") + lsl_filetemplate.replace("*", f"{run}")
    lsl_manager = LSLDataManager(lsl_filename)

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
softTablet_trialStartTimes = np.array(softTablet_trialStartTimes)
trigLaptop_trialStartTimes = np.array(trigLaptop_trialStartTimes)
trigTablet_trialStartTimes = np.array(trigTablet_trialStartTimes)

##genero un dataframe con los tiempos de inicio de sesión
session_start_times = pd.DataFrame({
    "soft_laptop": softLaptop_sessionStartTimes,
    "soft_tablet": softTablet_sessionStartTimes,
    "trig_laptop": trigLaptop_sessionStartTimes
})

#genero diccionarios y almaceno cada lista con un key correspondiente a la sesión
trigLaptop_tst_dict = {run: trigLaptop_trialStartTimesDiff[i] for i, run in enumerate(runs)}
trigTablet_tst_dict = {run: trigTablet_trialStartTimesDiff[i] for i, run in enumerate(runs)}
softLaptop_tst_dict = {run: softLaptop_trialStartTimesDiff[i] for i, run in enumerate(runs)}
softTablet_tst_dict = {run: softTablet_trialStartTimesDiff[i] for i, run in enumerate(runs)}
softLaptop_cd_dict = {run: softLaptop_cueDuration[i] for i, run in enumerate(runs)}
softTablet_cd_dict = {run: softTablet_cueDuration[i] for i, run in enumerate(runs)}

##los datos son lista con listas. La idea es convertir todo a un array de numpy de una dimensión
softLaptop_trialStartTimesDiff = np.concatenate(softLaptop_trialStartTimesDiff)
softTablet_trialStartTimesDiff = np.concatenate(softTablet_trialStartTimesDiff)
softLaptop_cueDuration = np.concatenate(softLaptop_cueDuration)
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

#guardo los dataframes en test\markers_test_data\csv_data
if save:
    trials_duration_soft.to_csv("test/markers_test_data/csv_data/trials_duration_lsl.csv", index=False)
    cue_durations.to_csv("test/markers_test_data/csv_data/cue_durations_lsl.csv", index=False)
    trials_duration_trig.to_csv("test/markers_test_data/csv_data/trials_duration_trigbox.csv", index=False)

trials_summary_soft = trials_duration_soft.describe()
cue_summary = cue_durations.describe()
trials_summary_trig = trials_duration_trig.describe()

print("Resumen de duración de trials:")
print(trials_summary_soft)
print("Resumen de duración de cues:")
print(cue_summary)
print("Resumen de duración de trials (trig):")
print(trials_summary_trig)

##Gráficos
### ************* GRÁFICOS PARA DURACIÓN DE TRIALS ******************************************
##gráfico de histograma y kde de las columnas laptop_trial_durations y tablet_trial_durations
##duración de trials para lsl
plt.figure(figsize=(12, 6))
sns.histplot(data=trials_duration_soft, x="soft_laptop", kde=True, color="green",
             label=f"Laptop - Media {trials_duration_soft['soft_laptop'].mean():.4f} - std {trials_duration_soft['soft_laptop'].std():.4f}",
             stat="density", bins=60)
sns.histplot(data=trials_duration_soft, x="soft_tablet", kde=True, color="orange",
             label=f"Tablet - Media {trials_duration_soft['soft_tablet'].mean():.4f} - std {trials_duration_soft['soft_tablet'].std():.4f}",
               stat="density", bins=60)
plt.title("Distribución de Duraciones de Trials (LSL)")
plt.xlabel("Duración (s)")
plt.ylabel("Densidad")
plt.legend()
if save:
    plt.savefig("test/markers_test_data/figs/trials_duration_lsl.png")
if show:
    plt.show()

##histograma y kde para diferencias lsl
plt.figure(figsize=(12, 6))
sns.histplot(data=trials_duration_soft, x="diferencias_soft", kde=True, color="#59A4FF",
             label=f"Diferencias - Media {trials_duration_soft['diferencias_soft'].mean():.4f} - std {trials_duration_soft['diferencias_soft'].std():.4f}",
             stat="density", bins=60)
plt.title("Diferencias de duraciones de Trials para laptop vs tablet (LSL)")
plt.xlabel("Duración (s)")
plt.ylabel("Densidad")
plt.legend()
if save:
    plt.savefig("test/markers_test_data/figs/trials_diferencias_lsl.png")
if show:
    plt.show()

##gráfico de cajas de las duraciones de trials para tablet y laptop lsl
plt.figure(figsize=(12, 6))
sns.boxplot(data=trials_duration_soft[["soft_laptop", "soft_tablet"]], palette="Set2")
plt.title("Duraciones de Trials para laptop vs tablet (LSL)")
plt.ylabel("Duración (s)")
if save:
    plt.savefig("test/markers_test_data/figs/trials_boxplot_lsl.png")
if show:
    plt.show()

##grafico de caja para diferencias lsl
plt.figure(figsize=(8, 6))
sns.boxplot(data=trials_duration_soft["diferencias_soft"], color="#59A4FF", showfliers=False)
plt.title("Diferencias de Duraciones de Trials (LSL)")
plt.ylabel("Duración (s)")
if save:
    plt.savefig("test/markers_test_data/figs/trials_diferencias_boxplot_lsl.png")
if show:
    plt.show()


##repito para triggers
##gráfico de histograma y kde de las columnas laptop_trial_durations y tablet_trial_durations
plt.figure(figsize=(12, 6))
sns.histplot(data=trials_duration_trig, x="trig_laptop", kde=True, color="green",
                label=f"Laptop - Media {trials_duration_trig['trig_laptop'].mean():.4f} - std {trials_duration_trig['trig_laptop'].std():.4f}",
                stat="density", bins=60)
sns.histplot(data=trials_duration_trig, x="trig_tablet", kde=True, color="orange",
                label=f"Tablet - Media {trials_duration_trig['trig_tablet'].mean():.4f} - std {trials_duration_trig['trig_tablet'].std():.4f}",
                stat="density", bins=60)
plt.title("Distribución de Duraciones de Trials (Triggers de g.tec)")
plt.xlabel("Duración (s)")
plt.ylabel("Densidad")
plt.legend()
if save:
    plt.savefig("test/markers_test_data/figs/trials_duration_trigbox.png")
if show:
    plt.show()

##histograma y kde para diferencias triggers
plt.figure(figsize=(12, 6))
sns.histplot(data=trials_duration_trig, x="diferencias_trig", kde=True, color="#59A4FF",
                label=f"Diferencias - Media {trials_duration_trig['diferencias_trig'].mean():.4f} - std {trials_duration_trig['diferencias_trig'].std():.4f}",
                stat="density", bins=60)
plt.title("Diferencias de duraciones de Trials para laptop vs tablet (Triggers de g.tec)")
plt.xlabel("Duración (s)")
plt.ylabel("Densidad")
plt.legend()
if save:
    plt.savefig("test/markers_test_data/figs/trials_diferencias_trigbox.png")
if show:
    plt.show()

##gráfico de cajas de las duraciones de trials para tablet y laptop triggers
plt.figure(figsize=(12, 6))
sns.boxplot(data=trials_duration_trig[["trig_laptop", "trig_tablet"]], palette="Set2")
plt.title("Duraciones de Trials para laptop vs tablet (Triggers de g.tec)")
plt.ylabel("Duración (s)")
if save:
    plt.savefig("test/markers_test_data/figs/trials_boxplot_trigbox.png")
if show:
    plt.show()

##grafico de caja para diferencias triggers
plt.figure(figsize=(8, 6))
sns.boxplot(data=trials_duration_trig["diferencias_trig"], color="#59A4FF", showfliers=False)
plt.title("Diferencias de Duraciones de Trials (Triggers de g.tec)")
plt.ylabel("Duración (s)")
if save:
    plt.savefig("test/markers_test_data/figs/trials_diferencias_boxplot_trigbox.png")
if show:
    plt.show()

### ************* GRÁFICOS PARA DURACIÓN DE CUES ******************************************
##histograma y kde lsl
plt.figure(figsize=(12, 6))
sns.histplot(data=cue_durations, x="soft_laptop", kde=True, color="green",
             label=f"Laptop - Media {cue_durations['soft_laptop'].mean():.4f} - std {cue_durations['soft_laptop'].std():.4f}",
             stat="density", bins=40)
sns.histplot(data=cue_durations, x="soft_tablet", kde=True, color="orange",
                label=f"Tablet - Media {cue_durations['soft_tablet'].mean():.4f} - std {cue_durations['soft_tablet'].std():.4f}",
                stat="density", bins=40)
plt.title("Distribución de Duraciones de Cues (LSL)")
plt.xlabel("Duración (s)")
plt.ylabel("Densidad")
plt.legend()
if save:
    plt.savefig("test/markers_test_data/figs/cue_durations_lsl.png")
if show:
    plt.show()

##histograma y kde para diferencias lsl
plt.figure(figsize=(12, 6))
sns.histplot(data=cue_durations, x="diferencias_soft", kde=True,
                label=f"Diferencias - Media {cue_durations['diferencias_soft'].mean():.4f} - std {cue_durations['diferencias_soft'].std():.4f}",
                color="#59A4FF", stat="density", bins=40)
plt.title("Diferencias de duraciones de Cues para laptop vs tablet (LSL)")
plt.xlabel("Duración (s)")
plt.ylabel("Densidad")
plt.legend()
if save:
    plt.savefig("test/markers_test_data/figs/cue_diferencias_lsl.png")
if show:
    plt.show()

