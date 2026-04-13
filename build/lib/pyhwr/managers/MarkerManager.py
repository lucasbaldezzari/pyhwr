import json
import random
import logging
from pylsl import StreamInfo, StreamOutlet, local_clock
from typing import Any, Optional, Union

class MarkerManager:
    """Clase para gestionar el envío de marcadores a través de LSL (Lab Streaming Layer)."""

    def __init__(
        self,
        stream_name: str = "Generic_Markers",
        stream_type: str = "Events",
        source_id: Optional[str] = None,
        channel_count: int = 1,
        channel_format: str = "string",
        nominal_srate: float = 0.0,
        logger: Optional[logging.Logger] = None
    ) -> None:
        """
        Inicializa un flujo LSL para enviar marcadores.
        """
        self.stream_name = stream_name
        self.stream_type = stream_type
        self.source_id = source_id or f"{stream_name}_{random.randint(1000, 9999)}"

        # Configurar la información del stream LSL
        self.outlet_info = StreamInfo(
            name=self.stream_name,
            type=self.stream_type,
            nominal_srate=nominal_srate,
            channel_format=channel_format,
            channel_count=channel_count,
            source_id=self.source_id
        )

        # Crear el outlet para enviar los datos
        self.outlet = StreamOutlet(self.outlet_info)

        # Configurar logging
        self.logger = logger or logging.getLogger("MarkerManager")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("[%(name)s] %(levelname)s: %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            self.logger.propagate = False

        self.logger.info(f"Outlet LSL creado: {stream_name} ({stream_type}) [{self.source_id}]")

    def sendMarker(self, message: Union[str, dict, Any]) -> None:
        """Envía un marcador (evento) al flujo LSL."""
        if message is None or message == "":
            self.logger.warning("Intento de enviar marcador vacío o nulo — ignorado.")
            return

        try:
            payload = json.dumps(message) if isinstance(message, dict) else str(message)
            self.outlet.push_sample([payload], timestamp=local_clock())
            self.logger.debug(f"Marcador enviado: {payload}")
        except Exception as e:
            self.logger.error(f"Error enviando marcador: {e}", exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    try:
        from pyhwr.managers import TabletMessenger
        tablet_messenger = TabletMessenger(serial="R52W70ATD1W")

        marker_gen = MarkerManager(
            stream_name="Generic_Markers",
            stream_type="Test_Events",
            source_id="Test_Source",
        )

        trial_data, _ = tablet_messenger.read_trial_json("test_subject", 1, 2, 1)
        marker_gen.sendMarker(trial_data)

    except ImportError:
        print("⚠️ 'pyhwr.managers' no disponible. Ejecutando ejemplo simple...")
        marker_gen = MarkerManager()
        marker_gen.sendMarker({"test": "marker sent successfully"})