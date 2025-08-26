import pyxdf

path="C:\\Users\\corre\\OneDrive\\Desktop\\test_lab\\sub-P001\\ses-S001\\eeg"
file = "sub-P001_ses-S001_task-Default_run-001_eeg.xdf"

data,header = pyxdf.load_xdf(path + "\\" + file)