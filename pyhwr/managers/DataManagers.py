import pyxdf
import h5py
import json
import numpy as np
from datetime import datetime, timezone, timedelta
import pandas as pd
import xml.etree.ElementTree as ET

class GHiampDataManager():
    """
    Clase para gestionar los datos registrados desde el amplifacor g.HIAMP.
    El archivo es un .hdf5 que contiene toda la información.
    """

    def __init__(self, filename, normalize_time=True, sfreq=256.):
        self.filename = filename
        self.sfreq = sfreq
        self.normalize_time = normalize_time
        self.file_data = self._read_data(self.filename)
        self.markers_info = self._get_markers_info()
        self.fecha_registro, self.timestamp_registro = self._get_datetime()
        self.raw_data = self._get_samples() ##muestras del g.H
        self.channels_info = self._get_channels_info()
        ##Revisar qué otra información es relevante del archivo hdf5
        
    def _read_data(self, filename):
        return h5py.File(filename, "r")
    
    def _get_channels_info(self):
        """
        Obtiene:
        - df_used: canales usados (AcquisitionTaskDescription)
        - df_device: canales disponibles (DAQDeviceCapabilities)
        - df_match: unión de ambos para ver correspondencia
        """
        used_xml = self.file_data["RawData"]["AcquisitionTaskDescription"][0]
        device_xml = self.file_data["RawData"]["DAQDeviceCapabilities"][0]

        df_used = self._resume_channels_from_xml(used_xml)
        df_device = self._resume_channels_from_xml(device_xml)

        # df_match = pd.merge(
        #     df_used,
        #     df_device,
        #     on="PhysicalChannelNumber",
        #     how="left",
        #     suffixes=("_used", "_device")
        # )

        return {
            "used_channels": df_used,
            "device_capabilities": df_device,
            # "matched": df_match
        }

    def _resume_channels_from_xml(self, xml_bytes, root_tag="ChannelProperties"):
        """
        Parsea un XML con estructura de canales (ya sea AcquisitionTaskDescription o DAQDeviceCapabilities)
        y retorna un DataFrame con toda la información.
        """
        xml_str = xml_bytes.decode("utf-8")
        root = ET.fromstring(xml_str)

        # Diferentes estructuras según tipo de XML
        if root.tag == "AcquisitionTaskDescription":
            path = ".//ChannelProperties/ChannelProperties"
        elif root.tag == "DAQDeviceCapabilities":
            path = ".//AnalogChannelProperties/ChannelProperties"
        else:
            path = f".//{root_tag}"

        channels = []
        for ch in root.findall(path):
            ch_dict = {}
            for elem in ch:
                if len(elem) > 0:
                    for sub in elem:
                        ch_dict[sub.tag] = sub.text
                else:
                    ch_dict[elem.tag] = elem.text
            channels.append(ch_dict)

        df = pd.DataFrame(channels)

        # Conversión de tipos
        numeric_cols = [
            "BipolarPhysicalChannelNumber", "SensitivityLowValue", "SensitivityHighValue",
            "SampleRate", "Offset", "NotchFilter", "HighpassFilter", "LowpassFilter",
            "DeviceNumber", "LogicalChannelNumber", "PhysicalChannelNumber"
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        bool_cols = ["IsBipolar", "IsTriggerChannel"]
        for col in bool_cols:
            if col in df.columns:
                df[col] = df[col].map({"true": True, "false": False})

        return df

    def _get_samples(self):
        """
        Función para obtener los datos de EEG con self.file_data["RawData"]["Samples"][:]
        """
        return self.file_data["RawData"]["Samples"][:]
    
    def _get_triggers_info(self):
        """
        .file_data["AsynchronData"]["AsynchronSignalTypes"][0]
        """

        trigger_info_xml = self.file_data["AsynchronData"]["AsynchronSignalTypes"][0]


    def _get_markers_info(self):
        """Función para obtener los marcadores del experimento.
        
        Retornaría una lista con los marcadores, un array con los tiempos,
        un diccionario con los keys siendo cada id enviado por el ghiamp y el
        valor sería el nombre. Por defecto es el mismo que envía el ampli"""
        markers_info = {}
        list_ids = self.file_data["AsynchronData"]["TypeID"][:].reshape(-1)
        list_ids -= list_ids.min()
        list_ids += 1
        ids = np.array(sorted(list(set(list_ids))))
        times = np.astype(self.file_data["AsynchronData"]["Time"][:][:].reshape(-1), float)

        for marker_id in ids:
            filter = np.where(list_ids==marker_id)
            if self.normalize_time:
                markers_info[marker_id] = (times[filter]/self.sfreq).tolist()
            else:
                markers_info[marker_id] = times[filter].tolist()

        return markers_info
    
    def changeMarkersNames(self, new_names: dict):
        """Función para cambiar los nombres de los marcadores.
        
        Recibe un diccionario con keys siendo los ids de los marcadores
        y values los nuevos nombres a asignar."""
        for marker_id, new_name in new_names.items():
            if marker_id in self.markers_info:
                self.markers_info[new_name] = self.markers_info.pop(marker_id)

    def _get_datetime(self):
        """
        Función para obtener la fecha y hora de registro del archivo hdf5.
        Retorna un objeto datetime y el timestamp correspondiente.
        1. Extraer el string de fecha del archivo hdf5
        2. Parsear el string de fecha
        3. Convertir a zona horaria UTC-3
        4. Timestamp en esa zona horaria
        5. Retornar ambos valores
        """

        data = self.file_data["RawData"]["AcquisitionTaskDescription"][0].split()
        #Busco el string que contiene la fecha
        target = next((item for item in data if b"<RecordingDateBegin>" in item), None)

        if target:
            #byte a str
            target_str = target.decode("utf-8")
            
            #Extaigo la fecha del string
            start_tag = "<RecordingDateBegin>"
            end_tag = "</RecordingDateBegin>"
            date_str = target_str.split(start_tag)[1].split(end_tag)[0]

            # 3. Parsear el string de fecha
            # Cortamos a 6 decimales porque datetime soporta hasta microsegundos
            dt_utc = datetime.strptime(date_str[:26] + "Z", "%Y-%m-%dT%H:%M:%S.%fZ")
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)

            # 4. Convertir a zona horaria UTC-3
            tz_minus3 = timezone(timedelta(hours=-3))
            dt_local = dt_utc.astimezone(tz_minus3)

            # 5. Timestamp en esa zona horaria
            ts = dt_local.timestamp()
            #retorno fecha y hora de registro, y timestamp
            return dt_local, ts
        else:
            return None, None

    def __getitem__(self, key):
        """
        Permite acceso a datos temporales de la siguiente forma:
          lsl_manager["time_mark", :]
          lsl_manager["time_mark", 0:20]
        """
        if not isinstance(key, tuple) or len(key) != 2:
            raise KeyError("Formato de índice no válido. Usa ('time_mark', slice).")

        time_mark, idx = key

        if time_mark not in self.markers_info:
            return None

        return self.markers_info[time_mark][idx]

class LSLDataManager():
    """
    Clase para gestionar los datos registrados desde LSL.
    """
    def __init__(self, filename):
        """
        filename: str.  Ruta al archivo .xdf con los datos."""
        self.filename = filename
        self.raw_data, self.header = self._read_data(self.filename)
        self.streamers_names = self._get_streamers_names()
        self.streamers_keys = self._get_streamers_keys()
        self.time_series = self._get_timeseries()
        self.fecha_registro, self.timestamp_registro = self._get_datetime()
        self.first_timestamp = self._get_first_timestamp() #esta en tiempo interno de LSL

        ##faltaría sacar información de los canales, sus posiciones, sus nombres, etc.
        ##Revisar qué otra información es relevante del archivo xdf

    def _read_data(self, filename):
        return pyxdf.load_xdf(filename)
    
    def _get_streamers_names(self):
        """
        Función para obtener información de los streams registrados.
        """
        return [data["info"]["name"][0] for data in self.raw_data]
    
    def _get_streamers_keys(self):
        """
        Función para obtener las keys de los streams registrados.
        """
        streamers_keys = {}
        for data in self.raw_data:
            streamer_name = data["info"]["name"][0]
            time_series_temp = data["time_series"][0][0]
            data = self._parse_trial_message(time_series_temp).keys()
            streamers_keys[streamer_name] = list(data)

        return streamers_keys
    
    def _get_timeseries(self):
        """
        Función para obtener las series de tiempo de cada stream.
        """
        timeseries_dict = {}
        for data in self.raw_data:
            streamer_timeseries = []
            for time_series in data["time_series"]:
                streamer_timeseries.append(self._parse_trial_message(time_series[0]))
            
            timeseries_dict[data["info"]["name"][0]] = streamer_timeseries

        return timeseries_dict

    def _parse_trial_message(self, raw):
        # 1) Si viene como bytes (a veces pasa con sockets/LSL)
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", errors="replace")

        if raw is None or raw == "":
            return []
        
        # 2) Limpieza simple
        raw = raw.strip()
        # 3) Si por logging quedó envuelto en comillas, las quitamos (solo las exteriores)
        if raw and raw[0] in "\"'" and raw[-1] == raw[0]:
            raw = raw[1:-1]
        # 4) Parseo JSON → dict
        return json.loads(raw)

    def _get_datetime(self):
        """
        Función para obtener la fecha y hora de registro del archivo xdf.
        """
        
        try:
            dt = datetime.strptime(self.header["info"]["datetime"][0], "%Y-%m-%dT%H:%M:%S%z")
            # Forzar conversión a UTC-3
            tz_minus3 = timezone(timedelta(hours=-3))
            dt_local = dt.astimezone(tz_minus3)
            return dt_local, dt.timestamp()
        except Exception:
            return None, None
        
    def _get_first_timestamp(self):
        """
        Función para obtener el primer timestamp registrado en el archivo xdf.
        """
        # lsl_manager.raw_data[0]["footer"]["info"]["first_timestamp"]
        first_timestamp = {}
        for data in self.raw_data:
            streamer_name = data["info"]["name"][0]
            first_timestamp[streamer_name] = float(data["footer"]["info"]["first_timestamp"][0])

        return first_timestamp

    def __getitem__(self, key):
        """
        Permite acceso tipo:
          lsl_manager["streamer", "trialID", :]
          lsl_manager["streamer", "trialID", 0:20]
        """
        if not isinstance(key, tuple) or len(key) != 3:
            raise KeyError("Formato de índice no válido. Usa ('streamer_name','label',slice).")

        streamer, label, idx = key

        # Validación de streamer
        if streamer not in self.time_series:
            return None

        trials = self.time_series[streamer]

        # Filtrar por trialID
        filtered = []
        for t in trials:
            if isinstance(t, dict) and label in t:
                filtered.append(t[label])

        if not filtered:
            return None

        # Aplicar slicing / indexing
        try:
            return filtered[idx]
        except Exception:
            return None

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    np.set_printoptions(suppress=True)

    sfreq = 256.
    filename = "test\\data\\gtec_recordings\\full_setup_9.hdf5"
    ghiamp_manager = GHiampDataManager(filename, normalize_time=True, sfreq=sfreq)

    ghiamp_manager.changeMarkersNames({1: "inicioSesión", 2: "trialLaptop", 3: "trialTablet", 4: "penDown"})
    print(len(ghiamp_manager["trialLaptop", :]))
    print(len(ghiamp_manager["trialTablet", :]))
    print(ghiamp_manager.fecha_registro, ghiamp_manager.timestamp_registro)

    ghiamp_manager.file_data["AsynchronData"]["AsynchronSignalTypes"][0]#.keys()#["Time"]

    path="test\\data\\sub-test_pilin\\ses-S001\\test_pilin"
    file = "sub-test_pilin_ses-S001_task-Default_run-001_test_pilin.xdf"

    lsl_filename = path + "\\" + file
    lsl_manager = LSLDataManager(lsl_filename)

    print(lsl_manager.streamers_names)
    print(lsl_manager.streamers_keys)
    print(lsl_manager["Tablet_Markers", "trialStartTime", :])
    trials_time_laptop = np.array(lsl_manager["Laptop_Markers", "trialStartTime", :])
    lsl_laptop_start = lsl_manager["Laptop_Markers", "sessionStartTime", :][0]
    print(lsl_laptop_start)
    print(lsl_manager.fecha_registro, lsl_manager.timestamp_registro)

    lsl_laptop_first_timestamp = lsl_manager.first_timestamp["Laptop_Markers"]
    lsl_laptop_start - lsl_laptop_first_timestamp
    print(np.diff(np.array(lsl_manager["Tablet_Markers", "coordinates", :][2])[:,2]).mean())

    ##obtengo las coordenadas y tiempo de cada trazo
    coordenadas = lsl_manager["Tablet_Markers", "coordinates", :][:]

    info = ghiamp_manager._get_channels_info()

    print(info["used_channels"].head())#["ChannelName"]
    print(info["used_channels"].columns)

    print(info["device_capabilities"].head())
    print(info["device_capabilities"].columns)

    print(info["matched"].head())
    print(info["matched"].columns)
    
    # used_channels_colums = ["ChannelName","ChannelType",
    #                         "SampleRate","HighpassFilter","LowpassFilter","NotchFilter","Offset",
    #                         "IsBipolar","SensitivityHighValue","SensitivityHighValue"]
    
    # used_channels_colums = ["ChannelName","ChannelType",
    #                         "SampleRate","HighpassFilter","LowpassFilter","NotchFilter","Offset",
    #                         "IsBipolar","SensitivityHighValue","SensitivityHighValue"]