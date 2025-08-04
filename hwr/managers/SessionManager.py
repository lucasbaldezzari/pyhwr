import random
import time
import numpy as np
import keyboard
import logging
from pylsl import local_clock
from hwr.utils import SesionInfo

logging.basicConfig(level=logging.WARNING)  # Configuración básica del logger

class SessionManager:

    def __init__(self, phases, sesioninfo):
        self.phases = phases
        self.sesioninfo = sesioninfo
        self.in_phase = list(phases.keys())[-1]
        self.next_transition = -1

        self.creation_time = local_clock()
        self.accumulated_time = 0
        self._last_phase_time = self.creation_time

    def _advance_phase(self):
        """
        Función para avanzar a la siguiente fase
        """
        now = local_clock()
        self.accumulated_time += now - self._last_phase_time
        self._last_phase_time = now

        self.in_phase = self.phases[self.in_phase]["next"]
        self.next_transition = now + self.phases[self.in_phase]["duration"]

    def update(self):
        """
        Método para avanzar de fase solamente cuando se superen los tiempos de cada una.
        """
        now = local_clock()
        if now > self.next_transition:
            self._advance_phase()
            return True
        return False

    def next(self):
        """
        Usar este método si se necesita pasar a una nueva fase de manera asíncrona.
        """
        self._advance_phase()

    def moveTo(self, phase_name):
        """
        Método para mover manualmente a una fase específica.
        Útil para situaciones donde se necesita un control más preciso sobre las fases.
        """
        if phase_name in self.phases:
            self.in_phase = phase_name
            self.next_transition = local_clock() + self.phases[phase_name]["duration"]
            self._last_phase_time = local_clock()
        else:
            logging.error(f"Fase '{phase_name}' no encontrada en las fases definidas.")

    def get_elapsed_time(self):
        return local_clock() - self.creation_time

    def get_accumulated_time(self):
        return self.accumulated_time
    

if __name__ == "__main__":
    # Ejemplo de uso
    phases = {
    "start": {"next": "rest", "duration": 5.0},
    "rest": {"next": "precue", "duration": 2.0},
    "precue": {"next": "cue", "duration": 0.5},
    "cue": {"next": "evaluate", "duration": 3.0},
    "evaluate": {"next": "rest", "duration": 2.0},
    "first_jump": {"next": "start", "duration": 0.1},}

    sesion_info = SesionInfo(
        session_id="12345",
        session_name="Test Session",
        session_date=time.strftime("%Y-%m-%d"),
        run_number=1,
        subject_name="Test Subject"
    )

    manager = SessionManager(phases, sesion_info)
    contador = 0
    while True:
        if manager.update():
            contador += 1
            print(f"Avanzando a la fase: {manager.in_phase}")
            print(f"Tiempo acumulado: {manager.get_accumulated_time()}")
        if contador == 6:
            break