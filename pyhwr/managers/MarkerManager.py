import json
from pylsl import StreamInfo, StreamOutlet, local_clock
import logging
from random import random

class MarkerManager():
    """Clase para gestionar los marcadores en la interfaz usando LSL"""
    def __init__(self, stream_name = "Generic_Markers", stream_type = "Events", source_id = None,
                  channel_count = 1, channel_format="string", nominal_srate = 0):
        
        self.stream_name = stream_name
        self.stream_type = stream_type
        if source_id is None:
            source_id = f"{self.stream_name}_{random.randint(1000, 9999)}"

        self.outlet_info = StreamInfo(
                name=stream_name,
                type=stream_type,
                nominal_srate=nominal_srate,
                channel_format=channel_format,
                channel_count=channel_count,
                source_id=source_id)

        self.outlet = StreamOutlet(self.outlet_info) #creo el outlet

        ##configurando logging
        self.logger = logging.getLogger("MarkerManager")
        if not self.logger.handlers:
            self.log_consola = logging.StreamHandler()
            formatter = logging.Formatter("[%(name)s] %(levelname)s: %(message)s")
            self.log_consola.setFormatter(formatter)
            self.logger.addHandler(self.log_consola)
            self.logger.propagate = False 

        self.logger.info(f"Creando un outlet con nombre {stream_name} y tipo {stream_type}")

    def sendMarker(self, mensaje):
        self.logger.debug(f"Enviando marcador: {mensaje}")
        mensaje = json.dumps(mensaje) if isinstance(mensaje, dict) else str(mensaje)
        self.outlet.push_sample([mensaje], timestamp=local_clock())

if __name__ == "__main__":
    from pyhwr.managers import TabletMessenger
    tablet_messenger = TabletMessenger(serial="R52W70ATD1W")
    logging.basicConfig(level=logging.INFO)
    marker_gen = MarkerManager(stream_name="Generic_Markers",
                               stream_type="Test_Events",
                               source_id="Test_Source",
                               channel_count=1,
                               channel_format="string",
                               nominal_srate=0)

    trial_data, _ = tablet_messenger.read_trial_json("test_subject", 1, 2, 1)

    marker_gen.sendMarker(trial_data)
