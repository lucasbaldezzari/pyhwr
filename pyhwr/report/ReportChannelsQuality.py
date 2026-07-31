from __future__ import annotations

from typing import Any, Sequence, TYPE_CHECKING

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray

if TYPE_CHECKING:
    import mne


# ── Funciones de calidad de canales ───────────────────────────────────
#
# Implementación tal como se especifica en "_hide_docs/Calidad de canales
# EEG.pdf" (págs. 17-27): métricas robustas por ventana temporal, pensadas
# para señal EEG ya filtrada (banda + notch), sfreq=1200 Hz, ventanas de 2 s
# con 50% de solapamiento.


def _validate_eeg_data(data: ArrayLike) -> NDArray[np.float64]:
    """
    Valida y convierte los datos EEG a un array float64.

    Parameters
    ----------
    data : array-like, shape (n_channels, n_samples)
        Señal EEG.

    Returns
    -------
    x : ndarray, shape (n_channels, n_samples)
        Datos convertidos a float64.
    """
    x = np.asarray(data, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError(
            "Los datos deben tener forma (n_channels, n_samples)."
        )
    if x.shape[0] < 1 or x.shape[1] < 2:
        raise ValueError("La matriz EEG no contiene suficientes datos.")

    return x


def _window_parameters(
    n_samples: int,
    sfreq: float,
    window_s: float,
    overlap: float,
) -> tuple[NDArray[np.int64], int, NDArray[np.float64]]:
    """
    Calcula los índices de inicio y los centros temporales de las ventanas.
    """
    if sfreq <= 0:
        raise ValueError("sfreq debe ser mayor que cero.")

    if window_s <= 0:
        raise ValueError("window_s debe ser mayor que cero.")

    if not 0 <= overlap < 1:
        raise ValueError("overlap debe estar en el intervalo [0, 1).")

    window_samples = int(round(window_s * sfreq))
    step_samples = int(round(window_samples * (1.0 - overlap)))

    if window_samples < 2:
        raise ValueError("La ventana debe contener al menos dos muestras.")

    if step_samples < 1:
        raise ValueError("El desplazamiento entre ventanas es demasiado pequeño.")

    if n_samples < window_samples:
        raise ValueError(
            f"La señal tiene {n_samples} muestras, pero la ventana requiere "
            f"{window_samples} muestras."
        )

    starts = np.arange(
        0,
        n_samples - window_samples + 1,
        step_samples,
        dtype=np.int64,
    )

    centers_s = (starts + window_samples / 2.0) / sfreq

    return starts, window_samples, centers_s


def robust_zscore(
    values: ArrayLike,
    axis: int,
    epsilon: float = 1e-15,
) -> NDArray[np.float64]:
    """
    Calcula un z-score robusto utilizando mediana y MAD.

    z = (x - mediana) / (1.4826 * MAD)

    Los resultados son NaN cuando la dispersión robusta es prácticamente cero.
    """
    x = np.asarray(values, dtype=np.float64)

    center = np.nanmedian(x, axis=axis, keepdims=True)
    mad = np.nanmedian(np.abs(x - center), axis=axis, keepdims=True)
    scale = 1.4826 * mad

    return np.divide(
        x - center,
        scale,
        out=np.full_like(x, np.nan),
        where=scale > epsilon,
    )


# 1. Pico a pico robusto ────────────────────────────────────────────────

def windowed_robust_peak_to_peak(
    data: ArrayLike,
    sfreq: float = 1200.0,
    window_s: float = 2.0,
    overlap: float = 0.5,
    q_low: float = 1.0,
    q_high: float = 99.0,
) -> dict[str, NDArray[np.float64]]:
    """
    Calcula el pico a pico convencional y robusto por canal y ventana.

    Parameters
    ----------
    data : array-like, shape (n_channels, n_samples)
        Señal EEG.
    sfreq : float
        Frecuencia de muestreo en Hz.
    window_s : float
        Duración de cada ventana en segundos.
    overlap : float
        Fracción de solapamiento entre ventanas.
    q_low, q_high : float
        Percentiles utilizados para el pico a pico robusto.

    Returns
    -------
    result : dict
        result["rp2p"] tiene forma (n_channels, n_windows).
        result["p2p"] contiene el pico a pico convencional.
        result["times"] contiene el centro de cada ventana en segundos.
    """
    x = _validate_eeg_data(data)

    if not 0 <= q_low < q_high <= 100:
        raise ValueError("Los percentiles deben cumplir 0 <= q_low < q_high <= 100.")

    starts, window_samples, times = _window_parameters(
        n_samples=x.shape[1],
        sfreq=sfreq,
        window_s=window_s,
        overlap=overlap,
    )

    n_channels = x.shape[0]
    n_windows = len(starts)

    rp2p = np.full((n_channels, n_windows), np.nan)
    p2p = np.full((n_channels, n_windows), np.nan)

    for w, start in enumerate(starts):
        segment = x[:, start : start + window_samples]

        q1 = np.nanpercentile(segment, q_low, axis=1)
        q99 = np.nanpercentile(segment, q_high, axis=1)

        rp2p[:, w] = q99 - q1
        p2p[:, w] = (
            np.nanmax(segment, axis=1)
            - np.nanmin(segment, axis=1)
        )

    return {
        "rp2p": rp2p,
        "p2p": p2p,
        "times": times,
        "starts": starts,
    }


# 2. MAD o amplitud robusta ─────────────────────────────────────────────

def windowed_mad_amplitude(
    data: ArrayLike,
    sfreq: float = 1200.0,
    window_s: float = 2.0,
    overlap: float = 0.5,
    scale_to_sigma: bool = True,
) -> dict[str, NDArray[np.float64]]:
    """
    Calcula la amplitud robusta mediante MAD por canal y ventana.

    Parameters
    ----------
    scale_to_sigma : bool
        Si es True, multiplica MAD por 1.4826 para aproximar la
        desviación estándar bajo una distribución normal.

    Returns
    -------
    result : dict
        mad : MAD escalado o no escalado.
        median : mediana temporal de cada ventana.
        times : centro temporal de las ventanas.
    """
    x = _validate_eeg_data(data)

    starts, window_samples, times = _window_parameters(
        n_samples=x.shape[1],
        sfreq=sfreq,
        window_s=window_s,
        overlap=overlap,
    )

    n_channels = x.shape[0]
    n_windows = len(starts)

    mad_values = np.full((n_channels, n_windows), np.nan)
    medians = np.full((n_channels, n_windows), np.nan)

    scale = 1.4826 if scale_to_sigma else 1.0

    for w, start in enumerate(starts):
        segment = x[:, start : start + window_samples]

        median = np.nanmedian(segment, axis=1)
        absolute_deviation = np.abs(segment - median[:, np.newaxis])

        mad = scale * np.nanmedian(absolute_deviation, axis=1)

        medians[:, w] = median
        mad_values[:, w] = mad

    return {
        "mad": mad_values,
        "median": medians,
        "times": times,
        "starts": starts,
    }


# 3. Canal plano o de muy baja variabilidad ─────────────────────────────

def detect_flat_or_low_variability(
    data: ArrayLike,
    sfreq: float = 1200.0,
    window_s: float = 2.0,
    overlap: float = 0.5,
    flat_epsilon: float | None = None,
    flat_fraction_threshold: float = 0.95,
    relative_mad_threshold: float = 0.10,
    robust_z_threshold: float = -5.0,
) -> dict[str, NDArray]:
    """
    Detecta canales planos o con variabilidad anormalmente baja.

    Parameters
    ----------
    flat_epsilon : float or None
        Una diferencia entre muestras consecutivas menor o igual a este valor
        se considera plana.

        Debe expresarse en las mismas unidades que los datos.

        Si es None, solo considera diferencias exactamente iguales a cero.

        Para datos MNE expresados en voltios podría probarse inicialmente
        con 1e-12, pero debería ajustarse según la resolución del amplificador.
    flat_fraction_threshold : float
        Fracción mínima de diferencias casi nulas para declarar una ventana
        plana.
    relative_mad_threshold : float
        Una ventana se considera de baja variabilidad cuando:

            MAD_canal / mediana_espacial_MAD < threshold
    robust_z_threshold : float
        Umbral inferior para el z-score robusto espacial del log(MAD).

    Returns
    -------
    result : dict
        flat_fraction : fracción de diferencias consecutivas casi nulas.
        relative_mad : MAD del canal dividido por la mediana espacial.
        z_log_mad : z-score robusto espacial.
        flat : máscara de ventanas planas.
        low_variability : máscara de variabilidad baja.
        bad : unión de ambos criterios.
    """
    x = _validate_eeg_data(data)

    starts, window_samples, times = _window_parameters(
        n_samples=x.shape[1],
        sfreq=sfreq,
        window_s=window_s,
        overlap=overlap,
    )

    n_channels = x.shape[0]
    n_windows = len(starts)

    flat_fraction = np.full((n_channels, n_windows), np.nan)
    mad_values = np.full((n_channels, n_windows), np.nan)

    for w, start in enumerate(starts):
        segment = x[:, start : start + window_samples]

        median = np.nanmedian(segment, axis=1)
        mad_values[:, w] = (
            1.4826
            * np.nanmedian(
                np.abs(segment - median[:, np.newaxis]),
                axis=1,
            )
        )

        differences = np.diff(segment, axis=1)
        valid = np.isfinite(differences)

        if flat_epsilon is None:
            nearly_flat = differences == 0.0
        else:
            nearly_flat = np.abs(differences) <= flat_epsilon

        numerator = np.sum(nearly_flat & valid, axis=1)
        denominator = np.sum(valid, axis=1)

        flat_fraction[:, w] = np.divide(
            numerator,
            denominator,
            out=np.full(n_channels, np.nan),
            where=denominator > 0,
        )

    epsilon = np.finfo(float).eps

    spatial_median_mad = np.nanmedian(
        mad_values,
        axis=0,
        keepdims=True,
    )

    relative_mad = np.divide(
        mad_values,
        spatial_median_mad,
        out=np.full_like(mad_values, np.nan),
        where=spatial_median_mad > epsilon,
    )

    log_mad = np.log(np.maximum(mad_values, epsilon))
    z_log_mad = robust_zscore(log_mad, axis=0)

    flat = flat_fraction >= flat_fraction_threshold

    low_variability = (
        (relative_mad < relative_mad_threshold)
        | (z_log_mad < robust_z_threshold)
    )

    bad = flat | low_variability

    return {
        "mad": mad_values,
        "flat_fraction": flat_fraction,
        "relative_mad": relative_mad,
        "z_log_mad": z_log_mad,
        "flat": flat,
        "low_variability": low_variability,
        "bad": bad,
        "times": times,
        "starts": starts,
    }


# 4. No estacionariedad ──────────────────────────────────────────────────

def windowed_nonstationarity(
    data: ArrayLike,
    sfreq: float = 1200.0,
    window_s: float = 2.0,
    overlap: float = 0.5,
    robust_z_threshold: float = 5.0,
    minimum_ratio: float = 2.0,
) -> dict[str, NDArray]:
    """
    Cuantifica cambios abruptos de amplitud y potencia entre ventanas.

    La función calcula:
    - MAD por ventana.
    - Potencia media cuadrática por ventana.
    - Razón de MAD entre ventanas consecutivas.
    - Razón de potencia entre ventanas consecutivas.
    - Z-scores robustos temporales y espaciales de dichos cambios.

    Parameters
    ----------
    minimum_ratio : float
        Cambio multiplicativo mínimo requerido para marcar una transición.
        Por ejemplo, 2 significa duplicación o reducción a la mitad.
    robust_z_threshold : float
        Umbral para considerar atípico un cambio respecto de:
        - la historia del propio canal;
        - los demás canales en la misma transición.

    Returns
    -------
    result : dict
        Arrays de forma (n_channels, n_windows). La primera ventana no tiene
        una ventana previa, por lo que sus cambios son NaN y su flag es False.
    """
    x = _validate_eeg_data(data)

    starts, window_samples, times = _window_parameters(
        n_samples=x.shape[1],
        sfreq=sfreq,
        window_s=window_s,
        overlap=overlap,
    )

    n_channels = x.shape[0]
    n_windows = len(starts)

    mad_values = np.full((n_channels, n_windows), np.nan)
    power_values = np.full((n_channels, n_windows), np.nan)

    for w, start in enumerate(starts):
        segment = x[:, start : start + window_samples]

        median = np.nanmedian(segment, axis=1)

        mad_values[:, w] = (
            1.4826
            * np.nanmedian(
                np.abs(segment - median[:, np.newaxis]),
                axis=1,
            )
        )

        power_values[:, w] = np.nanmean(segment**2, axis=1)

    epsilon = np.finfo(float).eps

    log_mad = np.log(np.maximum(mad_values, epsilon))
    log_power = np.log(np.maximum(power_values, epsilon))

    # Cambio absoluto logarítmico entre ventanas consecutivas.
    delta_log_mad = np.abs(np.diff(log_mad, axis=1))
    delta_log_power = np.abs(np.diff(log_power, axis=1))

    # Equivale al mayor valor entre x_w/x_w-1 y x_w-1/x_w.
    mad_ratio = np.exp(delta_log_mad)
    power_ratio = np.exp(delta_log_power)

    # Atipicidad respecto de la historia del propio canal.
    z_mad_temporal = robust_zscore(delta_log_mad, axis=1)
    z_power_temporal = robust_zscore(delta_log_power, axis=1)

    # Atipicidad respecto de los demás canales en el mismo instante.
    z_mad_spatial = robust_zscore(delta_log_mad, axis=0)
    z_power_spatial = robust_zscore(delta_log_power, axis=0)

    mad_change_flag = (
        (mad_ratio >= minimum_ratio)
        & (
            (z_mad_temporal >= robust_z_threshold)
            | (z_mad_spatial >= robust_z_threshold)
        )
    )

    power_change_flag = (
        (power_ratio >= minimum_ratio)
        & (
            (z_power_temporal >= robust_z_threshold)
            | (z_power_spatial >= robust_z_threshold)
        )
    )

    transition_bad = mad_change_flag | power_change_flag

    # Se agrega una primera columna porque la primera ventana no tiene anterior.
    def prepend_nan(array: NDArray[np.float64]) -> NDArray[np.float64]:
        return np.concatenate(
            [
                np.full((array.shape[0], 1), np.nan),
                array,
            ],
            axis=1,
        )

    def prepend_false(array: NDArray[np.bool_]) -> NDArray[np.bool_]:
        return np.concatenate(
            [
                np.zeros((array.shape[0], 1), dtype=bool),
                array,
            ],
            axis=1,
        )

    return {
        "mad": mad_values,
        "power": power_values,
        "delta_log_mad": prepend_nan(delta_log_mad),
        "delta_log_power": prepend_nan(delta_log_power),
        "mad_ratio": prepend_nan(mad_ratio),
        "power_ratio": prepend_nan(power_ratio),
        "z_mad_temporal": prepend_nan(z_mad_temporal),
        "z_mad_spatial": prepend_nan(z_mad_spatial),
        "z_power_temporal": prepend_nan(z_power_temporal),
        "z_power_spatial": prepend_nan(z_power_spatial),
        "mad_change_flag": prepend_false(mad_change_flag),
        "power_change_flag": prepend_false(power_change_flag),
        "bad": prepend_false(transition_bad),
        "times": times,
        "starts": starts,
    }


# Función integradora ────────────────────────────────────────────────────

def compute_basic_channel_quality(
    data: ArrayLike,
    sfreq: float = 1200.0,
    window_s: float = 2.0,
    overlap: float = 0.5,
    amplitude_z_threshold: float = 5.0,
    relative_mad_threshold: float = 0.10,
    flat_fraction_threshold: float = 0.95,
    flat_epsilon: float | None = None,
    nonstationarity_z_threshold: float = 5.0,
    nonstationarity_minimum_ratio: float = 2.0,
) -> dict[str, NDArray]:
    """
    Ejecuta un control básico de calidad por canal y ventana.
    """
    rp2p_result = windowed_robust_peak_to_peak(
        data=data,
        sfreq=sfreq,
        window_s=window_s,
        overlap=overlap,
    )

    mad_result = windowed_mad_amplitude(
        data=data,
        sfreq=sfreq,
        window_s=window_s,
        overlap=overlap,
    )

    flat_result = detect_flat_or_low_variability(
        data=data,
        sfreq=sfreq,
        window_s=window_s,
        overlap=overlap,
        flat_epsilon=flat_epsilon,
        flat_fraction_threshold=flat_fraction_threshold,
        relative_mad_threshold=relative_mad_threshold,
        robust_z_threshold=-amplitude_z_threshold,
    )

    nonstationarity_result = windowed_nonstationarity(
        data=data,
        sfreq=sfreq,
        window_s=window_s,
        overlap=overlap,
        robust_z_threshold=nonstationarity_z_threshold,
        minimum_ratio=nonstationarity_minimum_ratio,
    )

    epsilon = np.finfo(float).eps

    rp2p = rp2p_result["rp2p"]
    mad = mad_result["mad"]

    z_log_rp2p = robust_zscore(
        np.log(np.maximum(rp2p, epsilon)),
        axis=0,
    )

    z_log_mad = robust_zscore(
        np.log(np.maximum(mad, epsilon)),
        axis=0,
    )

    high_amplitude = (
        (z_log_rp2p > amplitude_z_threshold)
        | (z_log_mad > amplitude_z_threshold)
    )

    low_amplitude = (
        (z_log_rp2p < -amplitude_z_threshold)
        | (z_log_mad < -amplitude_z_threshold)
    )

    amplitude_bad = high_amplitude | low_amplitude

    # Una ventana se considera mala si:
    # - el canal está plano o tiene variabilidad baja;
    # - presenta no estacionariedad;
    # - ambas métricas de amplitud indican atipicidad.
    bad_windows = (
        flat_result["bad"]
        | nonstationarity_result["bad"]
        | amplitude_bad
    )

    bad_fraction = np.mean(bad_windows, axis=1)

    return {
        "times": rp2p_result["times"],
        "rp2p": rp2p,
        "p2p": rp2p_result["p2p"],
        "mad": mad,
        "z_log_rp2p": z_log_rp2p,
        "z_log_mad": z_log_mad,
        "high_amplitude": high_amplitude,
        "low_amplitude": low_amplitude,
        "flat": flat_result["flat"],
        "low_variability": flat_result["low_variability"],
        "nonstationary": nonstationarity_result["bad"],
        "bad_windows": bad_windows,
        "bad_fraction": bad_fraction,
    }


# ── Clase de reporte ──────────────────────────────────────────────────

class ReportChannelsQuality:
    """
    Evalúa la calidad de los canales EEG (independiente de los trials),
    a partir de métricas robustas por ventana temporal: pico a pico robusto,
    amplitud robusta (MAD), canal plano/baja variabilidad y no
    estacionariedad. Ver _hide_docs/Calidad de canales EEG.pdf para el
    diseño completo de estas métricas.

    Espera una señal EEG ya filtrada (banda + notch) — reutiliza la que
    construye ReportTrialsQuality.get_eeg_raw(), para no repetir la
    selección de canales EEG ni el filtrado.

    Qué criterios entran en el % de "ventanas malas" (y por lo tanto en el
    estado de cada canal) es elegible vía el parámetro `methods`: por
    defecto se usan los cuatro descriptos en el PDF, pero se puede evaluar
    con un subconjunto (p. ej. solo amplitud, o todo menos no-estacionariedad
    si se sabe que da muchos falsos positivos en cierto experimento).
    """

    #: Criterios disponibles y su etiqueta legible para la tabla/resumen.
    _METHOD_LABELS: dict[str, str] = {
        "amplitude": "Amplitud atípica",
        "flat": "Plano",
        "low_variability": "Baja variabilidad",
        "nonstationary": "No estacionario",
    }
    _AVAILABLE_METHODS: tuple[str, ...] = tuple(_METHOD_LABELS)

    def __init__(
        self,
        eeg_raw: "mne.io.RawArray",
        methods: Sequence[str] | None = None,
        window_s: float = 2.0,
        overlap: float = 0.5,
        amplitude_z_threshold: float = 5.0,
        relative_mad_threshold: float = 0.10,
        flat_fraction_threshold: float = 0.95,
        flat_epsilon: float | None = None,
        nonstationarity_z_threshold: float = 5.0,
        nonstationarity_minimum_ratio: float = 2.0,
    ) -> None:
        """
        Parámetros
        ----------
        eeg_raw : mne.io.RawArray
            Señal EEG (solo canales EEG), ya filtrada en banda + notch.
        methods : Sequence[str] | None
            Subconjunto de criterios a combinar para decidir si una ventana
            es "mala": alguno de "amplitude", "flat", "low_variability",
            "nonstationary" (ver `ReportChannelsQuality.available_methods()`).
            None (default) usa los cuatro.
        window_s, overlap : float
            Duración de ventana (s) y fracción de solapamiento para todas
            las métricas.
        amplitude_z_threshold : float
            Umbral de z-score robusto (log rP2P / log MAD) para marcar
            amplitud atípica.
        relative_mad_threshold : float
            Umbral de MAD relativo a la mediana espacial para "baja
            variabilidad".
        flat_fraction_threshold : float
            Fracción mínima de diferencias casi nulas para declarar una
            ventana plana.
        flat_epsilon : float | None
            Tolerancia para considerar "casi nula" una diferencia entre
            muestras consecutivas (None → sólo diferencias exactamente 0).
        nonstationarity_z_threshold, nonstationarity_minimum_ratio : float
            Umbrales para marcar transiciones abruptas de amplitud/potencia
            entre ventanas consecutivas.
        """
        if methods is None:
            methods = self._AVAILABLE_METHODS

        methods = tuple(methods)
        invalid = sorted(set(methods) - set(self._AVAILABLE_METHODS))
        if invalid:
            raise ValueError(
                f"Método(s) desconocido(s): {invalid}. "
                f"Disponibles: {list(self._AVAILABLE_METHODS)}."
            )
        if not methods:
            raise ValueError("methods no puede estar vacío: elegí al menos un criterio.")

        self.eeg_raw = eeg_raw
        self.methods = methods
        self.window_s = window_s
        self.overlap = overlap
        self.amplitude_z_threshold = amplitude_z_threshold
        self.relative_mad_threshold = relative_mad_threshold
        self.flat_fraction_threshold = flat_fraction_threshold
        self.flat_epsilon = flat_epsilon
        self.nonstationarity_z_threshold = nonstationarity_z_threshold
        self.nonstationarity_minimum_ratio = nonstationarity_minimum_ratio

        self._result: dict[str, Any] | None = None
        self._ch_names: list[str] | None = None

    @classmethod
    def available_methods(cls) -> tuple[str, ...]:
        """Nombres válidos para el parámetro `methods` del constructor."""
        return cls._AVAILABLE_METHODS

    def evaluate(self) -> dict[str, Any]:
        """
        Corre (una única vez, con memoización) compute_basic_channel_quality
        sobre la señal EEG, y luego recombina "bad_windows"/"bad_fraction"
        usando únicamente los criterios elegidos en self.methods (en vez de
        los cuatro que compute_basic_channel_quality combina por defecto).

        Devuelve el dict de compute_basic_channel_quality con "bad_windows"/
        "bad_fraction" ya recalculados, más una clave adicional "criteria":
        {método: máscara (n_channels, n_windows)} con los cuatro criterios
        por separado, para inspección o para channels_df().
        """
        if self._result is not None:
            return self._result

        data = self.eeg_raw.get_data(picks="eeg")
        self._ch_names = self.eeg_raw.copy().pick("eeg").ch_names

        result = compute_basic_channel_quality(
            data=data,
            sfreq=self.eeg_raw.info["sfreq"],
            window_s=self.window_s,
            overlap=self.overlap,
            amplitude_z_threshold=self.amplitude_z_threshold,
            relative_mad_threshold=self.relative_mad_threshold,
            flat_fraction_threshold=self.flat_fraction_threshold,
            flat_epsilon=self.flat_epsilon,
            nonstationarity_z_threshold=self.nonstationarity_z_threshold,
            nonstationarity_minimum_ratio=self.nonstationarity_minimum_ratio,
        )

        criteria = {
            "amplitude": result["high_amplitude"] | result["low_amplitude"],
            "flat": result["flat"],
            "low_variability": result["low_variability"],
            "nonstationary": result["nonstationary"],
        }
        selected = np.stack([criteria[m] for m in self.methods], axis=0)
        bad_windows = np.any(selected, axis=0)

        result["criteria"] = criteria
        result["bad_windows"] = bad_windows
        result["bad_fraction"] = np.mean(bad_windows, axis=1)

        self._result = result
        return self._result

    @staticmethod
    def _status_from_fraction(fraction: float) -> str:
        """Cortes según _hide_docs/Calidad de canales EEG.pdf, pág. 28."""
        if fraction >= 0.30:
            return "Malo"
        if fraction >= 0.15:
            return "Problemático"
        if fraction >= 0.05:
            return "Revisar"
        return "Bueno"

    def channels_df(self) -> pd.DataFrame:
        """
        Tabla por canal: % de ventanas malas, estado (Bueno/Revisar/
        Problemático/Malo) y el subcriterio (entre los elegidos en
        self.methods) que más aportó a ese porcentaje, para que la tabla sea
        accionable y no sólo un número. Ordenada de peor a mejor.
        """
        result = self.evaluate()
        bad_fraction = result["bad_fraction"]
        criteria = result["criteria"]

        rows = []
        for idx, ch_name in enumerate(self._ch_names):
            method_fractions = {
                self._METHOD_LABELS[m]: criteria[m][idx].mean() for m in self.methods
            }
            main_issue = max(method_fractions, key=method_fractions.get) if bad_fraction[idx] > 0 else "-"

            rows.append({
                "Canal": ch_name,
                "% ventanas malas": round(float(bad_fraction[idx]) * 100, 1),
                "Estado": self._status_from_fraction(bad_fraction[idx]),
                "Criterio principal": main_issue,
            })

        df = pd.DataFrame(rows)
        return df.sort_values("% ventanas malas", ascending=False).reset_index(drop=True)

    def summary(self) -> dict[str, Any]:
        df = self.channels_df()
        counts = df["Estado"].value_counts()

        return {
            "total_channels": len(df),
            "good_channels": int(counts.get("Bueno", 0)),
            "review_channels": int(counts.get("Revisar", 0)),
            "problematic_channels": int(counts.get("Problemático", 0)),
            "bad_channels": int(counts.get("Malo", 0)),
            "window_s": f"{self.window_s:.1f} s",
            "amplitude_z_threshold": self.amplitude_z_threshold,
            "methods": ", ".join(self._METHOD_LABELS[m] for m in self.methods),
        }

    def to_context(self) -> dict[str, Any]:
        """
        Arma el fragmento de contexto listo para
        ReportGenerator.set_channels_quality(): channels_quality_summary,
        channels_quality_table, channels_quality_intro (lista los criterios
        usados).
        """
        methods_label = ", ".join(self._METHOD_LABELS[m] for m in self.methods)
        context: dict[str, Any] = {
            "channels_quality_summary": self.summary(),
            "channels_quality_intro": f"Evaluación basada en: {methods_label}.",
        }

        df = self.channels_df()
        if not df.empty:
            context["channels_quality_table"] = df.to_html(
                index=False, classes="dataframe", border=0, escape=False
            )

        return context


if __name__ == "__main__":
    import os

    from pyhwr.managers import GHiampDataManager, LSLDataManager
    from pyhwr.report.ReportTrialsQuality import ReportTrialsQuality

    subject_id = 6
    session_id = 1
    round_id = 6
    round_type = "Ejecutada"

    path = f"D:\\dataset\\DataBase\\sub-{subject_id:02d}\\ses-{session_id:02d}"
    file_stem = f"sub-{subject_id:02d}_ses-{session_id:02d}_task-{round_type.lower()}_run-{round_id:02d}_eeg"

    gmanager = GHiampDataManager(os.path.join(path, f"{file_stem}.hdf5"), normalize_time=True)
    lsl_manager = LSLDataManager(os.path.join(path, f"{file_stem}.xdf"))

    trials_quality = ReportTrialsQuality(gmanager, lsl_manager)
    channels_quality = ReportChannelsQuality(trials_quality.get_eeg_raw(),
                                             methods=["amplitude","flat","low_variability"])

    print(channels_quality.summary())
    print(channels_quality.channels_df())
