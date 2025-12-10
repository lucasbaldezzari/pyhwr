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

    def __init__(self, filename, subject="Test", normalize_time=True):
        """
        Parámetros
        ----------
        filename: str.  Ruta al archivo .hdf5 con los datos.
        normalize_time: bool. Si es True, los tiempos de los marcadores se normalizan a segundos.
        """
        self.filename = filename
        self.subject = subject
        self.file_data = self._read_data(self.filename)
        self.normalize_time = normalize_time
        self.fecha_registro, self.timestamp_registro = self._get_datetime()
        self.raw_data = self._get_samples() ##muestras del g.H
        self.channels_info = self._get_channels_info()
        self.sample_rate = self.channels_info["used_channels"]["SampleRate"][0]
        self.markers_info = self._get_markers_info()
        self.times = self._get_times()
        
    def _read_data(self, filename):
        return h5py.File(filename, "r")

    def _get_channels_info(self):
        """
        Función para obtener información de los canales usados y disponibles.

        Obtiene:
        - df_used: canales usados (AcquisitionTaskDescription)
        - df_device: canales disponibles (DAQDeviceCapabilities)
        - df_match: unión de ambos para ver correspondencia
        """
        used_xml = self.file_data["RawData"]["AcquisitionTaskDescription"][0]
        device_xml = self.file_data["RawData"]["DAQDeviceCapabilities"][0]

        df_used = self._resume_channels_from_xml(used_xml)
        df_device = self._resume_channels_from_xml(device_xml)

        columnas_interes = ["ChannelName","PhysicalChannelNumber","ChannelType",
                            "SampleRate","HighpassFilter","LowpassFilter",
                            "NotchFilter","Offset",
                            "IsBipolar","SensitivityHighValue","SensitivityHighValue"]
        
        df_used = df_used[columnas_interes + ["PhysicalChannelNumber"]]
        df_device = df_device[columnas_interes + ["PhysicalChannelNumber"]]

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
        Parsea un XML con estructura de canales (ya sea AcquisitionTaskDescription
        o DAQDeviceCapabilities) y retorna un DataFrame con toda la información.
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
    
    def _get_times(self, tinit = 0, tend = None):
        """
        Función para obtener los tiempos de las muestras a partir de la
        frecuencia de muestreo. Por defecto retorna en segundos y desde t=0
        """
        n_samples = self.raw_data.shape[0]
        if tend is None:
            tend = n_samples / self.sample_rate

        times = np.linspace(0, n_samples / self.sample_rate, n_samples, endpoint=False)

        if self.normalize_time:
            return times.tolist()
        else:
            return (times * self.sample_rate).tolist()

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
                markers_info[marker_id] = (times[filter]/self.sample_rate).tolist()
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
    
    def __str__(self):
        # Contar canales usados por tipo
        if "ChannelType" in self.channels_info["used_channels"].columns:
            canales_por_tipo = self.channels_info["used_channels"]["ChannelType"].value_counts().to_dict()
        else:
            canales_por_tipo = {"Desconocido": len(self.channels_info["used_channels"])}

        info = (
            f"GHiampDataManager\n"
            f"Archivo: {self.filename}\n"
            f"Sujeto: {self.subject}\n"
            f"Fecha registro: {self.fecha_registro}\n"
            f"Frecuencia de muestreo: {self.sample_rate:.2f} Hz\n"
            f"Total de canales usados: {len(self.channels_info['used_channels'])}\n"
            f"Canales por tipo: {canales_por_tipo}\n"
            f"Cantidad de eventos: {sum(len(v) for v in self.markers_info.values())}\n"
            f"IDs de marcadores: {list(self.markers_info.keys())}"
        )
        return info

    def __repr__(self):
        return self.__str__()

class LSLDataManager():
    """
    Clase para gestionar los datos registrados desde LSL.
    """
    def __init__(self, filename):
        """
        filename: str.  Ruta al archivo .xdf con los datos."""
        ##agregar chequeos de que hay al menos un trial con datos por streamer sino arrojar error.
        self.filename = filename
        self.raw_data, self.header = self._read_data(self.filename)
        self.streamers_names = self._get_streamers_names()
        self.streamers_keys = self._get_streamers_keys()
        self.time_series = self._get_timeseries()
        self.fecha_registro, self.timestamp_registro = self._get_datetime()
        self.first_timestamp = self._get_first_timestamp() #esta en tiempo interno de LSL
        self.trials_info = self._get_trials_info()
        ##agregar método para obtener tiempo promedio entre triasl, duración total de la sesión,
        ##tiempo promedio entre cues y otras cosas relevantes.
        

    def _read_data(self, filename):
        """
        Lee los datos del archivo .xdf y retorna el contenido crudo y el encabezado.
        """
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
        """
        Función para parsear el mensaje JSON de cada trial.
        Retorna un diccionario con la información del trial.
        """
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
        first_timestamp = {}
        for data in self.raw_data:
            streamer_name = data["info"]["name"][0]
            first_timestamp[streamer_name] = float(data["footer"]["info"]["first_timestamp"][0])

        return first_timestamp

    def _get_trials_info(self):
        """
        Función para exrtaer toda la información de los trials registrados por cada streamer.
        La función retorna un diccionario con los keys siendo los nombres de los streamers. Cada key es otro
        diccionario con los keys siendo los IDs de los trials y los values siendo listas con los datos de cada trial.
        """
        trials_info = {}
        for streamer in self.streamers_names:
            keys = self.streamers_keys[streamer]
            trials_data = self.time_series[streamer]
            trials_info[streamer] = {i+1: dict(zip(keys, trials_data[i].values()) if isinstance(trials_data[i], dict)
                                               else trials_data[i])
                                               for i in range(len(trials_data))}
            
        ##para cada streamer, elimino los trials que no tienen datos (diccionarios vacíos
        for streamer in trials_info:
            trials_info[streamer] = {k: v for k, v in trials_info[streamer].items() if v}
            
        return trials_info

    def __getitem__(self, key):
        """
        Permite acceso tipo:
          lsl_manager["streamer", "trialID", :]
          lsl_manager["streamer", "trialID", 0:5]
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
        
    def __str__(self):
        resumen_streams = []
        for streamer, trials in self.time_series.items():
            num_markers = sum(len(trial.keys()) for trial in trials if isinstance(trial, dict))
            resumen_streams.append(f"    - {streamer}: {num_markers} marcadores")

        # Agregar detalle de trials
        resumen_trials = []
        for streamer in self.streamers_names:
            try:
                # Intentamos obtener las letras de este streamer
                letras = self[streamer, "letter", :]
                if letras:
                    letras = list(letras)
                    resumen_trials.append(
                        f"    - {streamer}: {len(letras)} trials / Letras → {letras}"
                    )
                else:
                    resumen_trials.append(
                        f"    - {streamer}: Sin información de 'letter'"
                    )
            except Exception:
                resumen_trials.append(
                    f"    - {streamer}: No se pudo acceder a 'letter'"
                )
            

        info = (
            f"LSLDataManager\n"
            f" Archivo: {self.filename}\n"
            f" Fecha de registro: {self.fecha_registro}\n"
            f"Timestamp inicio: {min(self.first_timestamp.values()) if self.first_timestamp else 'N/A'}\n"
            # f"Timestamp fin: {max(self.first_timestamp.values()) if self.first_timestamp else 'N/A'}\n"
            f"Streamers detectados ({len(self.streamers_names)}):\n" +
            "\n".join(resumen_streams) +
            "\n  Trials por streamer:\n" +
            "\n".join(resumen_trials)
        )
        return info

    def __repr__(self):
        return self.__str__()
    
    def __len__(self):
        """Retorna la cantidad de streamers"""
        return len(self.streamers_names)

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    np.set_printoptions(suppress=True)

    sfreq = 256.
    filename = "test\\data\\gtec_recordings\\full_setup_9.hdf5"
    ghiamp_manager = GHiampDataManager(filename, normalize_time=True)

    ghiamp_manager.changeMarkersNames({1: "sessionStarted", 2: "trialLaptop", 3: "trialTablet", 4: "penDown"})
    print(ghiamp_manager["sessionStarted", :])
    print(len(ghiamp_manager["trialLaptop", :]))
    print(len(ghiamp_manager["trialTablet", :]))
    print(ghiamp_manager.fecha_registro, ghiamp_manager.timestamp_registro)

    channels_info = ghiamp_manager.channels_info
    print(channels_info["used_channels"].head())#["ChannelName"]
    print(channels_info["used_channels"].columns)
    print(channels_info["device_capabilities"].head())
    print(channels_info["device_capabilities"].columns)

    ## ****** DATOS DE LSL *********

    path="test\\data\\sueltos\\"
    file = "sub-P1_ses-S1_task-Default_run-001_test_v0.04.xdf"

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
    coordenadas = np.array(lsl_manager["Tablet_Markers", "coordinates", :][0])
    # x, y, t = coordenadas[:, 0], coordenadas[:, 1], coordenadas[:, 2]
    # coordenadas = lsl_manager["Tablet_Markers", "coordinates", :][:]
    # plt.figure(figsize=(12, 6))
    # plt.plot(x, y, color="#9d1212", linewidth = 10, zorder=1)   # Une los puntos en orden
    # plt.scatter(x, y, color="#ffffff", s=20, zorder = 2)  # Opcional: puntos de muestreo
    # plt.title(f"Trazo registrado")
    # plt.xlabel("X")
    # plt.ylabel("Y")
    # plt.gca().invert_yaxis()  # Si la tableta tiene origen en la esquina superior izquierda
    # plt.axis("equal")
    # plt.show()

    lsl_manager["Laptop_Markers", "letter", :]