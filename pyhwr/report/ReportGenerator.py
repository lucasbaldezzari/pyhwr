from __future__ import annotations

import json
from multiprocessing import context
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

class ReportGenerator:
    def __init__(self) -> None:
        # Carpeta donde está ESTE archivo, independientemente de dónde ejecutes Python
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
    generator = ReportGenerator()
    html = generator.render_html()
    output_path = generator.save_html(html)
    print(f"HTML generado en: {output_path}")