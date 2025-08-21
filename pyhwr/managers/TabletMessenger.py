import subprocess
import json
from collections import deque
from pathlib import Path
import re
import logging
import time

class TabletMessenger:
    def __init__(self, max_messages=200, serial="R52W70ATD1W"):
        """Constructor de la clase"""
        self.buffer = None
        self.history = deque(maxlen=max_messages)
        self.max_messages = max_messages
        self.serial = serial

        ##configurando logging

        self.logger = logging.getLogger("TabletMessenger")
        if not self.logger.handlers:
            self.log_consola = logging.StreamHandler()
            formatter = logging.Formatter("[%(name)s] %(levelname)s: %(message)s")
            self.log_consola.setFormatter(formatter)
            self.logger.addHandler(self.log_consola)
            self.logger.propagate = False    # <-- evita que el root lo vuelva a imprimir

    def make_message(self, sesionStatus, sesion_id, run_id, subject_id,
                     trialID, trialPhase, letter, duration):

        return {"sesionStatus": sesionStatus,
                "session_id": sesion_id,
                "run_id": run_id,
                "subject_id": subject_id,
                "trialInfo": {"trialID": trialID,
                              "trialPhase": trialPhase,
                              "letter": letter,
                              "duration": duration
                              }}

    def send_message(self, message: dict, tabletID: str):
        """Envía un mensaje a la tablet usando ADB broadcast."""
        json_str = json.dumps(message)
        cmd = f'adb -s {self.serial} shell am broadcast -a {tabletID} --es payload \'{json_str}\''
        self.logger.info("Enviando mensaje a la tablet: %s", cmd)
        try:
            subprocess.run(cmd, shell=True, check=True)
            self.logger.info("Mensaje enviado correctamente.")
        except subprocess.CalledProcessError as e:
            self.logger.error("Error al enviar mensaje: %s", e)
    
    def _device_docs_path(self, subject: str, session: str, run: str, trial_id: int|None=None) -> str:
        base = f"/storage/emulated/0/Documents/{subject}/{session}/{run}"
        return f"{base}/trial_{trial_id}.json" if trial_id is not None else base
    
    def _exists_on_device(self, device_path: str) -> bool:
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        # 'test -f' devuelve 0 si existe archivo
        cmd += ["shell", "test", "-f", device_path, "&&", "echo", "EXISTS"]
        try:
            out = subprocess.check_output(cmd, text=True).strip()
            return out == "EXISTS"
        except subprocess.CalledProcessError:
            return False

    def _choose_existing_device_path(self, subject: str, session: str, run: str, trial_id: int) -> str | None:
        """Devuelve la primera ruta existente para el trial, probando pública y sandbox."""
        cand_pub = self._device_docs_path(subject, session, run, trial_id)
        if self._exists_on_device(cand_pub):
            return cand_pub
        return None
    
    def read_trial_json(self, subject: str, session: str, run: str, trial_id: int) -> dict:
        # 1) Ruta pública Documents
        path_pub = self._device_docs_path(subject, session, run, trial_id)
        # 2) Fallback: sandbox de la app (getExternalFilesDir(DIRECTORY_DOCUMENTS))
        path_app = self._device_app_docs_path(subject, session, run, trial_id)

        if self._exists_on_device(path_pub):
            cmd = ["adb"]
            if self.serial:
                cmd += ["-s", self.serial]
            cmd += ["shell", "cat", path_pub]
            out = subprocess.check_output(cmd, text=True)
            return json.loads(out)

        logger.error("No se encontró el JSON del trial %d.", trial_id)
        return None

    def pull_trial_json(self, subject: str, session: str, run: str, trial_id: int, local_dir: str | Path = "./") -> Path:
        """Descarga (adb pull) el archivo del trial a la PC y devuelve la ruta local."""
        device_path = self._choose_existing_device_path(subject, session, run, trial_id)
        if not device_path:
            available = self.list_trials(subject, session, run)
            self.logger.error("No se encontró trial_%s.json para pull. Trials disponibles: %s", trial_id, available)
            raise FileNotFoundError(f"trial_{trial_id}.json no encontrado. Disponibles: {available}")

        local_dir = Path(local_dir)
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / f"trial_{trial_id}.json"

        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += ["pull", device_path, str(local_path)]

        subprocess.run(cmd, check=True)
        return local_path

    def list_trials(self, subject: str, session: str, run: str) -> list[int]:
        """
        Lista los trial IDs existentes en la carpeta:
        /storage/emulated/0/Documents/<subject>/<session>/<run>/
        Devuelve una lista de enteros [IDs] en base a archivos trial_*.json
        """
        folder = self._device_docs_path(subject, session, run, trial_id=None)
        cmd = ["adb"]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += ["shell", "ls", "-1", folder]

        try:
            out = subprocess.check_output(cmd, text=True)
        except subprocess.CalledProcessError:
            return []

        ids = []
        for name in out.splitlines():
            name = name.strip()
            if name.startswith("trial_") and name.endswith(".json"):
                num = name[len("trial_"):-len(".json")]
                if num.isdigit():
                    ids.append(int(num))
        return sorted(ids)

    def enable_logging(self, enabled = True):
        """Habilita o deshabilita el logging de mensajes."""
        if enabled and self.log_consola not in self.logger.handlers:
            self.logger.addHandler(self.log_consola)
        elif not enabled and self.log_consola in self.logger.handlers:
            self.logger.removeHandler(self.log_consola)

if __name__ == "__main__":
    import numpy as np
    import matplotlib.pyplot as plt
    tablet_messenger = TabletMessenger(serial="R52W70ATD1W")
    logger = logging.getLogger("TabletMessenger")
    logger.setLevel(logging.INFO)

    trialPhase = "trialInfo"

    mensaje = {"sesionStatus": "on",
               "session_id": 1,
               "run_id": 1,
               "subject_id": "test_subject",
               "trialInfo": {"trialID": 1,
                             "trialPhase": trialPhase, 
                             "letter": "l", 
                             "duration": 4.0}}
    tablet_id = "com.handwriting.ACTION_MSG"
    tablet_messenger.send_message(mensaje, tablet_id)

    # trial_data = tablet_messenger.read_trial_json("testsubject", "1", "1", 11)
    # print(trial_data)
    # coordenadas = np.array(trial_data["coordinates"])
    # plt.plot(coordenadas[:, 0], -coordenadas[:, 1], 
    #      linestyle='-',   # línea sólida
    #      marker=None)      # sin puntos
    # plt.show()
    # tablet_messenger.pull_trial_json("testsubject", "1", "1", 1, local_dir="test")