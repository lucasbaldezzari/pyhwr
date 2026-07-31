from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np

if TYPE_CHECKING:
    from pyhwr.managers import LSLDataManager


class ReportFigureGenerator:
    """
    Genera las figuras de trazos/tiempos de escritura que ReportGenerator
    embebe en el reporte HTML, para un sujeto/ronda particular.

    Cada gráfica se genera únicamente si el LSLDataManager tiene los datos de
    los que depende (coordinates_info, traces_duration). No se discrimina por
    tipo de ronda: en una ronda Imaginada esos datos están vacíos, así que las
    gráficas correspondientes simplemente no se generan.
    """

    def __init__(self, lsl_manager: "LSLDataManager", figures_dir: Path | str, file_prefix: str) -> None:
        self.manager = lsl_manager
        self.figures_dir = Path(figures_dir)
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        self.file_prefix = file_prefix

    def _save(self, fig, suffix: str) -> Path:
        path = self.figures_dir / f"{self.file_prefix}_{suffix}.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    def generate_all_traces(self, **plot_kwargs) -> Path | None:
        """
        Grilla letra x trial con el trazo de cada trial en su propio panel
        (referencia completa). Delega en LSLDataManager.plot_all_traces.
        """
        fig, _ = self.manager.plot_all_traces(show=False, **plot_kwargs)
        if fig is None:
            return None

        return self._save(fig, "all_traces")

    def generate_traces_by_letter(
        self,
        panel_size: tuple[float, float] = (4, 4),
        line_color: str = "#9d1212",
        line_width: float = 3,
        alpha: float = 0.35,
    ) -> Path | None:
        """
        Un panel por letra, superponiendo (semi-transparente) los trazos de
        todos los trials de esa letra en el mismo eje.
        """
        if not self.manager.coordinates_info:
            return None

        trials_by_letter: dict[str, list] = defaultdict(list)
        for trial_id, info in self.manager.coordinates_info.items():
            trials_by_letter[info["letter"]].append(trial_id)

        letters = sorted(trials_by_letter.keys())
        if not letters:
            return None

        width, height = panel_size
        fig, axes = plt.subplots(1, len(letters), figsize=(width * len(letters), height))
        axes = [axes] if len(letters) == 1 else list(axes)

        plotted_any = False
        for ax, letter in zip(axes, letters):
            for trial_id in trials_by_letter[letter]:
                coords = self.manager.getTrialCoordinates(trial_id)
                if self.manager.is_none_like(coords):
                    continue

                x, y = coords[:, 0], coords[:, 1]
                ax.plot(x, y, color=line_color, linewidth=line_width, alpha=alpha, zorder=1)
                plotted_any = True

            ax.set_title(f"Letra {letter}")
            ax.invert_yaxis()
            ax.axis("equal")
            ax.axis("off")

        if not plotted_any:
            plt.close(fig)
            return None

        plt.tight_layout()
        return self._save(fig, "trazos_por_letra")

    def generate_duration_histogram(self, bins: int = 10, color: str = "#316CF4") -> Path | None:
        """Histograma de duración de escritura (traces_duration) por trial."""
        durations = [
            info["duration"]
            for info in self.manager.traces_duration.values()
            if info.get("duration") is not None
        ]
        if not durations:
            return None

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(durations, bins=bins, color=color, edgecolor="white")
        ax.set_xlabel("Duración (s)")
        ax.set_ylabel("Cantidad de trials")
        ax.set_title("Distribución de duración de escritura")

        return self._save(fig, "duracion")

    def _boxplot_by_letter(
        self,
        ax,
        data_by_trial: dict,
        value_key: str,
        ylabel: str,
        color: str,
    ) -> bool:
        """
        Dibuja un boxplot + dispersión (jitter) por letra en el eje dado, a
        partir de un dict {trialID: {"letter": str, value_key: float | None}}.
        Devuelve False (sin dibujar nada) si no hay valores disponibles.
        """
        rows = [
            (info["letter"], info[value_key])
            for info in data_by_trial.values()
            if info.get(value_key) is not None
        ]
        if not rows:
            return False

        letters = sorted({letter for letter, _ in rows})
        data_by_letter = [[v for l, v in rows if l == letter] for letter in letters]

        ax.boxplot(
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

        for i, values in enumerate(data_by_letter):
            jitter = np.random.normal(i, 0.08, size=len(values))
            ax.scatter(jitter, values, color=color, alpha=0.35, s=9, zorder=3)

        ax.set_xticks(range(len(letters)))
        ax.set_xticklabels(letters, fontsize=10)
        ax.set_xlabel("Letra")
        ax.set_ylabel(ylabel)
        ax.set_xlim(-0.7, len(letters) - 0.3)
        return True

    def generate_pendown_delay_boxplot(self, color: str = "#9d1212") -> Path | None:
        """Boxplot + dispersión del pendown delay por letra."""
        fig, ax = plt.subplots(figsize=(8, 6))
        if not self._boxplot_by_letter(ax, self.manager.pendown_delays, "delay", "Delay (s)", color):
            plt.close(fig)
            return None

        ax.set_title("Tiempo de reacción al cue (Pendown Delay) por letra")
        return self._save(fig, "pendown_delays")

    def generate_traces_duration_boxplot(self, color: str = "#316CF4") -> Path | None:
        """Boxplot + dispersión de la duración de escritura por letra."""
        fig, ax = plt.subplots(figsize=(8, 6))
        if not self._boxplot_by_letter(ax, self.manager.traces_duration, "duration", "Duración (s)", color):
            plt.close(fig)
            return None

        ax.set_title("Duración de escritura por letra")
        return self._save(fig, "traces_duration")

    def generate_letter_summary_heatmap(self) -> Path | None:
        """
        Heatmap de resumen por letra: media de pendown delay y de duración de
        trazo (una columna, la ronda actual).
        """
        resumen_delay = self.manager.penDown_delays_resume()
        resumen_duration = self.manager.tracesDuration_resume()
        if resumen_delay.empty and resumen_duration.empty:
            return None

        metrics = [
            (resumen_duration, "Duración de Trazo media (s)", "YlGnBu"),
            (resumen_delay, "Pendown Delay medio (s)", "YlOrRd"),
        ]

        fig, axes = plt.subplots(1, 2, figsize=(9, 6))
        fig.suptitle("Resumen por letra", fontsize=14, fontweight="bold")

        plotted_any = False
        for ax, (df, title, cmap_name) in zip(axes, metrics):
            if df.empty:
                ax.axis("off")
                continue

            pivot = df.set_index("letter")[["mean"]].sort_index()
            values = pivot.values
            finite = values[~np.isnan(values)]
            vmin = finite.min() if finite.size else 0
            vmax = finite.max() if finite.size else 1

            im = ax.imshow(values, aspect="auto", cmap=cmap_name, vmin=vmin, vmax=vmax, interpolation="nearest")

            for i, val in enumerate(values[:, 0]):
                if not np.isnan(val):
                    txt_color = "white" if val > (vmin + (vmax - vmin) * 0.65) else "black"
                    ax.text(0, i, f"{val:.2f}", ha="center", va="center",
                            fontsize=9, color=txt_color, fontweight="bold")

            ax.set_xticks([0])
            ax.set_xticklabels(["actual"], fontsize=9)
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels(pivot.index, fontsize=9)
            ax.set_title(title, fontsize=11)
            ax.set_ylabel("Letra")
            ax.grid(False)
            plt.colorbar(im, ax=ax, fraction=0.05, pad=0.04)
            plotted_any = True

        if not plotted_any:
            plt.close(fig)
            return None

        plt.tight_layout()
        return self._save(fig, "letter_heatmap")

    def generate_delay_duration_scatter(self) -> Path | None:
        """
        Scatter duración del trazo (eje x) vs pendown delay (eje y) por
        trial, coloreado por letra, con recta de regresión y R².
        """
        rows = []
        for trial_id, delay_info in self.manager.pendown_delays.items():
            duration_info = self.manager.traces_duration.get(trial_id, {})
            delay = delay_info.get("delay")
            duration = duration_info.get("duration")
            if delay is None or duration is None:
                continue
            rows.append((delay_info["letter"], duration, delay))

        if not rows:
            return None

        letters = sorted({letter for letter, _, _ in rows})
        cmap = plt.colormaps.get_cmap("tab20").resampled(len(letters))
        letter_colors = {letter: cmap(i) for i, letter in enumerate(letters)}

        fig, ax = plt.subplots(figsize=(8, 6))
        for letter in letters:
            durations = [d for l, d, _ in rows if l == letter]
            delays = [y for l, _, y in rows if l == letter]
            ax.scatter(durations, delays, color=letter_colors[letter], s=28,
                       alpha=0.65, label=letter, edgecolors="none")

        durations_all = np.array([d for _, d, _ in rows])
        delays_all = np.array([y for _, _, y in rows])

        if len(durations_all) >= 2:
            coeffs = np.polyfit(durations_all, delays_all, 1)
            poly = np.poly1d(coeffs)
            x_line = np.linspace(durations_all.min(), durations_all.max(), 200)
            ax.plot(x_line, poly(x_line), "k--", linewidth=1.5, alpha=0.55)
            r2 = np.corrcoef(durations_all, delays_all)[0, 1] ** 2
            ax.text(
                0.97, 0.05, f"R² = {r2:.3f}",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=10,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
            )

        ax.set_xlabel("Duración del trazo (s)")
        ax.set_ylabel("Pendown delay (s)")
        ax.set_title("Correlación: Duración del trazo vs Pendown Delay")
        ax.legend(fontsize=8, ncol=2, loc="upper left", title="Letra",
                  title_fontsize=9, framealpha=0.8)

        return self._save(fig, "delay_duration_scatter")

    def generate_all(self) -> dict:
        """
        Genera todas las figuras disponibles y arma el fragmento de contexto
        (trace_plot_path, trace_extra_plots, other_graphs) listo para usar en
        ReportGenerator/context.json. Las claves para las que no hay datos no
        se incluyen.
        """
        context: dict = {}

        all_traces_path = self.generate_all_traces(
            hide_title=True, hide_ticks=True, hide_labels=True, hide_spines=True,
        )
        if all_traces_path is not None:
            context["trace_plot_path"] = f"../figures/{all_traces_path.name}"
            context["trace_plot_caption"] = "Trazos individuales de cada trial."

        by_letter_path = self.generate_traces_by_letter()
        if by_letter_path is not None:
            context["trace_extra_plots"] = [{
                "title": "Trazos por letra (trials superpuestos)",
                "path": f"../figures/{by_letter_path.name}",
                "caption": "Todos los trials de cada letra, superpuestos en un mismo eje.",
            }]

        other_graphs = []

        duration_path = self.generate_duration_histogram()
        if duration_path is not None:
            other_graphs.append({
                "title": "Distribución de duración",
                "path": f"../figures/{duration_path.name}",
                "caption": "Histograma de tiempos de escritura.",
                "description": "Distribución de la duración de los trials.",
            })

        pendown_boxplot_path = self.generate_pendown_delay_boxplot()
        if pendown_boxplot_path is not None:
            other_graphs.append({
                "title": "Pendown delay por letra",
                "path": f"../figures/{pendown_boxplot_path.name}",
                "caption": "Tiempo de reacción al cue por letra.",
                "description": "Boxplot con dispersión de trials por letra.",
            })

        duration_boxplot_path = self.generate_traces_duration_boxplot()
        if duration_boxplot_path is not None:
            other_graphs.append({
                "title": "Duración de escritura por letra",
                "path": f"../figures/{duration_boxplot_path.name}",
                "caption": "Duración del trazo por letra.",
                "description": "Boxplot con dispersión de trials por letra.",
            })

        heatmap_path = self.generate_letter_summary_heatmap()
        if heatmap_path is not None:
            other_graphs.append({
                "title": "Resumen por letra",
                "path": f"../figures/{heatmap_path.name}",
                "caption": "Media de pendown delay y duración de trazo por letra.",
                "description": "Heatmap de resumen por letra para la ronda actual.",
            })

        scatter_path = self.generate_delay_duration_scatter()
        if scatter_path is not None:
            other_graphs.append({
                "title": "Correlación delay vs duración",
                "path": f"../figures/{scatter_path.name}",
                "caption": "Duración del trazo vs pendown delay por trial.",
                "description": "Cada punto es un trial, coloreado por letra, con recta de regresión y R².",
            })

        if other_graphs:
            context["other_graphs"] = other_graphs

        return context


if __name__ == "__main__":
    import os

    from pyhwr.managers import LSLDataManager
    from pyhwr.report.ReportGenerator import _resolve_base_dir

    subject_id = 6
    session_id = 1
    round_id = 5
    round_type = "Ejecutada"

    path = f"D:\\dataset\\DataBase\\sub-{subject_id:02d}\\ses-{session_id:02d}"
    lsl_filename = f"sub-{subject_id:02d}_ses-{session_id:02d}_task-{round_type.lower()}_run-{round_id:02d}_eeg.xdf"
    lsl_manager = LSLDataManager(os.path.join(path, lsl_filename))

    figures_dir = _resolve_base_dir() / "figures"
    file_prefix = f"sub-{subject_id:02d}_ses-{session_id:02d}_run-{round_id:02d}"

    figure_generator = ReportFigureGenerator(lsl_manager, figures_dir, file_prefix)
    print(figure_generator.generate_all())
