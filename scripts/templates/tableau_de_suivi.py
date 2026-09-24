"""Build the « Tableau de suivi » template (action log): project box, attendees and recipients per
organisation, numbered topics typed Action / Decision / Observation with owner and due date.

Generic: the internal organisation is {{organization_name}}; no brand in the document.
Run: python scripts/templates/tableau_de_suivi.py -> templates/default/linto-tableau-de-suivi.docx
Placeholders: job_date, organization_name (standard), fields extracted from the « ## Réunion »
section of the output, and output (topic table, formatted by the output_tables renderer).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from docx_kit import *  # noqa: E402,F403

LEFT, RIGHT = 1.8, 1.8
BODY_W = 21.0 - LEFT - RIGHT          # 17.4 cm
GRID = "7F7F7F"
SYM_A, SYM_D, SYM_O = "C51C42", "1F8A5B", "2B5797"   # Action, Decision, Observation
LABEL = GREY_LIGHT

P = {
    "projet": "{{projet: valeur de la ligne Projet de la section Réunion, recopiée telle quelle}}",
    "ordre": "{{ordre_du_jour: valeur de la ligne Ordre du jour de la section Réunion, par défaut Réunion de suivi}}",
    "anime": "{{anime_par: valeur de la ligne Animé par de la section Réunion}}",
    "org_ext": "{{organisation_externe: valeur de la ligne Organisation externe de la section Réunion, par défaut -}}",
    "part_ext": "{{participants_externes: noms de la ligne Participants externes de la section Réunion, un par ligne, chaque ligne commençant par ✓ suivi d'un espace, par défaut -}}",
    "part_lin": "{{participants_internes: noms de la ligne Participants internes de la section Réunion, un par ligne, chaque ligne commençant par ✓ suivi d'un espace, par défaut -}}",
    "dest_ext": "{{destinataires_externes: noms de la ligne Destinataires externes de la section Réunion, un par ligne, par défaut -}}",
    "dest_lin": "{{destinataires_internes: noms de la ligne Destinataires internes de la section Réunion, un par ligne, par défaut -}}",
}


def header(section):
    h = section.header
    h.is_linked_to_previous = False
    for i, (label, value, rlabel, rvalue) in enumerate((
        ("Projet :", "{{projet}}", "Date :", "{{job_date}}"),
        ("Fichier :", "CompteRendu_{{job_date}}_v1_0.docx", "Édité le :", "{{job_date}}"),
    )):
        p = h.paragraphs[0] if i == 0 else h.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        tab_stops(p, [(1.6, "left"), (13.3, "left"), (15.6, "left")])
        run(p, label, size=7.5, color=LABEL, font="Inter Light")
        run(p, "\t", size=7.5)
        run(p, value, size=7.5, color=INK)
        run(p, "\t", size=7.5)
        run(p, rlabel, size=7.5, color=LABEL, font="Inter Light")
        run(p, "\t", size=7.5)
        run(p, rvalue, size=7.5, color=INK)


def footer(section):
    f = section.footer
    f.is_linked_to_previous = False
    t = table(f, 1, [5.6, 9.4, 6.0], indent_cm=-LEFT)
    r = t.rows[0]
    row_height(r, 1.4, exact=True)
    for c in r.cells:
        cell_shade(c, LINTO_GREEN_DARK)
        cell_valign(c, "center")
    cell_margins(r.cells[0], left=LEFT)
    cell_margins(r.cells[2], right=RIGHT)
    p = first_para(r.cells[0])
    p.paragraph_format.left_indent = Cm(LEFT)
    run(p, "Tableau de suivi", size=8, color=WHITE, bold=True)
    run(first_para(r.cells[1], align="center"), "Document généré avec LinTO, à relire avant diffusion.", size=6.5, color=WHITE)
    p = first_para(r.cells[2], align="right")
    p.paragraph_format.right_indent = Cm(RIGHT)
    run(p, "Page ", size=8, color=WHITE, bold=True)
    field(p, "PAGE", size=8, color=WHITE, bold=True)
    run(p, "/", size=8, color=WHITE, bold=True)
    field(p, "NUMPAGES", size=8, color=WHITE, bold=True)
    # the footer paragraph python-docx created before the table would add a blank line under the band
    first = f.paragraphs[0]
    first.paragraph_format.space_after = Pt(0)
    first.paragraph_format.line_spacing = Pt(1)
    f._element.remove(first._p)
    f._element.append(first._p)


def cartouche(doc):
    w = [3.2, 5.9, 3.3, 5.0]
    t = table(doc, 7, w)
    table_borders(t, color=GRID, size=4)
    table_cell_margins(t, top=0.07, bottom=0.07, left=0.12, right=0.12)
    for i, (label, value, bold) in enumerate((("Projet :", P["projet"], True), ("Ordre du jour :", P["ordre"], True),
                                              ("Animé par :", P["anime"], False))):
        row = t.rows[i]
        run(first_para(row.cells[0]), label, size=10, color=INK)
        merged = row.cells[1].merge(row.cells[3])
        run(first_para(merged), value, size=10, color=INK, bold=bold)
    a = t.cell(3, 0).merge(t.cell(3, 1))
    run(first_para(a, align="center"), "Participants", size=10, color=INK)
    rcp = t.cell(3, 2).merge(t.cell(3, 3))
    run(first_para(rcp, align="center"), "Destinataires", size=10, color=INK)
    for j, label in enumerate(("Société", "Nom", "Société", "Nom")):
        c = t.cell(4, j)
        cell_shade(c, PAPER)
        run(first_para(c, align="center"), label, size=10, color=INK)
    for i, (company, att, rec) in enumerate(((P["org_ext"], P["part_ext"], P["dest_ext"]),
                                            ("{{organization_name}}", P["part_lin"], P["dest_lin"]))):
        row = t.rows[5 + i]
        # the external company placeholder carries its description once, the second cell reuses the bare name
        for j, text in ((0, company), (2, company if i else "{{organisation_externe}}")):
            cell_valign(row.cells[j], "center")
            run(first_para(row.cells[j], align="center"), text, size=10, color=INK)
        for j, text in ((1, att), (3, rec)):
            cell_valign(row.cells[j], "center")
            run(first_para(row.cells[j], line=1.25), text, size=10, color=INK)
    for row in t.rows:
        row_cant_split(row)


def legend(doc):
    p = para(doc, before=6)
    tab_stops(p, [(BODY_W / 2, "center"), (BODY_W, "right")])
    for i, (sym, color, label) in enumerate((("►", SYM_A, " A (Action)"), ("◆", SYM_D, " D (Décision)"),
                                              ("▲", SYM_O, " O (Observation)"))):
        run(p, ("\t" if i else "") + sym, size=7.5, color=color)
        run(p, label, size=7, color=GREY_LIGHT, font="Inter Light")


def build(out):
    doc = new_document(margins_cm=(LEFT, RIGHT, 2.3, 2.5), size=9.5)
    doc.sections[0].header_distance = Cm(1.0)
    header(doc.sections[0])
    footer(doc.sections[0])
    para(doc, "Tableau de suivi", align="center", before=6, after=10, size=15, color=LINTO_GREEN_DARK, bold=True)
    cartouche(doc)
    spacer(doc, 8)
    para(doc, "{{output}}")
    legend(doc)
    default_table_style(doc, border=GRID, cell_mar_cm=(0.07, 0.12))
    # "## Sujets" / "## Réunion" headings of the output are structure for the model and the extraction, not for the reader
    h2 = doc.styles["Heading 2"].element.get_or_add_rPr()
    put(h2, OxmlElement("w:vanish"), RPR_ORDER)
    topics_style = named_table_style(doc, "CR Sujets", border=GRID, size=4, header_bold=False,
                                     header_bottom=(INK, 8), cell_mar_cm=(0.1, 0.12), repeat_header=False)
    set_core_properties(doc, "Tableau de suivi · LinTO", "tableau-de-suivi")
    doc.save(out)
    embed_fonts(out, inter_families())
    # template-driven {{output}} handling, branch feat/docx-output-tables of llm-gateway; ignored by 2.6.0
    set_custom_properties(out, {
        "hide_sections": "Réunion",
        "style_table": topics_style,
        "table_widths": "5,55,7,20,13",
        "table_align": "center,left,center,center,center",
        "table_symbol_colors": f"►:{SYM_A},◆:{SYM_D},▲:{SYM_O}",
    })
    print("written", out)


if __name__ == "__main__":
    build(HERE.parent.parent / "templates" / "default" / "linto-tableau-de-suivi.docx")
