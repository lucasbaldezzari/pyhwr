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
    # 4) Parseo JSON -> dict
    return json.loads(raw)

path="test\\data\\sub-test_pilin\\ses-S001\\test_pilin"
file = "sub-test_pilin_ses-S001_task-Default_run-001_test_pilin.xdf"

data,header = pyxdf.load_xdf(path + "\\" + file)
trial = 5
trial_data = data[0]["time_series"][trial-1][0] if data[0]["info"]["name"][0] == "Tablet_Markers" else data[1]["time_series"][trial-1][0]

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


x, y, t = coordenadas[:, 0], coordenadas[:, 1], coordenadas[:, 2]
t = t - t[0]  # Normalizar tiempo al inicio
diff = penup - pendown
fsampling = diff/len(x)
print(f"Duración de cada trazo: {np.mean(fsampling):.2f} ms")
print(f"Frecuencia de muestreo aproximada: {np.mean(fsampling):.2f} ms")


plt.figure(figsize=(12, 6))
plt.plot(x, y, color="#35129d", linewidth = 10, zorder=1)   # Une los puntos en orden
plt.scatter(x, y, color="#11aa30", s=20, zorder = 2)  # Opcional: puntos de muestreo
plt.title(f"Coordenadas de la letra: {letra}")
plt.xlabel("X")
plt.ylabel("Y")
plt.gca().invert_yaxis()  # Si la tableta tiene origen en la esquina superior izquierda
plt.axis("equal")
plt.show()