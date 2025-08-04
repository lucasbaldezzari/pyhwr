import subprocess
import json

mensaje = {
    "sesionStatus": "on",
    "trialInfo": {"trialStatus": "cue", "letter": "a"}
}
json_str = json.dumps(mensaje)

# Armar el comando exactamente como lo escribirías en consola
cmd = f'adb shell am broadcast -a com.handwriting.ACTION_MSG --es payload \'{json_str}\''

try:
    print("Ejecutando:", cmd)
    subprocess.run(cmd, shell=True, check=True)
    print("Mensaje enviado correctamente.")
except subprocess.CalledProcessError as e:
    print("Error al ejecutar el comando ADB:", e)