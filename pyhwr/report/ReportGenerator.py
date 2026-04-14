from __future__ import annotations

import json
from multiprocessing import context
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

class ReportGenerator:
    def __init__(self) -> None:
        # Carpeta donde está ESTE archivo
        self.base_dir = Path(__file__).resolve().parent

        # Rutas absolutas derivadas de base_dir
        self.context_path = self.base_dir / "context.json"
        self.templates_dir = self.base_dir / "templates"
        self.template_path = self.templates_dir / "report_template.html"
        self.output_dir = self.base_dir / "output"
        self.output_html_path = self.output_dir / "report.html"

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

    def save_html(self, html: str | None = None) -> Path:
        if html is None:
            html = self.render_html()

        with self.output_html_path.open("w", encoding="utf-8") as f:
            f.write(html)

        return self.output_html_path


if __name__ == "__main__":
    from pyhwr.managers import LSLDataManager
    import os
    generator = ReportGenerator()

    generator.setResumen(
        subject_id=1,
        round_type="Ejecutada",
        session_id=1,
        round_id=1,
        trial_count=40,
        run_duration=400,
        general_comments=""
    )

    path = "test\\data\\pruebas_piloto\\emgeog\\"
    lsl_filename = "sub-emgeogtrazos_ses-01_task-ejecutada_run-01_emgeog.xdf"
    lsl_manager = LSLDataManager(os.path.join(path, lsl_filename))

    trials_description = lsl_manager.describe_trials()
    resumen_pendown = lsl_manager.penDown_delays_resume()
    resumen_traces = lsl_manager.tracesDuration_resume()

    generator.set_lslresumen(
        trials_description,
        resumen_traces,
        resumen_pendown
        )

    html = generator.render_html()
    generator.save_html(html)