import logging
import pyxdf
import h5py
import json
import numpy as np
from datetime import datetime, timezone, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
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
            else:
                logging.warning(f"Al parecer no hay marcador con id {marker_id}. No se puede establecer {new_name}")

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
    
    def __len__(self):
        """Retorna la cantidad de eventos registrados"""
        pass

class LSLDataManager():
    """
    Clase para gestionar los datos registrados desde LSL.
    """
    def __init__(self, filename, tablet_name = "Tablet_Markers", laptop_name = "Laptop_Markers"):
        """
        filename: str.  Ruta al archivo .xdf con los datos."""
        ##agregar chequeos de que hay al menos un trial con datos por streamer sino arrojar error.
        self.filename = filename
        self.tab_name = tablet_name
        self.lap_name = laptop_name
        self.raw_data, self.header = self._read_data(self.filename)
        self.streamers_names = self._get_streamers_names()
        self.streamers_keys = self._get_streamers_keys()
        self.time_series = self._get_timeseries()
        self.fecha_registro, self.timestamp_registro = self._get_datetime()
        self.trials_info = self._get_trials_info()
        self.first_lsl_timestamp = self._get_first_lsl_timestamp() #esta en tiempo interno de LSL
        self.first_timestamp = self._get_first_run_timestamp() #tiempo del primer trial registrado en cada streamer, que se asume es el inicio de la primera ronda
        self.coordinates_info = self.get_coordinates_info()
        self.pendown_delays = self.get_pendownDelays()
        self.trials_times = self.trialsTimes()
        self.traces_duration = self.get_tracesDuration()
        ##agregar método para obtener tiempo promedio entre triasl, duración total de la sesión,
        ##tiempo promedio entre cues y otras cosas relevantes.

    def _read_data(self, filename):
        """
        Lee los datos del archivo .xdf y retorna el contenido crudo y el encabezado.
        """
        return pyxdf.load_xdf(filename)
    
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
    
    def _get_streamers_names(self):
        """
        Función para obtener información de los streams registrados.
        """
        return [data["info"]["name"][0] for data in self.raw_data]
    
    def _get_streamers_keys(self):
        """
        Obtiene las keys registradas en cada streamer.
        """
        streamers_keys = {}

        for data in self.raw_data:
            streamer_name = data["info"]["name"][0]

            if len(data["time_series"]) == 0:
                streamers_keys[streamer_name] = []
                continue

            time_series_temp = data["time_series"][0][0]
            parsed = self._parse_trial_message(time_series_temp)

            if isinstance(parsed, dict):
                streamers_keys[streamer_name] = list(parsed.keys())
            else:
                streamers_keys[streamer_name] = []

        return streamers_keys
    
    @property
    def trials_qty(self):
        """
        Función para obtener la cantidad de trials registrados en cada streamer.
        """
        trials_qty = {}
        for streamer in self.streamers_names:
            trials_qty[streamer] = len(self.trials_info[streamer])

        return trials_qty
    
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
    
    def trialsTimes(self):
        """
        Función para obtener un dataframe con los tiempos de cada trial en segundos y relativos al
        sessionStartTime. Cada fila es un trial, las columnas son, letra, trialStartTime, trialCueTime y trialRestTime.
        """
        trials_time_dic = {}
        for name in self.streamers_names:
            df = pd.DataFrame(self.trials_info[name]).T[["letter", "trialStartTime", "trialCueTime", "trialRestTime"]]
            first_timestamp = self.first_timestamp[name]
            values = df[["trialStartTime", "trialCueTime", "trialRestTime"]].values
            values = (values - first_timestamp)/1000
            df[["trialStartTime", "trialCueTime", "trialRestTime"]] = values
            trials_time_dic[name] = df

        return trials_time_dic

    def has_stream(self, streamer_name: str) -> bool:
        """
        Indica si un streamer existe en el archivo XDF.
        """
        return streamer_name in self.time_series
    
    @property
    def has_tablet_stream(self) -> bool:
        """
        Indica si existe el streamer de la tablet.
        """
        return self.has_stream(self.tab_name)


    @property
    def has_laptop_stream(self) -> bool:
        """
        Indica si existe el streamer de la laptop.
        """
        return self.has_stream(self.lap_name)


    def _get_trials_from_streamer(self, streamer_name: str) -> dict:
        """
        Retorna los trials de un streamer si existen.
        Si el streamer no existe, retorna un diccionario vacío.
        """
        return self.trials_info.get(streamer_name, {})

    def get_coordinates_info(self):
        """
        Función para obtener las coordenadas de los trazos registrados. Se retorna un diccionario
        donde cada key es el trialID y los valores son otro diccionario con, letra, lista de ternas (x,y,t) donde t
        es el tiempo relativo al inicio del trazo (primer timestamp de la primera coordenada).
        """

        coordinates_info = {}
        
        if not self.has_tablet_stream:
            logging.warning(
                f"No se encontró el streamer '{self.tab_name}'. "
                "No se computará información de coordenadas."
            )
            return coordinates_info
        
        ##recorro cada trial registrado en el streamer Tablet_Markers de self.time_series

        for trial in self.time_series[self.tab_name]:
            coordinates_trial = np.array(trial["coordinates"])
            letter_trial = trial["letter"]
            if len(coordinates_trial) > 0:
                first_timestamp = coordinates_trial[0,2]
                #resto el primer timestamp a todos los tiempos para tenerlos relativos al inicio del trazo
                coordinates_trial[:,2] = coordinates_trial[:,2] - first_timestamp
                coordinates_info[trial["trialID"]] = {
                    "letter": letter_trial,
                    "coordinates": [(x, y, t) for x, y, t in coordinates_trial]
                }
            else:
                coordinates_info[trial["trialID"]] = {
                    "letter": trial["letter"],
                    "coordinates": None
                    }

        return coordinates_info

    def getTrialCoordinates(self, trialID):
        """
        Obtiene las coordenadas de un trial específico.

        Retorna
        -------
        np.ndarray | None
            Retorna un array si hay coordenadas.
            Retorna None si no hay tablet, no existe el trial o no hay coordenadas.
        """
        if not self.coordinates_info:
            return None

        trial_info = self.coordinates_info.get(trialID, None)

        if trial_info is None:
            return None

        coordinates = trial_info.get("coordinates", None)

        if coordinates is None:
            return None

        return np.array(coordinates)

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
        
    def _get_first_lsl_timestamp(self):
        """
        Función para obtener el primer timestamp registrado en el archivo xdf.
        """
        first_timestamp = {}
        for data in self.raw_data:
            streamer_name = data["info"]["name"][0]
            first_timestamp[streamer_name] = float(data["footer"]["info"]["first_timestamp"][0])

        return first_timestamp
    
    def _get_first_run_timestamp(self):
        """
        Obtiene el timestamp de inicio de la primera ronda para cada streamer.
        Si un streamer no tiene trials válidos, retorna None para ese streamer.
        """
        dic = {}

        for name in self.streamers_names:
            trials = self.trials_info.get(name, {})

            if not trials:
                dic[name] = None
                continue

            first_key = list(trials.keys())[0]
            dic[name] = trials[first_key].get("sessionStartTime", None)

        return dic

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
    
    def _describe_one_streamer(self, streamer_name: str) -> dict:
        """
        Calcula estadísticas básicas para un streamer.
        Si el streamer no existe o no tiene trials, retorna valores None.
        """
        empty_dict = {
            "duration": None,
            "trials": None,
            "trials_avg_time": None,
            "trials_time_std": None,
            "cues_avg_time": None,
            "cues_time_std": None,
            "letters": None,
        }

        trials_info = self._get_trials_from_streamer(streamer_name)

        if not trials_info:
            return empty_dict

        keys = list(trials_info.keys())
        first_key = keys[0]
        last_key = keys[-1]

        first_trial = trials_info[first_key]
        last_trial = trials_info[last_key]

        session_start = first_trial.get("sessionStartTime", None)
        session_final = last_trial.get("sessionFinalTime", None)

        out = empty_dict.copy()

        if session_start is not None and session_final is not None:
            out["duration"] = round(float((session_final - session_start) / 1000), 2)

        out["trials"] = len(trials_info)

        trial_times = [
            trial.get("trialStartTime", None)
            for trial in trials_info.values()
            if trial.get("trialStartTime", None) is not None
        ]

        if len(trial_times) >= 2:
            trial_times_diff = np.abs(np.diff(trial_times))
            out["trials_avg_time"] = round(float(np.mean(trial_times_diff) / 1000), 2)
            out["trials_time_std"] = round(float(np.std(trial_times_diff) / 1000), 2)

        cue_times = []
        rest_times = []

        for trial in trials_info.values():
            cue = trial.get("trialCueTime", None)
            rest = trial.get("trialRestTime", None)

            if cue is not None and rest is not None:
                cue_times.append(cue)
                rest_times.append(rest)

        if len(cue_times) > 0:
            cue_durations = np.abs(np.array(rest_times) - np.array(cue_times))
            out["cues_avg_time"] = round(float(np.mean(cue_durations) / 1000), 2)
            out["cues_time_std"] = round(float(np.std(cue_durations) / 1000), 2)

        letters = [
            trial.get("letter", None)
            for trial in trials_info.values()
            if trial.get("letter", None) is not None
        ]

        if letters:
            out["letters"] = sorted(list(set(letters)))

        return out
    
    def describe_trials(self):
        """
        Describe los trials registrados en los streamers disponibles.

        Si no existe Tablet_Markers, sus valores quedan en None.
        Si no existe Laptop_Markers, sus valores quedan en None.
        """
        final_dict = {
            self.tab_name: self._describe_one_streamer(self.tab_name),
            self.lap_name: self._describe_one_streamer(self.lap_name)
        }

        return pd.DataFrame(final_dict)
        
    def get_pendownDelays(self):
        """
        Retorna un diccionario con los keys seindo los trialID y cada valor es otro diccionario con
        letra y la diferencia de tiempo entre el trialCueTime y el primer penDown registrado en coordinates_info.
        Esto da una idea del tiempo que tarda la persona en comenzar a dibujar después de recibir el cue.

        Si no hay penDown registrado para un trial, se aigna un valor de None para ese trialID.
        """
        delays = {}

        tablet_trials = self._get_trials_from_streamer(self.tab_name)

        if not tablet_trials:
            logging.warning(
                f"No hay trials para '{self.tab_name}'. "
                "No se computarán delays de penDown."
            )
            return delays

        for trial in tablet_trials.values():
            pendownmarker = trial["penDownMarkers"]
            if len(pendownmarker) > 0: #hubo un evento de penDown registrado
                penDownTime = pendownmarker[0] #tiempo del primer penDown registrado
                trialCueTime = trial["trialCueTime"] #tiempo del cue
                delay = penDownTime - trialCueTime #diferencia entre ambos tiempos
                delays[trial["trialID"]] = {
                    "letter": trial["letter"],
                    "delay": round(float(delay)/1000,2) #segundos
                }
                
            else:
                delays[trial["trialID"]] = {
                    "letter": trial["letter"],
                    "delay": None
                }
                continue

        return delays
    
    def penDown_delays_resume(self):
        """
        Retorna un dataframe con estadísticos del delay de penDown.
        Si no hay datos de tablet, retorna un DataFrame vacío.
        """
        columns = ["letter", "mean", "std", "max", "min", "count"]

        if not self.pendown_delays:
            return pd.DataFrame(columns=columns)

        df = pd.DataFrame.from_dict(self.pendown_delays, orient="index")

        if df.empty or "letter" not in df.columns or "delay" not in df.columns:
            return pd.DataFrame(columns=columns)

        stats_df = (
            df.groupby("letter")["delay"].agg(
                mean="mean",
                std="std",
                max="max",
                min="min",
                count="count"
            ).reset_index().sort_values("letter")
        )

        return stats_df

    def get_tracesDuration(self):
        """
        Retorna un diccionario con la duración de cada trazo para cada letra. Los keys son los trialID y
        cada valor es otro diccionario con el valor de duración del trazo. 
        La duración del trazo se obtiene a partir del último punto registrado del trazo dibujado en la
        tablet.
        """
        durations = {}

        tablet_trials = self._get_trials_from_streamer(self.tab_name)

        if not tablet_trials:
            logging.warning(
                f"No hay trials para '{self.tab_name}'. "
                "No se computarán duraciones de trazos."
            )
            return durations
        
        for trial in tablet_trials.values():
            traces = np.array(trial["coordinates"])
            if len(traces) > 0: #se registró al menos un punto de trazado
                first_point = traces[0,2] #tiempo del último penDown registrado
                last_point = traces[-1,2] #tiempo del último penDown registrado
                durations[trial["trialID"]] = {
                    "letter": trial["letter"],
                    "duration": round(float((last_point-first_point)/1000),2) #segundos
                }

            else:
                durations[trial["trialID"]] = {
                    "letter": trial["letter"],
                    "duration": None
                }
                continue

        return durations
    
    def tracesDuration_resume(self):
        """
        Retorna un dataframe con estadísticos de duración de trazos.
        Si no hay datos de tablet, retorna un DataFrame vacío.
        """
        columns = ["letter", "mean", "std", "max", "min", "count"]

        if not self.traces_duration:
            return pd.DataFrame(columns=columns)

        df = pd.DataFrame.from_dict(self.traces_duration, orient="index")

        if df.empty or "letter" not in df.columns or "duration" not in df.columns:
            return pd.DataFrame(columns=columns)

        stats_df = (
            df.groupby("letter")["duration"].agg(
                mean="mean",
                std="std",
                max="max",
                min="min",
                count="count"
            ).reset_index().sort_values("letter")
        )

        return stats_df
    
    def infoTrial(self, trialID):
        """
        Obtiene la información de un trial específico usando datos de la tablet.

        Retorna
        -------
        dict | None
            Retorna un diccionario si existe información de tablet para ese trial.
            Retorna None si no hay tablet o si el trial no existe.
        """
        if not self.has_tablet_stream:
            return None

        tablet_trials = self._get_trials_from_streamer(self.tab_name)
        info_trial = tablet_trials.get(trialID, None)

        if info_trial is None:
            return None

        first_timestamp = self.first_timestamp.get(self.tab_name, None)

        info_dict = {
            "letter": info_trial.get("letter", None),
            "trialStartTime": None,
            "trialCueTime": None,
            "trialRestTime": None,
            "pendowns": None,
            "penups": None,
            "writing_duration": None,
            "pendown_delay": None
        }

        if first_timestamp is not None:
            trial_start = info_trial.get("trialStartTime", None)
            trial_cue = info_trial.get("trialCueTime", None)
            trial_rest = info_trial.get("trialRestTime", None)

            if trial_start is not None:
                info_dict["trialStartTime"] = (trial_start - first_timestamp) / 1000

            if trial_cue is not None:
                info_dict["trialCueTime"] = (trial_cue - first_timestamp) / 1000

            if trial_rest is not None:
                info_dict["trialRestTime"] = (trial_rest - first_timestamp) / 1000

            info_dict["pendowns"] = [
                (t - first_timestamp) / 1000
                for t in info_trial.get("penDownMarkers", [])
            ]

            info_dict["penups"] = [
                (t - first_timestamp) / 1000
                for t in info_trial.get("penUpMarkers", [])
            ]

        coordinates = self.getTrialCoordinates(trialID)

        if coordinates is not None and len(coordinates) > 0:
            writing_duration = coordinates[-1, 2] / 1000
            info_dict["writing_duration"] = round(float(writing_duration), 3)

        info_dict["pendown_delay"] = self.pendown_delays.get(
            trialID, {}
        ).get("delay", None)

        return info_dict
    
    def lettersTrials(self, letter):
        """
        Retorna los trialID asociados a una letra para laptop y tablet.

        Retorna
        -------
        tuple[list, list]
            (trials_ids_laptop, trials_ids_tablet)

            Si no hay tablet, trials_ids_tablet será [].
        """
        trial_ids_tablet = []
        trials_ids_laptop = []

        laptop_trials = self._get_trials_from_streamer(self.lap_name)
        tablet_trials = self._get_trials_from_streamer(self.tab_name)

        for trialID, info in laptop_trials.items():
            if info.get("letter", None) == letter:
                trials_ids_laptop.append(trialID)

        for trialID, info in tablet_trials.items():
            if info.get("letter", None) == letter:
                trial_ids_tablet.append(trialID)

        return trials_ids_laptop, trial_ids_tablet
    
    def is_none_like(self, coordinates):
        """
        Función para verificar si un valor es None o equivalente a
        None (como un array vacío o un array escalar con valor None).
        Params:
            - coordinates: valor a verificar
        """
        if coordinates is None:
            return True
        if isinstance(coordinates, np.ndarray) and coordinates.shape == () and coordinates.item() is None:
            return True
        return False
    
    def plot_traces(self, trialID, title = None, filename = None,
                    show = True, save = False, figsize=(12, 6),
                    line_color = "#9d1212", line_width = 10,
                    point_color = "#ffffff", point_size = 20,
                    hide_title = False, hide_axes = False, hide_ticks = False,
                    hide_labels = False, hide_spines = False):
        """
        Función para graficar el trazo registrado
        en un trial específico. Se obtiene la información de coordinates_info.
        """
        coordinates = self.getTrialCoordinates(trialID)
        if self.is_none_like(coordinates):
            raise ValueError(f"No hay coordenadas registradas para el trialID {trialID}")
        
        x, y, t = coordinates[:, 0], coordinates[:, 1], coordinates[:, 2]
        letra = self.coordinates_info[trialID]["letter"]
        if filename is None:
            filename = f"trazo_trial_{trialID}_letra_{letra}.png"

        fig, ax = plt.subplots()
        fig.set_size_inches(*figsize)
        ax.plot(x, y, color=line_color, linewidth=line_width, zorder=1)   # Une los puntos en orden
        ax.scatter(x, y, color=point_color, s=point_size, zorder = 2)  # Opcional: puntos de muestreo
        ax.set_title(title if title else f"Trazo registrado - Trial {trialID}")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.invert_yaxis()  # Si la tableta tiene origen en la esquina superior izquierda
        ax.axis("equal")

        if hide_title:
            ax.set_title("")
        if hide_axes:
            ax.axis("off")

        if hide_ticks:
            ax.set_xticks([])
            ax.set_yticks([])

        if hide_labels:
            ax.set_xlabel("")
            ax.set_ylabel("")

        if hide_spines:
            for spine in ax.spines.values():
                spine.set_visible(False)

        if save:
            plt.savefig(filename)

        if show:
            plt.show()

        return fig, ax

    def plot_all_traces(self, grilla=None, figsize=(12, 8), line_color = "#9d1212", line_width = 10,
                        point_color = "#ffffff", point_size = 20, show = True,
                        hide_title = False, hide_axes = False, hide_ticks = False,
                        hide_labels = False, hide_spines = False):
        """Función para graficar todos los trazos registrados en el streamer Tablet_Markers.
        Se organiza en una grilla donde las columnas son las letras y las filas son los trials de cada letra.
        Si no se especifica el tamaño de la grilla, se calcula automáticamente en función de la cantidad de letras y trials.
        """
        if not self.coordinates_info:
            logging.warning(
                f"No hay coordenadas disponibles para graficar. "
                f"Probablemente no existe el streamer '{self.tab_name}'."
            )
            return None, None
        
        trials_by_letter = defaultdict(list)
        for trialID in self.coordinates_info.keys():
            letra = self.coordinates_info[trialID]["letter"]
            trials_by_letter[letra].append(trialID)

        different_letters = sorted(trials_by_letter.keys()) #ordenamos letras por columna

        for letra in different_letters:
            trials_by_letter[letra].sort()

        if grilla is None:
            n_columnas = len(different_letters)
            n_filas = max(len(trials_by_letter[letra]) for letra in different_letters)
        else:
            n_filas, n_columnas = grilla

        fig, axes = plt.subplots(n_filas, n_columnas,
                                figsize=figsize)

        # Normalizar axes a matriz 2D siempre
        if n_filas == 1 and n_columnas == 1:
            axes = [[axes]]
        elif n_filas == 1:
            axes = [axes]
        elif n_columnas == 1:
            axes = [[ax] for ax in axes]

        # 6. Poblar grilla correctamente
        for col, letra in enumerate(different_letters):
            trials = trials_by_letter[letra]

            for row, trialID in enumerate(trials):
                ax = axes[row][col]

                coordinates = self.getTrialCoordinates(trialID)
                if self.is_none_like(coordinates):
                    ax.axis("off")
                    continue

                x, y, t = coordinates[:, 0], coordinates[:, 1], coordinates[:, 2]

                ax.plot(x, y, color=line_color, linewidth=line_width, zorder=1)
                ax.scatter(x, y, color=point_color, s=point_size, zorder=2)

                ax.set_title(f"Trial {trialID} - {letra}")
                ax.set_xlabel("X")
                ax.set_ylabel("Y")
                ax.invert_yaxis()
                ax.axis("equal")

                if hide_title:
                    ax.set_title("")
                if hide_axes:
                    ax.axis("off")
                if hide_ticks:
                    ax.set_xticks([])
                    ax.set_yticks([])
                if hide_labels:
                    ax.set_xlabel("")
                    ax.set_ylabel("")
                if hide_spines:
                    for spine in ax.spines.values():
                        spine.set_visible(False)

            # 7. Apagar celdas vacías en la columna
            for row in range(len(trials), n_filas):
                axes[row][col].axis("off")

        plt.tight_layout()

        if show:
            plt.show()

        return fig, axes

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