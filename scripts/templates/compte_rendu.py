"""Build the « Compte rendu de réunion » template: infographic card on top, detailed minutes ({{output}}) below.

Run: python scripts/templates/compte_rendu.py  ->  templates/default/linto-compte-rendu.docx
The card is ONE top-level table (9-column grid, merged cells) because the gateway only substitutes
placeholders in top-level tables. Every extracted placeholder maps to a section of the prompt output.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from docx_kit import *  # noqa: E402,F403

AMBER = "B45309"
AMBER_LIGHT = "FEF3C7"
LEFT = RIGHT = 1.8
PAD, TILE, GAP = 0.35, 3.95, 0.3          # 2*0.35 + 4*3.95 + 3*0.3 = 17.4
GRID = [PAD, TILE, GAP, TILE, GAP, TILE, GAP, TILE, PAD]

P = {
    "titre": "{{titre: intitulé de la réunion en 4 à 9 mots, sans date ni le mot réunion, déduit de la section En bref}}",
    "accroche": "{{accroche: une seule phrase de 30 mots maximum qui dit l'objet de la réunion et son principal résultat, tirée de la section En bref}}",
    "nb_participants": "{{nb_participants: nombre de puces de la section Participants, en chiffres}}",
    "nb_decisions": "{{nb_decisions: nombre de puces de la section Décisions actées, en chiffres, 0 si la section indique Aucune décision actée}}",
    "nb_actions": "{{nb_actions: nombre de puces de la section Actions à mener, en chiffres, 0 si la section est vide}}",
    "echeance": "{{prochaine_echeance: l'échéance la plus proche parmi les Actions à mener, recopiée telle quelle puis le porteur entre parenthèses, 8 mots maximum, Aucune échéance fixée si aucune action n'a d'échéance}}",
    "decisions": "{{decisions_cles: les 4 décisions les plus importantes de la section Décisions actées, une par ligne commençant par • suivi d'un espace, 18 mots maximum chacune, qui a tranché en gras s'il est connu, Aucune décision actée si la section est vide}}",
    "participants": "{{participants: les noms de la section Participants, un par ligne commençant par • suivi d'un espace, sans fonction}}",
    "points": "{{points_ouverts: les 3 points les plus importants de la section Points ouverts, un par ligne commençant par • suivi d'un espace, 15 mots maximum chacun, Aucun si la section est vide}}",
    "prochaine": "{{prochaine_reunion: contenu de la section Prochaine réunion en une phrase de 20 mots maximum, Non fixée si rien n'est prévu}}",
    # mindmap renderer: image drawn from an extracted outline
    "mindmap": "{{mindmap_sujets: thème central = objet de la réunion en 2 à 5 mots ; une branche par sujet de la section Sujets abordés, dans l'ordre ; détails = faits, chiffres et décisions de la section Discussion pour ce sujet}}",
    # repeating rows (one row per list item)
    "chiffres": "{{chiffres: les 5 chiffres ou dates les plus utiles de la section Chiffres et dates clés, dans l'ordre d'importance}}",
    "chiffres_valeur": "{{chiffres.valeur: la valeur seule avec son unité, 14 caractères maximum, par exemple 10 000 €, 95 %, 30/09}}",
    "chiffres_objet": "{{chiffres.objet: ce à quoi la valeur se rapporte, 14 mots maximum}}",
    "actions": "{{actions: les actions de la section Actions à mener, 8 au maximum, les plus importantes d'abord}}",
    "actions_porteur": "{{actions.porteur: nom du porteur tel qu'écrit dans le compte rendu}}",
    "actions_action": "{{actions.action: l'action à réaliser, 16 mots maximum}}",
    "actions_echeance": "{{actions.echeance: l'échéance telle qu'écrite, ou non fixée}}",
}


def header_footer(section):
    h = section.header
    h.is_linked_to_previous = False
    p = h.paragraphs[0]
    tab_stops(p, [(17.4, "right")])
    picture(p, ASSETS / "linto-studio-logo.png", 0.55)
    run(p, "\t{{organization_name}}", size=7.5, color=GREY, font="Inter Light")
    paragraph_border(p._p.get_or_add_pPr(), bottom=(LINE, 4, 6))

    f = section.footer
    f.is_linked_to_previous = False
    p = f.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    tab_stops(p, [(17.4, "right")])
    paragraph_border(p._p.get_or_add_pPr(), top=(LINTO_GREEN, 6, 6))
    run(p, "Compte rendu généré avec LinTO par intelligence artificielle, à relire avant diffusion", size=7, color=GREY_LIGHT, font="Inter Light")
    run(p, "\t", size=7)
    run(p, "Page ", size=7.5, color=GREY)
    field(p, "PAGE", size=7.5, color=INK, bold=True)
    run(p, " / ", size=7.5, color=GREY)
    field(p, "NUMPAGES", size=7.5, color=GREY)
    para(f, after=0)  # breathing space above the bottom edge


def card(doc):
    """One top-level table on a 9-column grid; rows are built top to bottom."""
    layout = ["pad", "pill", "gap", "tiles", "gap", "title_chiffres", "chiffres", "gap",
              "panels", "gap", "title_actions", "head_actions", "actions", "gap", "footer", "pad"]
    t = table(doc, len(layout), GRID)
    rows = {name: t.rows[i] for i, name in enumerate(layout) if name not in ("pad", "gap")}
    for i, name in enumerate(layout):
        row = t.rows[i]
        row_cant_split(row)
        for c in row.cells:
            cell_shade(c, PAPER)
            cell_margins(c, top=0, bottom=0, left=0, right=0)
        if name in ("pad", "gap"):
            row_height(row, 0.35 if name == "pad" else 0.3, exact=True)

    def span(row, a, b):
        return row.cells[a].merge(row.cells[b]) if a != b else row.cells[a]

    def section_title(row, text, color):
        c = span(row, 1, 7)
        cell_margins(c, top=0.05, bottom=0.08)
        p = first_para(c)
        run(p, "●  ", size=7, color=color)
        run(p, text, size=7.5, color=color, bold=True, spacing=0.5)

    # pill + accroche
    c = span(rows["pill"], 1, 7)
    p = first_para(c, after=5)
    pill = run(p, "   COMPTE RENDU DE RÉUNION   ", size=6.5, color=WHITE, bold=True, spacing=0.6)
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), LINTO_GREEN)
    put(pill._element.get_or_add_rPr(), shd, RPR_ORDER)
    p = c.add_paragraph(); p.paragraph_format.space_after = Pt(0); p.paragraph_format.line_spacing = 1.25
    run(p, P["accroche"], size=11.5, color=INK)

    # KPI tiles
    row = rows["tiles"]
    row_height(row, 1.75)
    for col, value, label, size in ((1, P["nb_participants"], "PARTICIPANTS", 20), (3, P["nb_decisions"], "DÉCISIONS ACTÉES", 20),
                                    (5, P["nb_actions"], "ACTIONS À MENER", 20), (7, P["echeance"], "PROCHAINE ÉCHÉANCE", 9.5)):
        c = row.cells[col]
        cell_shade(c, WHITE)
        cell_borders(c, top=(LINE, 4), left=(LINE, 4), bottom=(LINTO_GREEN, 18), right=(LINE, 4))
        cell_margins(c, top=0.18, bottom=0.12, left=0.3, right=0.25)
        cell_valign(c, "top")
        run(first_para(c, after=2), label, size=6.5, color=GREY, bold=True, spacing=0.5)
        p = c.add_paragraph(); p.paragraph_format.space_after = Pt(0); p.paragraph_format.line_spacing = 1.0
        run(p, value, size=size, color=LINTO_GREEN_DARK if size > 12 else INK, bold=True)

    # key figures: repeating rows (value | what it refers to)
    section_title(rows["title_chiffres"], "CHIFFRES CLÉS", LINTO_GREEN_DARK)
    row = rows["chiffres"]
    v = row.cells[1]
    o = span(row, 2, 7)
    for c in (v, o):
        cell_shade(c, WHITE)
        cell_valign(c, "center")
        cell_borders(c, top="nil", left="nil", right="nil", bottom=(LINE, 4))
    cell_borders(v, left=(LINTO_GREEN, 24))
    cell_margins(v, top=0.1, bottom=0.1, left=0.3, right=0.1)
    cell_margins(o, top=0.1, bottom=0.1, left=0.2, right=0.3)
    run(first_para(v), P["chiffres_valeur"], size=13, color=LINTO_GREEN_DARK, bold=True)
    p = first_para(o, line=1.15)
    run(p, P["chiffres"], size=9, color=INK)
    run(p, P["chiffres_objet"], size=9, color=INK)

    # decisions | open points
    def panel(cell, title, value, accent):
        cell_shade(cell, WHITE)
        cell_borders(cell, top=(LINE, 4), left=(accent, 24), bottom=(LINE, 4), right=(LINE, 4))
        cell_margins(cell, top=0.2, bottom=0.2, left=0.35, right=0.3)
        cell_valign(cell, "top")
        p = first_para(cell, after=4)
        run(p, "●  ", size=7, color=accent)
        run(p, title, size=7.5, color=accent, bold=True, spacing=0.5)
        p = cell.add_paragraph(); p.paragraph_format.space_after = Pt(1); p.paragraph_format.line_spacing = 1.25
        run(p, value, size=9, color=INK)
    row = rows["panels"]
    panel(span(row, 1, 3), "DÉCISIONS ACTÉES", P["decisions"], LINTO_GREEN)
    panel(span(row, 5, 7), "POINTS OUVERTS", P["points"], AMBER)

    # actions table: title, header, repeating row
    section_title(rows["title_actions"], "ACTIONS À MENER", INK)
    head = rows["head_actions"]
    cells = [head.cells[1], span(head, 2, 5), span(head, 6, 7)]
    for c, label in zip(cells, ("PORTEUR", "ACTION", "ÉCHÉANCE")):
        cell_shade(c, INK)
        cell_margins(c, top=0.08, bottom=0.08, left=0.3, right=0.2)
        run(first_para(c), label, size=6.5, color=WHITE, bold=True, spacing=0.5)
    row = rows["actions"]
    cells = [row.cells[1], span(row, 2, 5), span(row, 6, 7)]
    for c, value, bold, color in zip(cells, (P["actions_porteur"], P["actions"] + P["actions_action"], P["actions_echeance"]),
                                     (True, False, False), (INK, INK, LINTO_GREEN_DARK)):
        cell_shade(c, WHITE)
        cell_borders(c, top="nil", left="nil", right="nil", bottom=(LINE, 4))
        cell_margins(c, top=0.09, bottom=0.09, left=0.3, right=0.2)
        cell_valign(c, "top")
        run(first_para(c, line=1.15), value, size=9, color=color, bold=bold)

    # participants | next meeting
    def small_panel(cell, title, value, accent):
        cell_shade(cell, WHITE)
        cell_borders(cell, top=(LINE, 4), left=(accent, 24), bottom=(LINE, 4), right=(LINE, 4))
        cell_margins(cell, top=0.18, bottom=0.18, left=0.35, right=0.3)
        cell_valign(cell, "top")
        run(first_para(cell, after=3), title, size=7.5, color=accent, bold=True, spacing=0.5)
        p = cell.add_paragraph(); p.paragraph_format.space_after = Pt(0); p.paragraph_format.line_spacing = 1.2
        run(p, value, size=9, color=INK)
    row = rows["footer"]
    small_panel(span(row, 1, 3), "PARTICIPANTS", P["participants"], GREY)
    small_panel(span(row, 5, 7), "PROCHAINE RÉUNION", P["prochaine"], LINTO_GREEN_DARK)
    table_borders(t, none=True)


def build(out):
    doc = new_document(margins_cm=(LEFT, RIGHT, 2.2, 2.2), size=10)
    doc.sections[0].header_distance = Cm(0.9)
    doc.sections[0].footer_distance = Cm(0.8)
    style_headings(doc,
                   h1=(15, INK, 14, 6, None),
                   h2=(12.5, INK, 12, 5, LINTO_GREEN),
                   h3=(10.5, LINTO_GREEN_DARK, 9, 3, None))
    header_footer(doc.sections[0])

    para(doc, P["titre"], after=3, size=20, color=INK, bold=True, line=1.05)
    p = para(doc, after=10)
    run(p, "{{conversation_name}}", size=8.5, color=GREY)
    run(p, "   ·   ", size=8.5, color=GREY_LIGHT)
    run(p, "{{organization_name}}", size=8.5, color=GREY)
    run(p, "   ·   ", size=8.5, color=GREY_LIGHT)
    run(p, "Généré le {{job_date}}", size=8.5, color=GREY)
    card(doc)

    p = para(doc, before=16, after=4, keep_next=True)
    run(p, "CARTE DES SUJETS", size=8, color=LINTO_GREEN_DARK, bold=True, spacing=0.8)
    para(doc, P["mindmap"], align="center", after=0)

    p = para(doc, before=16, after=0, keep_next=True)
    run(p, "COMPTE RENDU DÉTAILLÉ", size=8, color=LINTO_GREEN_DARK, bold=True, spacing=0.8)
    para(doc, "{{output}}")
    set_core_properties(doc, "Compte rendu de réunion · LinTO", "compte-rendu")
    doc.save(out)
    embed_fonts(out, inter_families())
    print("written", out)


if __name__ == "__main__":
    build(HERE.parent.parent / "templates" / "default" / "linto-compte-rendu.docx")
