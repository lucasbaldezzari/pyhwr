from __future__ import annotations

import importlib.util
import json
from multiprocessing import context
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


def _resolve_base_dir() -> Path:
    """
    Ubica la carpeta de pyhwr.report vía su spec de import en vez de __file__,
    para que funcione tanto ejecutando el archivo (F5) como pegando/corriendo
    el código línea por línea en una Terminal/Interactive Window (donde
    __file__ no está definido).
    """
    spec = importlib.util.find_spec("pyhwr.report")
    if spec is None or spec.origin is None:
        raise ModuleNotFoundError(
            "No se pudo localizar el paquete 'pyhwr.report'. "
            "Verificá que 'pyhwr' esté instalado o en el PYTHONPATH."
        )
    return Path(spec.origin).resolve().parent


class ReportGenerator:
    def __init__(self) -> None:
        self.base_dir = _resolve_base_dir()

        # Rutas absolutas derivadas de base_dir
        self.context_path = self.base_dir / "context.json"
        self.templates_dir = self.base_dir / "templates"
        self.template_path = self.templates_dir / "report_template.html"
        self.output_dir = self.base_dir / "output"
        self.output_html_path: Path | None = None

        # context["lsl_tables"][0]["html"] = df_lsl.to_html(index=False, classes="dataframe")
        # context["gtec_tables"][0]["html"] = df_gtec.to_html(index=False, classes="dataframe")

        # Crear output si no existe
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Cargar contexto JSON
        self.context = self._load_context()

        # Preparar entorno Jinja2
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"])
        )

    def _load_context(self) -> dict[str, Any]:
        if not self.context_path.exists():
            raise FileNotFoundError(
                f"No se encontró context.json en: {self.context_path}"
            )

        with self.context_path.open("r", encoding="utf-8") as f:
            context = json.load(f)

        # Normalización opcional de algunos campos
        context = self._normalize_context(context)
        return context

    def setResumen(
        self,
        subject_id: str | int | None = None,
        round_type: str | None = None,
        session_id: str | int | None = None,
        round_id: str | int | None = None,
        trial_count: int | None = None,
        run_duration: float | int | None = None,
        round_duration_text: str | None = None,
        general_comments: str | None = None,
        pad_numbers: bool = True
    ) -> None:
        """
        Completa los datos del apartado 'Resumen general' dentro de self.context.

        Parámetros
        ----------
        subject_id : str | int | None
            Identificador del sujeto. Ej: '01' o 1.
        round_type : str | None
            Tipo de ronda. Ej: 'Ejecutada', 'Imaginada'.
        session_id : str | int | None
            Número o identificador de sesión. Ej: '01' o 1.
        round_id : str | int | None
            Número o identificador de ronda. Ej: '01' o 1.
        trial_count : int | None
            Cantidad total de trials.
        run_duration : float | int | None
            Duración total de la ronda en segundos. Si se proporciona, se formatea
            automáticamente como 'XXX segundos (~Y.Y min)'.
        round_duration_text : str | None
            Texto ya formateado para la duración. Tiene prioridad solo si no se pasa
            run_duration.
        general_comments : str | None
            Comentarios generales del resumen.
        pad_numbers : bool
            Si es True, session_id, round_id y subject_id enteros se formatean con dos dígitos.

        Retorna
        -------
        None
        """

        def _format_id(value: str | int | None) -> str | None:
            if value is None:
                return None

            if isinstance(value, int):
                return f"{value:02d}" if pad_numbers else str(value)

            value_str = str(value).strip()

            if value_str.isdigit() and pad_numbers:
                return f"{int(value_str):02d}"

            return value_str

        if subject_id is not None:
            self.context["subject_id"] = _format_id(subject_id)

        if round_type is not None:
            self.context["round_type"] = str(round_type).strip()

        if session_id is not None:
            self.context["session_id"] = _format_id(session_id)

        if round_id is not None:
            self.context["round_id"] = _format_id(round_id)

        if trial_count is not None:
            if trial_count < 0:
                raise ValueError("trial_count no puede ser negativo.")
            self.context["trial_count"] = int(trial_count)

        if run_duration is not None:
            if run_duration < 0:
                raise ValueError("run_duration no puede ser negativo.")

            seconds = float(run_duration)
            minutes = seconds / 60.0
            self.context["round_duration"] = f"{int(round(seconds))} segundos (~{minutes:.1f} min)"

        elif round_duration_text is not None:
            self.context["round_duration"] = str(round_duration_text).strip()

        if general_comments is not None:
            self.context["general_comments"] = str(general_comments).strip()


    def _format_dataframe(self, df, float_format: str = "{:.2f}"):
                df_to_render = df.copy()

                for col in df_to_render.columns:
                    if df_to_render[col].dtype.kind in "fc":
                        df_to_render[col] = df_to_render[col].map(
                            lambda x: float_format.format(x) if x == x else ""
                        )

                return df_to_render.to_html(
                    index=True,
                    classes="dataframe",
                    border=0,
                    escape=False
                )

    def set_lslresumen(
        self,
        trials_description_df,
        traces_duration_df,
        pendown_delays_df,
        float_format: str = "{:.2f}"
    ) -> None:
        """
        Inserta en self.context las tablas HTML del apartado 'Resumen LSL'.

        Parámetros
        ----------
        trials_description_df : pandas.DataFrame
            DataFrame con la descripción de trials.
        traces_duration_df : pandas.DataFrame
            DataFrame con el resumen de duración de trazos.
        pendown_delays_df : pandas.DataFrame
            DataFrame con el resumen de delays entre inicio de cue y primer pendown.
        float_format : str
            Formato para números flotantes. Por defecto: '{:.2f}'.

        Retorna
        -------
        None
        """

        self.context["lsl_summary_tables"] = [
            {
                "title": "Descripción de trials",
                "html": self._format_dataframe(trials_description_df, float_format)
            },
            {
                "title": "Resumen duración de trazos",
                "html": self._format_dataframe(traces_duration_df, float_format)
            },
            {
                "title": "Resumen delays entre inicio de cue y el primer pendown",
                "html": self._format_dataframe(pendown_delays_df, float_format)
            }
        ]

        # Si existía la estructura anterior, la quitamos para que no se renderice
        self.context.pop("lsl_tables", None)

    def set_figures(self, figures_context: dict[str, Any]) -> None:
        """
        Inserta en self.context las figuras generadas por
        ReportFigureGenerator.generate_all() (trace_plot_path,
        trace_plot_caption, trace_extra_plots, other_graphs).

        Reemplaza esas claves por completo en vez de solo actualizarlas: si
        no se generó una figura en particular (p. ej. ronda Imaginada, sin
        datos de trazos), la clave correspondiente se elimina del contexto
        para no dejar un placeholder de context.json apuntando a una imagen
        que no existe.

        Parámetros
        ----------
        figures_context : dict[str, Any]
            Resultado de ReportFigureGenerator.generate_all().

        Retorna
        -------
        None
        """
        figure_keys = ("trace_plot_path", "trace_plot_caption", "trace_extra_plots", "other_graphs")
        for key in figure_keys:
            self.context.pop(key, None)

        self.context.update(figures_context)

    def set_quality(self, quality_context: dict[str, Any]) -> None:
        """
        Inserta en self.context la sección 'Calidad de trials' generada por
        ReportTrialsQuality.to_context() (quality_summary,
        quality_rejected_table, quality_channel_offenders_table).

        Igual que set_figures, reemplaza esas claves por completo: si no se
        evaluó calidad para esta ronda, se eliminan del contexto para que el
        template caiga en su mensaje de "no evaluado" en vez de mostrar datos
        obsoletos de una corrida anterior.

        Parámetros
        ----------
        quality_context : dict[str, Any]
            Resultado de ReportTrialsQuality.to_context().

        Retorna
        -------
        None
        """
        quality_keys = ("quality_summary", "quality_rejected_table", "quality_channel_offenders_table")
        for key in quality_keys:
            self.context.pop(key, None)

        self.context.update(quality_context)

    def set_channels_quality(self, channels_quality_context: dict[str, Any]) -> None:
        """
        Inserta en self.context la sección 'Calidad de canales' generada por
        ReportChannelsQuality.to_context() (channels_quality_summary,
        channels_quality_table, channels_quality_intro).

        Igual que set_quality/set_figures, reemplaza esas claves por completo:
        si no se evaluó calidad de canales, se eliminan del contexto en vez de
        dejar datos obsoletos de una corrida anterior.

        Parámetros
        ----------
        channels_quality_context : dict[str, Any]
            Resultado de ReportChannelsQuality.to_context().

        Retorna
        -------
        None
        """
        channels_quality_keys = ("channels_quality_summary", "channels_quality_table", "channels_quality_intro")
        for key in channels_quality_keys:
            self.context.pop(key, None)

        self.context.update(channels_quality_context)

    def _normalize_context(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Corrige tipos o rutas problemáticas del JSON.
        """
        # include_toc debería ser booleano
        include_toc = context.get("include_toc", False)
        if isinstance(include_toc, str):
            context["include_toc"] = include_toc.strip().lower() == "true"

        return context

    def render_html(self) -> str:
        if not self.template_path.exists():
            raise FileNotFoundError(
                f"No se encontró el template HTML en: {self.template_path}"
            )

        template = self.jinja_env.get_template("report_template.html")
        rendered_html = template.render(**self.context)
        return rendered_html

    def _build_output_filename(self) -> str:
        """
        Arma el nombre del HTML de salida a partir de subject_id/session_id/
        round_id ya cargados en self.context (vía setResumen). Si falta
        alguno, usa 'report.html' como nombre genérico.
        """
        subject_id = self.context.get("subject_id")
        session_id = self.context.get("session_id")
        round_id = self.context.get("round_id")

        if subject_id and session_id and round_id:
            return f"report_sub-{subject_id}_ses-{session_id}_run-{round_id}.html"

        return "report.html"

    def save_html(self, html: str | None = None) -> Path:
        if html is None:
            html = self.render_html()

        self.output_html_path = self.output_dir / self._build_output_filename()

        with self.output_html_path.open("w", encoding="utf-8") as f:
            f.write(html)

        return self.output_html_path


if __name__ == "__main__":
    from pyhwr.managers import GHiampDataManager, LSLDataManager
    from pyhwr.report.ReportFigures import ReportFigureGenerator
    from pyhwr.report.ReportTrialsQuality import ReportTrialsQuality
    from pyhwr.report.ReportChannelsQuality import ReportChannelsQuality
    import os

    subject_id = 5
    session_id = 1
    round_id = 6
    round_type = "ejecutada"

    generator = ReportGenerator()

    path = f"D:\\dataset\\DataBase\\sub-{subject_id:02d}\\ses-{session_id:02d}"
    file_stem = f"sub-{subject_id:02d}_ses-{session_id:02d}_task-{round_type.lower()}_run-{round_id:02d}_eeg"
    lsl_manager = LSLDataManager(os.path.join(path, f"{file_stem}.xdf"))
    gmanager = GHiampDataManager(os.path.join(path, f"{file_stem}.hdf5"), normalize_time=True)

    trials_description = lsl_manager.describe_trials()
    resumen_pendown = lsl_manager.penDown_delays_resume()
    resumen_traces = lsl_manager.tracesDuration_resume()

    # Duración de la ronda: se toma el tiempo registrado por la tablet.
    run_duration = trials_description.loc["duration", lsl_manager.tab_name]

    generator.setResumen(
        subject_id=subject_id,
        round_type=round_type,
        session_id=session_id,
        round_id=round_id,
        trial_count=None,
        run_duration=run_duration,
        general_comments=""
    )

    generator.set_lslresumen(
        trials_description,
        resumen_traces,
        resumen_pendown
        )

    file_prefix = f"sub-{subject_id:02d}_ses-{session_id:02d}_run-{round_id:02d}"
    figure_generator = ReportFigureGenerator(lsl_manager, generator.base_dir / "figures", file_prefix)
    generator.set_figures(figure_generator.generate_all())

    quality = ReportTrialsQuality(gmanager, lsl_manager)
    generator.set_quality(quality.to_context())

    channels_quality = ReportChannelsQuality(
        quality.get_eeg_raw(),
        methods=["amplitude", "flat", "low_variability"],
    )
    generator.set_channels_quality(channels_quality.to_context())

    html = generator.render_html()
    generator.save_html(html)