"""
Script para generar figuras de análisis para TECBIOTEC
AUTOR: BALDEZZARI Lucas
"""

import os
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path
from pyhwr.managers import LSLDataManager

## Configuración de archivos y colores

DATASET_PATH = r"D:\dataset"
OUTPUT_PATH  = r"D:\repos\pyhwr\figures"

SUBJECTS = {
    "s01": {"folder": "s1", "sub_code": "sub-01"},
    "s02": {"folder": "s2", "sub_code": "sub-02"},
}

EJECUTADA_RUNS = {
    "s01": ["run-05", "run-06", "run-07"],
    "s02": ["run-05", "run-06", "run-07"],
}

SUBJECT_COLORS = {
    "s01": "#316CF4",
    "s02": "#DF2D47",
}

RUN_COLORS = ["#4a90d9", "#e88c2a", "#2aad58"]

SES  = "ses-01"
TASK = "ejecutada"

np.random.seed(42)

## Funciones útiles
def _set_style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
        "figure.dpi": 100,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def _save_fig(fig, name):
    Path(OUTPUT_PATH).mkdir(parents=True, exist_ok=True)
    out = os.path.join(OUTPUT_PATH, name)
    fig.savefig(out, dpi=150, bbox_inches="tight")


def _letter_colormap(letters):
    cmap = plt.colormaps.get_cmap("tab20").resampled(len(letters))
    return {letter: cmap(i) for i, letter in enumerate(sorted(letters))}


#  Carga de datos ***********************************─

def load_subject_runs(subject_id, subject_info, runs):
    """
    Carga los archivos XDF de los runs indicados para un sujeto.
    Retorna dict {run_id: LSLDataManager}.
    """
    managers = {}
    folder   = subject_info["folder"]
    sub_code = subject_info["sub_code"]

    for run in runs:
        filename = f"{sub_code}_{SES}_task-{TASK}_{run}_eeg.xdf"
        filepath = os.path.join(DATASET_PATH, folder, filename)

        if not os.path.exists(filepath):
            logging.warning(f"Archivo no encontrado: {filepath}")
            continue

        try:
            print(f"  Cargando {subject_id}/{run}...")
            managers[run] = LSLDataManager(filepath)
        except Exception as e:
            logging.warning(f"Error al cargar {filepath}: {e}")

    return managers


def build_aggregated_df(managers_dict, subject_id):
    """
    Construye un DataFrame con pendown_delays y traces_duration de todos los runs.

    Columnas: subject | run | trial_id | letter | pendown_delay_s | trace_duration_s
    """
    rows = []
    for run_id, manager in managers_dict.items():
        for trial_id, pd_info in manager.pendown_delays.items():
            dur_info = manager.traces_duration.get(trial_id, {})
            rows.append({
                "subject":          subject_id,
                "run":              run_id,
                "trial_id":         trial_id,
                "letter":           pd_info["letter"],
                "pendown_delay_s":  pd_info.get("delay"),
                "trace_duration_s": dur_info.get("duration"),
            })
    return pd.DataFrame(rows)


def build_resumen_df(managers_dict, subject_id):
    """
    Construye DataFrames de resumen por letra y run.
    Retorna (resumen_delays_df, resumen_duration_df).
    """
    delay_frames    = []
    duration_frames = []

    for run_id, manager in managers_dict.items():
        df_d = manager.penDown_delays_resume()
        if not df_d.empty:
            df_d["run"] = run_id
            df_d["subject"] = subject_id
            delay_frames.append(df_d)

        df_dur = manager.tracesDuration_resume()
        if not df_dur.empty:
            df_dur["run"] = run_id
            df_dur["subject"] = subject_id
            duration_frames.append(df_dur)

    res_d   = pd.concat(delay_frames,    ignore_index=True) if delay_frames    else pd.DataFrame()
    res_dur = pd.concat(duration_frames, ignore_index=True) if duration_frames else pd.DataFrame()
    return res_d, res_dur


# Figura 1: Grilla de trazos de escritura *********************

def fig_traces(all_managers):
    """
    Guarda plot_all_traces para el run-05 de cada sujeto en archivos separados.
    """
    print("Generando Fig 1: Trazos de escritura...")

    for subject_id, managers in all_managers.items():
        rep_run = "run-05"
        if rep_run not in managers:
            if not managers:
                logging.warning(f"No hay runs disponibles para {subject_id}")
                continue
            rep_run = list(managers.keys())[0]

        manager = managers[rep_run]
        color   = SUBJECT_COLORS[subject_id]

        fig, axes = manager.plot_all_traces(
            figsize=(28, 12),
            line_color=color,
            point_color="#ffffff",
            point_size=3,
            line_width=8,
            hide_title=True,
            hide_axes=True,
            hide_ticks=True,
            hide_labels=True,
            hide_spines=True,
            show=False,
        )

        if fig is None:
            logging.warning(f"No hay trazos para {subject_id}/{rep_run}")
            continue

        fig.suptitle(
            f"Trazos de escritura — {subject_id.upper()} | {rep_run}",
            fontsize=15, fontweight="bold", y=1.01,
        )
        plt.tight_layout()
        _save_fig(fig, f"fig01_trazos_{subject_id}.png")
        plt.close(fig)


# Figura 2 y 3: Boxplots con jitter *********************

def _boxplot_by_letter(ax, all_df, metric_col, subject_id, ylabel, color):
    """
    Dibuja boxplots + jitter por letra para un sujeto en el eje dado.
    """
    sub_df  = all_df[all_df["subject"] == subject_id].dropna(subset=[metric_col])
    letters = sorted(sub_df["letter"].unique())
    data_by_letter = [sub_df[sub_df["letter"] == l][metric_col].values for l in letters]

    bp = ax.boxplot(
        data_by_letter,
        positions=range(len(letters)),
        patch_artist=True,
        widths=0.5,
        medianprops=dict(color="black", linewidth=2),
        boxprops=dict(facecolor=color, alpha=0.45),
        whiskerprops=dict(linewidth=1.5, color=color),
        capprops=dict(linewidth=1.5, color=color),
        flierprops=dict(marker="", markersize=0),
    )

    for i, (letter, data) in enumerate(zip(letters, data_by_letter)):
        jitter = np.random.normal(i, 0.08, size=len(data))
        ax.scatter(jitter, data, color=color, alpha=0.35, s=9, zorder=3)

    global_mean = sub_df[metric_col].mean()
    ax.axhline(global_mean, linestyle="--", color="#555555", linewidth=1.2, alpha=0.7,
               label=f"Media global: {global_mean:.2f} s")

    ax.set_xticks(range(len(letters)))
    ax.set_xticklabels(letters, fontsize=10)
    ax.set_xlabel("Letra")
    ax.set_ylabel(ylabel)
    ax.set_title(subject_id.upper())
    ax.legend(fontsize=9)
    ax.set_xlim(-0.7, len(letters) - 0.3)


def fig_pendown_delays(all_df):
    print("Generando Fig 2: Pendown Delays...")
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
    fig.suptitle("Tiempo de reacción al cue (Pendown Delay) por letra",
                 fontsize=14, fontweight="bold")

    for ax, subject_id in zip(axes, SUBJECTS.keys()):
        _boxplot_by_letter(ax, all_df, "pendown_delay_s", subject_id,
                           "Delay (s)", SUBJECT_COLORS[subject_id])

    plt.tight_layout()
    _save_fig(fig, "fig02_pendown_delays.png")
    plt.close(fig)


def fig_traces_duration(all_df):
    print("Generando Fig 3: Duración de Trazos...")
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
    fig.suptitle("Duración de escritura por letra", fontsize=14, fontweight="bold")

    for ax, subject_id in zip(axes, SUBJECTS.keys()):
        _boxplot_by_letter(ax, all_df, "trace_duration_s", subject_id,
                           "Duración (s)", SUBJECT_COLORS[subject_id])

    plt.tight_layout()
    _save_fig(fig, "fig03_traces_duration.png")
    plt.close(fig)


# Figura 4: Evolución trial-a-trial *********************

def fig_trial_evolution(all_df):
    """
    Línea de pendown delay suavizado (rolling mean 5) más dispersión por trial.
    Una línea por run, dos paneles (s01 | s02).
    """
    print("Generando Fig 4: Evolución trial-a-trial...")

    fig, axes = plt.subplots(1, 2, figsize=(16, 5), sharey=True)
    fig.suptitle("Evolución del pendown delay a lo largo de los trials",
                 fontsize=14, fontweight="bold")

    for ax, subject_id in zip(axes, SUBJECTS.keys()):
        sub_df = all_df[all_df["subject"] == subject_id].dropna(subset=["pendown_delay_s"])
        runs   = sorted(sub_df["run"].unique())

        for run_idx, run_id in enumerate(runs):
            run_df  = sub_df[sub_df["run"] == run_id].sort_values("trial_id").reset_index(drop=True)
            color   = RUN_COLORS[run_idx % len(RUN_COLORS)]
            x_vals  = range(len(run_df))
            smoothed = run_df["pendown_delay_s"].rolling(5, min_periods=1).mean()

            ax.scatter(x_vals, run_df["pendown_delay_s"],
                       color=color, s=10, alpha=0.30, zorder=2)
            ax.plot(x_vals, smoothed, color=color, linewidth=2,
                    label=run_id, zorder=3)

        ax.set_xlabel("N° de trial")
        ax.set_ylabel("Pendown delay (s)")
        ax.set_title(subject_id.upper())
        ax.legend(fontsize=9, loc="upper right")
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    plt.tight_layout()
    _save_fig(fig, "fig04_trial_evolution.png")
    plt.close(fig)


#  Figura 5: Heatmap letra × run ****************************

def fig_heatmap(resumen_delays, resumen_duration):
    """
    Grilla 2×2: (delay | duración) × (s01 | s02).
    Filas = letras, columnas = runs, color = media.
    """
    print("Generando Fig 5: Heatmap resumen...")

    if resumen_delays.empty and resumen_duration.empty:
        logging.warning("Sin datos de resumen para el heatmap.")
        return

    subjects = sorted(set(
        list(resumen_delays.get("subject", pd.Series()).unique()) +
        list(resumen_duration.get("subject", pd.Series()).unique())
    ))

    metrics = [
        (resumen_delays,   "mean", "Pendown Delay medio (s)",    "YlOrRd"),
        (resumen_duration, "mean", "Duración de Trazo media (s)", "YlGnBu"),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Resumen por letra y run", fontsize=14, fontweight="bold")

    for col_idx, (df, value_col, title, cmap_name) in enumerate(metrics):
        for row_idx, subject_id in enumerate(subjects):
            ax = axes[row_idx][col_idx]

            if df.empty or "subject" not in df.columns:
                ax.axis("off")
                continue

            sub_df = df[df["subject"] == subject_id]
            if sub_df.empty:
                ax.axis("off")
                continue

            pivot = sub_df.pivot_table(
                values=value_col, index="letter", columns="run", aggfunc="mean"
            ).sort_index()

            vmin = pivot.values[~np.isnan(pivot.values)].min() if pivot.values.size else 0
            vmax = pivot.values[~np.isnan(pivot.values)].max() if pivot.values.size else 1

            im = ax.imshow(
                pivot.values, aspect="auto", cmap=cmap_name,
                vmin=vmin, vmax=vmax, interpolation="nearest",
            )

            for i in range(pivot.shape[0]):
                for j in range(pivot.shape[1]):
                    val = pivot.values[i, j]
                    if not np.isnan(val):
                        txt_color = "white" if val > (vmin + (vmax - vmin) * 0.65) else "black"
                        ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                                fontsize=9, color=txt_color, fontweight="bold")

            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels(pivot.columns, fontsize=9, rotation=30, ha="right")
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels(pivot.index, fontsize=9)
            ax.set_title(f"{subject_id.upper()} — {title}", fontsize=11)
            ax.set_xlabel("Run")
            ax.set_ylabel("Letra")
            ax.grid(False)
            plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04)

    plt.tight_layout()
    _save_fig(fig, "fig05_heatmap.png")
    plt.close(fig)


#  Figura 6: Scatter correlación delay vs duración *********************

def fig_scatter_corr(all_df):
    """
    Scatter pendown_delay vs trace_duration coloreado por letra.
    Línea de regresión y R² anotado. Dos paneles (s01 | s02).
    """
    print("Generando Fig 6: Scatter correlación...")

    letters          = sorted(all_df["letter"].dropna().unique())
    letter_colors_map = _letter_colormap(letters)

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle("Correlación: Pendown Delay vs Duración del Trazo",
                 fontsize=14, fontweight="bold")

    for ax, subject_id in zip(axes, SUBJECTS.keys()):
        sub_df = all_df[all_df["subject"] == subject_id].dropna(
            subset=["pendown_delay_s", "trace_duration_s"]
        )

        for letter in letters:
            l_df = sub_df[sub_df["letter"] == letter]
            ax.scatter(
                l_df["pendown_delay_s"], l_df["trace_duration_s"],
                color=letter_colors_map[letter], s=28, alpha=0.65,
                label=letter, edgecolors="none",
            )

        x_all = sub_df["pendown_delay_s"].values
        y_all = sub_df["trace_duration_s"].values

        if len(x_all) >= 2:
            coeffs = np.polyfit(x_all, y_all, 1)
            poly   = np.poly1d(coeffs)
            x_line = np.linspace(x_all.min(), x_all.max(), 200)
            ax.plot(x_line, poly(x_line), "k--", linewidth=1.5, alpha=0.55)
            r2 = np.corrcoef(x_all, y_all)[0, 1] ** 2
            ax.text(
                0.97, 0.05, f"R² = {r2:.3f}",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=10,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
            )

        ax.set_xlabel("Pendown delay (s)")
        ax.set_ylabel("Duración del trazo (s)")
        ax.set_title(subject_id.upper())
        ax.legend(
            fontsize=8, ncol=2, loc="upper left",
            title="Letra", title_fontsize=9,
            framealpha=0.8,
        )

    plt.tight_layout()
    _save_fig(fig, "fig06_scatter_corr.png")
    plt.close(fig)


#  Main ******************************************

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    _set_style()

    # ─ Carga ******************************************─
    print("=" * 55)
    print("  PyHWR - Analisis para Congreso")
    print("=" * 55)

    all_managers: dict[str, dict] = {}
    for subject_id, subject_info in SUBJECTS.items():
        print(f"\nSujeto: {subject_id}")
        all_managers[subject_id] = load_subject_runs(
            subject_id, subject_info, EJECUTADA_RUNS[subject_id]
        )

    # ─ DataFrames ***********************************─
    print("\n-- Construyendo DataFrames --")
    agg_frames          = []
    res_delay_frames    = []
    res_duration_frames = []

    for subject_id, managers in all_managers.items():
        agg_df        = build_aggregated_df(managers, subject_id)
        res_d, res_dur = build_resumen_df(managers, subject_id)
        agg_frames.append(agg_df)
        res_delay_frames.append(res_d)
        res_duration_frames.append(res_dur)

    all_df      = pd.concat(agg_frames,          ignore_index=True)
    resumen_d   = pd.concat(res_delay_frames,    ignore_index=True)
    resumen_dur = pd.concat(res_duration_frames, ignore_index=True)

    print(f"\nTrials cargados: {len(all_df)}")
    counts = all_df.groupby(["subject", "run"])["trial_id"].count()
    print(counts.to_string())

    # ─ Figuras ******************************************─
    print("\n-- Generando figuras --")
    fig_traces(all_managers)
    fig_pendown_delays(all_df)
    fig_traces_duration(all_df)
    fig_trial_evolution(all_df)
    fig_heatmap(resumen_d, resumen_dur)
    fig_scatter_corr(all_df)

    print(f"\nOK - Figuras guardadas en: {OUTPUT_PATH}")
