import subprocess
import json
from collections import deque
from pathlib import Path
import re
import logging
import time

class TabletMessenger:
    def __init__(self, max_messages=200, serial="R52W70ATD1W"):
        self.buffer = None
        self.history = deque(maxlen=max_messages)
        self.max_messages = max_messages
        self.serial = serial

    def send_message(self, message: dict, tabletID: str):
        """Envía un mensaje a la tablet usando ADB broadcast."""
        json_str = json.dumps(message)
        # cmd = f'adb shell am broadcast -a {tabletID} --es payload \'{json_str}\''
        cmd = f'adb -s {self.serial} shell am broadcast -a {tabletID} --es payload \'{json_str}\''
        logging.info("Enviando mensaje a la tablet: %s", cmd)
        try:
            subprocess.run(cmd, shell=True, check=True)
            logging.info("Mensaje enviado correctamente.")
        except subprocess.CalledProcessError as e:
            logging.error("Error al enviar mensaje: %s", e)
    
    def leer_logcat(self, tag="LaptopLucas", level="V"):
        # subprocess.run(f'adb -s {self.serial} logcat -c', shell=True)
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += ["logcat", f"{tag}:{level}", "*:S", "-v", "time"]

        logging.info("Iniciando logcat: %s", " ".join(cmd))
        self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1)

        json_re = re.compile(r'\{.*?\}')
        try:
            for line in self._proc.stdout:
                if not line:
                    continue
                line = line.strip()
                # DEBUG: ver lo que llega si no matchea
                m = json_re.search(line)
                if not m:
                    # logging.debug("No JSON en línea: %s", line)
                    continue
                raw = m.group(0)
                try:
                    data = json.loads(raw)
                    self.history.append(data)
                    logging.info("Mensaje recibido: %s", data)
                except json.JSONDecodeError as e:
                    logging.info("No es JSON válido (%s): %s", e, raw)
        except Exception as e:
            logging.error("Fallo leyendo logcat: %s", e)
        finally:
            logging.info("Finalizando lector de logcat")

        subprocess.run(f'adb -s {self.serial} logcat -c', shell=True)

    def dump_logcat(self, tag="LaptopLucas", level="V"):
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += ["logcat", f"{tag}:{level}", "*:S", "-v", "time", "-m", "1"]
        out = subprocess.check_output(cmd, text=True)
        rx = re.compile(r'\{.*\}')
        msgs = []
        for line in out.splitlines():
            m = rx.search(line)
            if m:
                try:
                    msgs.append(json.loads(m.group(0)))
                except json.JSONDecodeError:
                    pass
        self.history.extend(msgs)
        subprocess.run(f'adb -s {self.serial} logcat -c', shell=True)
        return msgs

    def get_history(self):
        return list(self.history)

    def save_to_json(self, path: str, append: bool = False):
        """Guarda historial en un archivo JSON, nuevo o agregando al final."""
        path = Path(path)
        data_to_save = self.get_history_dict()

        if append and path.exists():
            try:
                with path.open('r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                if isinstance(existing_data, dict):
                    last_index = max(map(int, existing_data.keys()), default=-1)
                    for i, msg in data_to_save.items():
                        existing_data[str(last_index + 1 + i)] = msg
                    data_to_save = existing_data
            except Exception as e:
                print(f"Error al leer archivo existente: {e}")

        with path.open('w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        print(f"Historial guardado en {path}")

    def set_history_limit(self, new_limit: int):
        """Cambia el límite de historial."""
        old = list(self.history)
        self.history = deque(old[-new_limit:], maxlen=new_limit)
        self.max_messages = new_limit

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tablet_messenger = TabletMessenger(serial="R52W70ATD1W")

    trialPhase = "start"
    mensaje = {"sesionStatus": "on",
               "sessionid": 1,
               "runid": 1,
               "subjectid": "testsubject",
               "trialInfo": {"trialID": 1,
                             "trialPhase": trialPhase, 
                             "letter": "e", 
                             "duration": 4.0}}
    tablet_id = "com.handwriting.ACTION_MSG"
    tablet_messenger.send_message(mensaje, tablet_id)

    # if trialPhase == "requestInfo":
    #     time.sleep(0.5)
    #     msgs = tablet_messenger.dump_logcat(tag="LaptopLucas")
    #     print(msgs)
        # tablet_messenger.leer_logcat(tag="LaptopLucas")
        # print(tablet_messenger.get_history())

    # tablet_messenger.leer_logcat(tag="LaptopLucas")
    # print(tablet_messenger.get_history())
    # msgs = tablet_messenger.dump_logcat(tag="LaptopLucas")
    # print(msgs)