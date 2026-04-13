import numpy as np
np.set_printoptions(suppress=True)
import matplotlib.pyplot as plt
import seaborn as sns
from pyhwr.managers import LSLDataManager, GHiampDataManager
import pandas as pd
from typing import Dict, List, Tuple

def _mad(x: np.ndarray) -> float:
    """
    Median Absolute Deviation (MAD) no escalado (en mismas unidades que x).
    """
    med = np.median(x)
    return float(np.median(np.abs(x - med)))

def _robust_sigma_from_mad(mad: float) -> float:
    """
    Estimación robusta del desvío estándar asumiendo ruido ~ simétrico ~ gaussiano.
    sigma_robusto = 1.4826 * MAD
    """
    return 1.4826 * mad

def latency_jitter_stats(dif_ms: np.ndarray) -> dict:
    """
    Calcula métricas de latencia y jitter a partir de dif = (Laptop - Tablet) [ms].

    Retorna:
      - n: cantidad de muestras
      - latency_median_ms: latencia típica (mediana de dif)
      - latency_mean_ms: media (sólo informativa; sensible a outliers)
      - jitter_residuals_ms: residuales dif - mediana (útiles para análisis adicionales)
      - jitter_mad_ms: MAD de residuales (robusto)
      - jitter_sigma_rob_ms: 1.4826 * MAD (estimación robusta del std bajo normalidad)
      - jitter_std_ms: std clásico (no robusto)
      - jitter_mean_abs_ms: mean absolute deviation (promedio de |residual|)
      - jitter_p95_abs_ms: percentil 95 de |residual|
      - jitter_p99_abs_ms: percentil 99 de |residual|
      - jitter_iqr_ms: IQR = p75 - p25 de residuales
      - jitter_range_ms: (min residual, max residual)
      - jitter_max_abs_ms: max |residual|
    """
    dif_ms = np.asarray(dif_ms).astype(float)
    n = dif_ms.size
    if n == 0:
        raise ValueError("dif_ms está vacío.")

    lat_med = float(np.median(dif_ms))
    lat_mean = float(np.mean(dif_ms))

    resid = dif_ms - lat_med  # jitter alrededor de la latencia típica
    abs_resid = np.abs(resid)

    mad = _mad(resid)
    sigma_rob = _robust_sigma_from_mad(mad)
    std = float(np.std(resid, ddof=1)) if n > 1 else 0.0
    mean_abs = float(np.mean(abs_resid))

    p95_abs = float(np.percentile(abs_resid, 95))
    p99_abs = float(np.percentile(abs_resid, 99))
    q25, q75 = np.percentile(resid, [25, 75])
    iqr = float(q75 - q25)
    rmin, rmax = float(np.min(resid)), float(np.max(resid))
    max_abs = float(np.max(abs_resid))

    return dict(
        n=n,
        latency_median_ms=lat_med,
        latency_mean_ms=lat_mean,
        jitter_residuals_ms=resid,           # lo dejo por si querés graficar
        jitter_mad_ms=mad,
        jitter_sigma_rob_ms=sigma_rob,
        jitter_std_ms=std,
        jitter_mean_abs_ms=mean_abs,
        jitter_p95_abs_ms=p95_abs,
        jitter_p99_abs_ms=p99_abs,
        jitter_iqr_ms=iqr,
        jitter_range_ms=(rmin, rmax),
        jitter_max_abs_ms=max_abs,
    )

def summarize_for_report(stats: dict) -> str:
    """
    Genera una línea legible para reportes.
    """
    return (
        f"n={stats['n']}, "
        f"lat_med={stats['latency_median_ms']:.2f} ms, "
        f"jitter: MAD={stats['jitter_mad_ms']:.2f} ms "
        f"(sigma_rob={stats['jitter_sigma_rob_ms']:.2f} ms), "
        f"std={stats['jitter_std_ms']:.2f} ms, "
        f"p95|res|={stats['jitter_p95_abs_ms']:.2f} ms, "
        f"p99|res|={stats['jitter_p99_abs_ms']:.2f} ms, "
        f"range=[{stats['jitter_range_ms'][0]:.2f}, {stats['jitter_range_ms'][1]:.2f}] ms"
    )

def compare_runs(run_difs_ms: Dict[str, np.ndarray]) -> List[Tuple[str, dict]]:
    """
    Calcula las métricas para múltiples 'runs'.

    Parámetros:
      - run_difs_ms: dict nombre_run -> array dif_ms

    Retorna:
      - lista de (nombre_run, stats_dict) en el mismo orden de inserción.
    """
    out = []
    for name, dif in run_difs_ms.items():
        stats = latency_jitter_stats(dif)
        out.append((name, stats))
    return out

file = "test\\markers_test_data\\sueltos\\sub-P001_ses-S006_task-Default_run-001_testeo_timestamp.xdf"

lsl_manager = LSLDataManager(file)

lsl_trialLaptop = np.array(lsl_manager["Laptop_Markers", "trialStartTime", :]).reshape(-1)
lsl_trialTablet = np.array(lsl_manager["Tablet_Markers", "trialStartTime", :]).reshape(-1)
lsl_fadeOffLaptop = np.array(lsl_manager["Laptop_Markers", "trialFadeOffTime", :]).reshape(-1)
lsl_fadeOffTablet = np.array(lsl_manager["Tablet_Markers", "trialFadeOffTime", :]).reshape(-1)
lsl_cueTimeLaptop = np.array(lsl_manager["Laptop_Markers", "trialCueTime", :]).reshape(-1)
lsl_cueTimeTablet = np.array(lsl_manager["Tablet_Markers", "trialCueTime", :]).reshape(-1)
lsl_sessionStartLaptop = np.array(lsl_manager["Laptop_Markers", "sessionStartTime", :]).reshape(-1)[0]
lsl_sessionStartTablet = np.array(lsl_manager["Tablet_Markers", "sessionStartTime", :]).reshape(-1)[0]

min_len_trials = min(len(lsl_trialLaptop), len(lsl_trialTablet))
lsl_trialLaptop = lsl_trialLaptop[:min_len_trials]
lsl_trialTablet = lsl_trialTablet[:min_len_trials]

min_len_fadeoff = min(len(lsl_fadeOffLaptop), len(lsl_fadeOffTablet))
lsl_fadeOffLaptop = lsl_fadeOffLaptop[:min_len_fadeoff]
lsl_fadeOffTablet = lsl_fadeOffTablet[:min_len_fadeoff]

min_len_cue = min(len(lsl_cueTimeLaptop), len(lsl_cueTimeTablet))
lsl_cueTimeLaptop = lsl_cueTimeLaptop[:min_len_cue]
lsl_cueTimeTablet = lsl_cueTimeTablet[:min_len_cue]


dif = (lsl_cueTimeLaptop - lsl_cueTimeTablet)
mediana = np.median(dif)
dif - mediana

latency_jitter_stats(dif)