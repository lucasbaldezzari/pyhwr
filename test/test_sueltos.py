import numpy as np
np.set_printoptions(suppress=True)
import matplotlib.pyplot as plt
import seaborn as sns
from pyhwr.managers import LSLDataManager, GHiampDataManager
import pandas as pd

file = "test\\markers_test_data\\sueltos\\sub-P001_ses-S003_task-Default_run-001_testeo_timestamp.xdf"

lsl_manager = LSLDataManager(file)

lsl_trialLaptop = np.array(lsl_manager["Laptop_Markers", "trialStartTime", :]).reshape(-1)
lsl_trialTablet = np.array(lsl_manager["Tablet_Markers", "trialStartTime", :]).reshape(-1)
lsl_fadeOffLaptop = np.array(lsl_manager["Laptop_Markers", "trialFadeOffTime", :]).reshape(-1)
lsl_fadeOffTablet = np.array(lsl_manager["Tablet_Markers", "trialFadeOffTime", :]).reshape(-1)
lsl_cueTimeLaptop = np.array(lsl_manager["Laptop_Markers", "trialCueTime", :]).reshape(-1)
lsl_cueTimeTablet = np.array(lsl_manager["Tablet_Markers", "trialCueTime", :]).reshape(-1)
lsl_sessionStartLaptop = np.array(lsl_manager["Laptop_Markers", "sessionStartTime", :]).reshape(-1)[0]
lsl_sessionStartTablet = np.array(lsl_manager["Tablet_Markers", "sessionStartTime", :]).reshape(-1)[0]

min_len_trials = min(len(lsl_trialLaptop), len(lsl_trialTablet))
lsl_trialLaptop = lsl_trialLaptop[:min_len_trials]
lsl_trialTablet = lsl_trialTablet[:min_len_trials]

min_len_fadeoff = min(len(lsl_fadeOffLaptop), len(lsl_fadeOffTablet))
lsl_fadeOffLaptop = lsl_fadeOffLaptop[:min_len_fadeoff]
lsl_fadeOffTablet = lsl_fadeOffTablet[:min_len_fadeoff]

min_len_cue = min(len(lsl_cueTimeLaptop), len(lsl_cueTimeTablet))
lsl_cueTimeLaptop = lsl_cueTimeLaptop[:min_len_cue]
lsl_cueTimeTablet = lsl_cueTimeTablet[:min_len_cue]

lsl_cueTimeLaptop - lsl_cueTimeTablet