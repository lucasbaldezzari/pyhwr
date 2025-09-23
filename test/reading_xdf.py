import pyxdf
import json
import numpy as np
import matplotlib.pyplot as plt

def parse_trial_message(raw):
    # 1) Si viene como bytes (a veces pasa con sockets/LSL)
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    # 2) Limpieza simple
    raw = raw.strip()
    # 3) Si por logging quedó envuelto en comillas, las quitamos (solo las exteriores)
    if raw and raw[0] in "\"'" and raw[-1] == raw[0]:
        raw = raw[1:-1]
    # 4) Parseo JSON → dict
    return json.loads(raw)

path="C:\\Users\\corre\\OneDrive\\Desktop\\test_lab\\sub-full_setup\\ses-S006\\full_setup"
file = "sub-full_setup_ses-S006_task-Default_run-001_full_setup.xdf"

data,header = pyxdf.load_xdf(path + "\\" + file)

trial_data = data[1]["time_series"][0][0]
parsed_trial_data = parse_trial_message(trial_data)
# print(parsed_trial_data.keys())
sessionStartTime = parsed_trial_data["sessionStartTime"]
sessionFinalTime = parsed_trial_data["sessionFinalTime"]
trialStartTime = parsed_trial_data["trialStartTime"]
print(trialStartTime)
coordenadas = np.array(parsed_trial_data["coordinates"])
letra = parsed_trial_data["letter"]
pendown = np.array(parsed_trial_data["penDownMarkers"])
pendown = pendown - sessionStartTime  # Normalizar tiempo al inicio
penup = np.array(parsed_trial_data["penUpMarkers"])
penup = penup - sessionStartTime  # Normalizar tiempo al inicio


x, y, t = coordenadas[:, 0], -coordenadas[:, 1], coordenadas[:, 2]
t = t - t[0]  # Normalizar tiempo al inicio
diff = penup - pendown
fsampling = diff/len(x)
print(f"Duración de cada trazo: {np.mean(fsampling):.2f} ms")
print(f"Frecuencia de muestreo aproximada: {np.mean(fsampling):.2f} ms")

plt.scatter(x,y)
# plt.plot(t,y)
# plt.plot(t,x)
plt.title(f"Coordenadas de la letra: {letra}")
plt.xlabel("X")
plt.ylabel("Y")
plt.show()


