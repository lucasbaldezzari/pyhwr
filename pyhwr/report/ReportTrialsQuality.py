from __future__ import annotations

from collections import Counter
from typing import Any, TYPE_CHECKING

import mne
import numpy as np
import pandas as pd

mne.set_log_level("WARNING")

if TYPE_CHECKING:
    from pyhwr.managers import GHiampDataManager, LSLDataManager


class ReportTrialsQuality:
    """
    Evalúa la calidad de los trials de una ronda a partir de la amplitud
    pico a pico de los canales EEG (se descartan EOG/EMG), usando el
    mecanismo de rechazo por diccionario `reject` de MNE:
    https://mne.tools/stable/auto_tutorials/preprocessing/20_rejecting_bad_data.html

    Cada trial se define desde el marcador 'trialTablet' (g.HIAMP) hasta el
    marcador de rest de ese trial (LSL, streamer Tablet_Markers), sincronizados
    al reloj del g.HIAMP mediante el marcador 'startRun'. No se distingue
    Ejecutada/Imaginada: ambos tipos de ronda tienen estos marcadores.

    Todos los trials se agrupan en un único objeto mne.Epochs (self._cleaned_epocas),
    lo que exige una duración común de época entre trials (mne.Epochs no
    admite duraciones distintas por época). Esa duración común se calcula
    igual que en epocas_escritura_ejecutada.py: el mínimo entre las
    duraciones propias (trialTablet → rest) de los trials no-artefacto, con
    un piso absoluto. Como consecuencia, el chequeo de amplitud pico a pico
    no cubre necesariamente la ventana completa y propia de cada trial, sino
    sólo los primeros `common_duration` segundos de cada uno.

    La evaluación de calidad de canales (más allá del rechazo por trial) vive
    en la clase hermana ReportChannelsQuality (ReportChannelsQuality.py), que
    puede reutilizar la señal EEG ya filtrada de esta clase vía get_eeg_raw().
    """

    #: IDs numéricos de marcador -> nombre, según el firmware del g.HIAMP.
    _MARKER_NAMES = {1: "startRun", 2: "trialTablet", 3: "penDown", 4: "trialLaptop"}

    def __init__(
        self,
        gmanager: "GHiampDataManager",
        lsl_manager: "LSLDataManager",
        reject_threshold: float = 150.0,
        l_freq: float = 4.0,
        h_freq: float = 30.0,
        notch_freq: float = 50.0,
        min_valid_duration: float = 2.0,
        common_duration_floor: float = 2.0,
    ) -> None:
        """
        Parámetros
        ----------
        gmanager : GHiampDataManager
            Debe haber sido creado con normalize_time=True (marcadores en segundos).
        lsl_manager : LSLDataManager
            Debe tener datos en el streamer 'Tablet_Markers' (trialRestTime),
            presentes tanto en rondas Ejecutadas como Imaginadas.
        reject_threshold : float
            Umbral de rechazo por amplitud pico a pico, en la escala nativa de
            las muestras crudas del g.HIAMP (µV aprox., sin conversión a V SI).
        l_freq, h_freq : float
            Banda de paso del filtro EEG.
        notch_freq : float
            Frecuencia del notch (ruido de línea).
        min_valid_duration : float
            Duración mínima (s) de la ventana propia de un trial (trialTablet
            → rest) para que aporte al cómputo de la duración común de época.
            Trials más cortos se consideran artefacto y se excluyen de ese
            cómputo (pero igual se intentan epocar).
        common_duration_floor : float
            Piso absoluto (s) para la duración común de época.
        """
        if not gmanager.normalize_time:
            raise ValueError(
                "ReportTrialsQuality requiere un GHiampDataManager con "
                "normalize_time=True (marcadores en segundos)."
            )

        self.gmanager = gmanager
        self.lsl_manager = lsl_manager
        self.reject_threshold = reject_threshold
        self.l_freq = l_freq
        self.h_freq = h_freq
        self.notch_freq = notch_freq
        self.min_valid_duration = min_valid_duration
        self.common_duration_floor = common_duration_floor

        self._raw: mne.io.RawArray | None = None
        self._trials: list[dict[str, Any]] | None = None
        self._full_epocas: mne.Epochs | None = None
        self._cleaned_epocas: mne.Epochs | None = None ##Objeto con épocas filtradas según reject
        self._common_duration: float | None = None

    # ── Señal EEG ──────────────────────────────────────────────────────

    def _ensure_marker_names(self) -> None:
        markers = self.gmanager.markers_info
        if "trialTablet" not in markers or "startRun" not in markers:
            self.gmanager.changeMarkersNames(self._MARKER_NAMES)

    def _build_eeg_raw(self) -> mne.io.RawArray:
        used = self.gmanager.channels_info["used_channels"]
        eeg_mask = (used["ChannelType"] == "EEG").to_numpy()
        eeg_positions = np.where(eeg_mask)[0]

        if eeg_positions.size == 0:
            raise ValueError("No se encontraron canales EEG en channels_info['used_channels'].")

        # "PhysicalChannelNumber" puede aparecer duplicada como columna en
        # channels_info (ver GHiampDataManager._get_channels_info); nos
        # quedamos con la primera ocurrencia.
        physical_col = used.loc[eeg_mask, "PhysicalChannelNumber"]
        if isinstance(physical_col, pd.DataFrame):
            physical_col = physical_col.iloc[:, 0]
        physical_numbers = physical_col.tolist()
        ch_names = [f"EEG{int(n):02d}" for n in physical_numbers]

        # gmanager.raw_data: (muestras, canales) → MNE espera (canales, muestras)
        eeg_data = self.gmanager.raw_data[:, eeg_positions].T.astype(np.float64)

        info = mne.create_info(ch_names=ch_names, sfreq=self.gmanager.sample_rate, ch_types="eeg")
        raw = mne.io.RawArray(eeg_data, info, verbose=False)
        raw.filter(l_freq=self.l_freq, h_freq=self.h_freq, picks="eeg", fir_design="firwin", verbose=False)
        raw.notch_filter([self.notch_freq], picks="eeg", verbose=False)
        return raw

    def _ensure_raw(self) -> mne.io.RawArray:
        if self._raw is None:
            self._ensure_marker_names()
            self._raw = self._build_eeg_raw()
        return self._raw

    def get_eeg_raw(self) -> mne.io.RawArray:
        """
        Devuelve la señal EEG (solo canales EEG, filtrada en banda + notch),
        construyéndola una única vez. Pensada para reutilizarse en
        ReportChannelsQuality sin repetir la selección de canales/filtrado.
        """
        return self._ensure_raw()

    # ── Ventanas de trial (trialTablet → rest) ────────────────────────

    def _trial_windows(self) -> list[dict[str, Any]]:
        self._ensure_marker_names()

        t0_gtec = self.gmanager.markers_info["startRun"][0]
        trials_tablet = np.array(self.gmanager.markers_info["trialTablet"])

        tablet_trials = self.lsl_manager.trials_info.get("Tablet_Markers", {})
        if not tablet_trials:
            raise ValueError(
                "No hay datos de 'Tablet_Markers' en el LSLDataManager: no se "
                "puede definir la ventana de trial (trialTablet → rest)."
            )

        n_lsl_trials = len(tablet_trials)
        letras = [tablet_trials[i]["letter"] for i in range(1, n_lsl_trials + 1)]

        start_time_tablet = tablet_trials[1]["sessionStartTime"] / 1000
        rest_times = np.array(self.lsl_manager["Tablet_Markers", "trialRestTime", :]) / 1000 - start_time_tablet
        rest_times_gtec = rest_times + t0_gtec

        n_trials = min(len(letras), len(trials_tablet), len(rest_times_gtec))

        return [
            {
                "trial_id": i + 1,
                "letter": letras[i],
                "start": float(trials_tablet[i]),
                "end": float(rest_times_gtec[i]),
            }
            for i in range(n_trials)
        ]

    # ── Duración común de época ────────────────────────────────────────

    def _compute_common_duration(self, windows: list[dict[str, Any]]) -> float:
        """
        Réplica de la lógica de epocas_escritura_ejecutada.py: duración común
        = máx(common_duration_floor, mínimo de las duraciones de trial que
        superen min_valid_duration). Si ningún trial aporta una duración
        válida, se usa directamente common_duration_floor.
        """
        valid_durations = [
            w["end"] - w["start"] for w in windows
            if (w["end"] - w["start"]) >= self.min_valid_duration
        ]
        if not valid_durations:
            return self.common_duration_floor

        return max(self.common_duration_floor, min(valid_durations))

    # ── Construcción del Epochs combinado ─────────────────────────────

    def _build_combined_epochs(
        self,
        raw: mne.io.RawArray,
        windows: list[dict[str, Any]],
        common_duration: float,
    ) -> tuple[mne.Epochs | None, list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Arma un único mne.Epochs con un evento por trial (ancla: inicio de
        trialTablet, duración: common_duration para todos). Devuelve
        (epochs, ventanas_incluidas, ventanas_fuera_de_rango); epochs es None
        si ninguna ventana entra en el raw. epochs.drop_log[i] corresponde en
        orden a ventanas_incluidas[i].
        """
        sfreq = raw.info["sfreq"]
        first_sample, last_sample = raw.first_samp, raw.last_samp

        letters = sorted({w["letter"] for w in windows})
        letter_codes = {letter: idx + 1 for idx, letter in enumerate(letters)}

        included: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        events = []

        for window in windows:
            start_sample = int(round(window["start"] * sfreq))
            end_sample = int(round((window["start"] + common_duration) * sfreq))
            if not (first_sample <= start_sample <= end_sample <= last_sample):
                skipped.append(window)
                continue

            events.append([start_sample, 0, letter_codes[window["letter"]]])
            included.append(window)

        if not included:
            return None, included, skipped


        self._full_epocas = epochs = mne.Epochs(
                    raw, np.array(events, dtype=int), event_id=letter_codes,
                    tmin=0, tmax=common_duration, baseline=None,
                    reject=None, preload=True, verbose=False,
                )
        epochs = mne.Epochs(
            raw, np.array(events, dtype=int), event_id=letter_codes,
            tmin=0, tmax=common_duration, baseline=None,
            reject={"eeg": self.reject_threshold}, preload=True, verbose=False,
        )
        return epochs, included, skipped

    # ── Evaluación pico a pico por trial ──────────────────────────────

    def evaluate(self) -> list[dict[str, Any]]:
        """
        Corre (una única vez, con memoización) la evaluación de amplitud pico
        a pico, vía un único mne.Epochs (self._cleaned_epocas) con
        reject={"eeg": ...} + drop_log.

        Devuelve una lista de dicts, uno por trial, con: trial_id, letter,
        start, end, duration, status ('aceptado' | 'rechazado' |
        'ventana_invalida' | 'fuera_de_rango'), rejected (bool | None, None
        si no se pudo evaluar) y channels (canales EEG responsables del
        rechazo).
        """
        if self._trials is not None:
            return self._trials

        raw = self._ensure_raw()
        windows = self._trial_windows()

        invalid_windows = [w for w in windows if (w["end"] - w["start"]) <= 0]
        ok_windows = [w for w in windows if (w["end"] - w["start"]) > 0]

        common_duration = self._compute_common_duration(ok_windows)
        epochs, included, skipped = self._build_combined_epochs(raw, ok_windows, common_duration)

        results_by_trial_id: dict[int, dict[str, Any]] = {}

        for window in invalid_windows:
            results_by_trial_id[window["trial_id"]] = self._trial_result(
                window["trial_id"], window["letter"], window["start"], window["end"],
                window["end"] - window["start"], "ventana_invalida",
            )

        for window in skipped:
            results_by_trial_id[window["trial_id"]] = self._trial_result(
                window["trial_id"], window["letter"], window["start"], window["end"],
                window["end"] - window["start"], "fuera_de_rango",
            )

        if epochs is not None:
            for window, drop_reasons in zip(included, epochs.drop_log):
                rejected = len(drop_reasons) > 0
                result = self._trial_result(
                    window["trial_id"], window["letter"], window["start"], window["end"],
                    window["end"] - window["start"], "rechazado" if rejected else "aceptado",
                )
                result["rejected"] = rejected
                result["channels"] = list(drop_reasons) if rejected else []
                results_by_trial_id[window["trial_id"]] = result

        results = [results_by_trial_id[w["trial_id"]] for w in windows]

        self._trials = results
        self._cleaned_epocas = epochs
        self._common_duration = common_duration
        return results

    @staticmethod
    def _trial_result(trial_id, letter, start, end, duration, status) -> dict[str, Any]:
        return {
            "trial_id": trial_id,
            "letter": letter,
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(duration, 3),
            "status": status,
            "rejected": None,
            "channels": [],
        }

    # ── Resúmenes ──────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        trials = self.evaluate()
        evaluated = [t for t in trials if t["rejected"] is not None]
        rejected = [t for t in evaluated if t["rejected"]]
        unprocessable = [t for t in trials if t["rejected"] is None]

        total = len(evaluated)
        n_rejected = len(rejected)
        pct = (n_rejected / total * 100) if total else 0.0

        return {
            "total_trials": total,
            "rejected_trials": n_rejected,
            "rejected_pct": f"{pct:.1f}%",
            "unprocessable_trials": len(unprocessable),
            "reject_threshold": f"{self.reject_threshold:.0f} µV",
            "common_duration_s": (
                f"{self._common_duration:.3f} s" if self._common_duration is not None else "Sin dato"
            ),
        }

    def rejected_trials_df(self) -> pd.DataFrame:
        rows = [
            {
                "Trial": t["trial_id"],
                "Letra": t["letter"],
                "Inicio (s)": t["start"],
                "Fin (s)": t["end"],
                "Duración (s)": t["duration"],
                "Canales responsables": ", ".join(t["channels"]),
            }
            for t in self.evaluate() if t["rejected"]
        ]
        return pd.DataFrame(rows)

    def channel_offenders_df(self) -> pd.DataFrame:
        counter: Counter = Counter()
        for t in self.evaluate():
            if t["rejected"]:
                counter.update(t["channels"])

        rows = [{"Canal": ch, "Trials rechazados": n} for ch, n in counter.most_common()]
        return pd.DataFrame(rows)

    # ── Contexto para ReportGenerator ─────────────────────────────────

    def to_context(self) -> dict[str, Any]:
        """
        Arma el fragmento de contexto listo para ReportGenerator.set_quality():
        quality_summary, quality_rejected_table, quality_channel_offenders_table.
        """
        context: dict[str, Any] = {"quality_summary": self.summary()}

        rejected_df = self.rejected_trials_df()
        if not rejected_df.empty:
            context["quality_rejected_table"] = rejected_df.to_html(
                index=False, classes="dataframe", border=0, escape=False
            )

        offenders_df = self.channel_offenders_df()
        if not offenders_df.empty:
            context["quality_channel_offenders_table"] = offenders_df.to_html(
                index=False, classes="dataframe", border=0, escape=False
            )

        return context


if __name__ == "__main__":
    import os

    from pyhwr.managers import GHiampDataManager, LSLDataManager

    subject_id = 4
    session_id = 1
    round_id = 5
    round_type = "Ejecutada"

    path = f"D:\\dataset\\DataBase\\sub-{subject_id:02d}\\ses-{session_id:02d}"
    file_stem = f"sub-{subject_id:02d}_ses-{session_id:02d}_task-{round_type.lower()}_run-{round_id:02d}_eeg"

    gmanager = GHiampDataManager(os.path.join(path, f"{file_stem}.hdf5"), normalize_time=True)
    lsl_manager = LSLDataManager(os.path.join(path, f"{file_stem}.xdf"))

    quality = ReportTrialsQuality(gmanager, lsl_manager, reject_threshold = 150)
    print(quality.summary())
    print(quality.rejected_trials_df())
    print(quality.channel_offenders_df())

    epocas = quality._full_epocas  # un único mne.Epochs con todos los trials
    epocas.plot(scalings=150)
    epocas.plot_image(combine="mean")
    # epocas['a'].average().plot()  # ejemplo: indexado por letra + promedio
