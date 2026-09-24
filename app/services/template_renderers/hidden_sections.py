"""Hidden sections: sections of the service output read by the extraction but not printed.

Property hide_sections = "Réunion,Attendance". A section is a Markdown heading with that text (any
level, case-insensitive) and everything up to the next heading of the same or a higher level.
Also inserts the blank line a model often forgets after a Markdown table: Python-Markdown would
otherwise append the following lines to the table's last row (always on, harmless).
"""
import re
from typing import Dict

from .base import OUTPUT, Renderer, RendererSpec, csv_values, register

SPEC = RendererSpec(
    trigger="Propriété personnalisée du template hide_sections, par exemple « Réunion ».",
    service_prompt=(
        "Le prompt du service fait écrire une section « ## Réunion » (même nom que dans hide_sections) qui porte les "
        "données du cartouche : une ligne « - Libellé : valeur » par donnée."
    ),
    placeholder_prompt="Les consignes pointent vers cette section : « valeur de la ligne Projet de la section Réunion ».",
    example="hide_sections = Réunion ; {{projet: valeur de la ligne Projet de la section Réunion}}",
)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def prepare(markdown: str, props: Dict[str, str]) -> str:
    lines = markdown.split("\n")
    hidden = {h.lower() for h in csv_values(props, "hide_sections")}
    if hidden:
        kept, skip_level = [], None
        for line in lines:
            m = HEADING_RE.match(line)
            if m:
                level = len(m.group(1))
                if skip_level is not None and level <= skip_level:
                    skip_level = None
                if skip_level is None and m.group(2).strip().lower() in hidden:
                    skip_level = level
                    continue
            if skip_level is None:
                kept.append(line)
        lines = kept
    fixed = []
    for i, line in enumerate(lines):
        fixed.append(line)
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if line.lstrip().startswith("|") and nxt.strip() and not nxt.lstrip().startswith("|"):
            fixed.append("")
    return "\n".join(fixed).strip()


@register
class HiddenSections(Renderer):
    """Hidden sections: sections of the service output read by the extraction but not printed."""
    name = "hidden_sections"
    family = OUTPUT
    order = 10
    spec = SPEC

    def prepare_output(self, doc, markdown, ctx):
        return prepare(markdown, ctx.props)
