"""Build the « Points clés » template: a one-page infographic, no {{output}} (the card is the document).
Run: python scripts/templates/points_cles.py -> templates/default/linto-points-cles.docx"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from docx_kit import *  # noqa: E402,F403

AMBER_ACCENT, AMBER_DARK = "D97706", "92400E"

P = {
    "titre": "{{titre: sujet de la réunion en 4 à 9 mots, sans date ni le mot réunion, déduit de la section L'essentiel}}",
    "essentiel": "{{essentiel: la phrase de la section L'essentiel, recopiée}}",
    "points": "{{points: les puces de la section Points clés, dans l'ordre, 8 au maximum}}",
    "pt_n": "{{points.numero: numéro sur deux chiffres, 01 pour le premier}}",
    "pt_t": "{{points.texte: la puce recopiée avec son passage en gras **…**, 25 mots maximum}}",
    "change": "{{ce_qui_change: la section Ce qui change, une ligne par puce commençant par • suivi d'un espace, 18 mots maximum chacune}}",
    "suite": "{{a_retenir: la section À retenir pour la suite, une ligne par puce commençant par • suivi d'un espace, porteur en gras, 18 mots maximum chacune}}",
    "chiffres": "{{chiffres: les puces de la section Chiffres clés, 4 au maximum, les plus parlantes d'abord}}",
    "ch_v": "{{chiffres.valeur: la valeur seule avec son unité, 14 caractères maximum}}",
    "ch_o": "{{chiffres.objet: ce à quoi elle se rapporte, 12 mots maximum}}",
    "mindmap": "{{mindmap_themes: thème central = sujet de la réunion en 2 à 5 mots ; reprendre la section Thèmes : une branche par thème, ses sous-puces comme détails}}",
    "participants": "{{participants_ligne: les noms de la section Participants séparés par des virgules}}",
}


def build(out):
    doc = service_document(P["titre"], ["{{conversation_name}}", "{{organization_name}}", "{{job_date}}"])
    card = Card(doc, ["pad", "header", "gap", "t_pts", "pts", "gap", "panels", "gap", "t_ch", "ch", "gap", "people", "pad"])
    card.header("header", "POINTS CLÉS", P["essentiel"], color=AMBER_ACCENT, size=12.5)
    card.title("t_pts", "À SAVOIR", AMBER_DARK)
    cells = card.repeated("pts", [(1, 1), (2, 7)], [(P["points"] + P["pt_n"], 20, AMBER_ACCENT, True),
                                                    (P["pt_t"], 10, INK, False)])
    cell_valign(cells[0], "center")
    cell_valign(cells[1], "center")
    card.panel("panels", 1, 3, "CE QUI CHANGE", P["change"], LINTO_GREEN)
    card.panel("panels", 5, 7, "À RETENIR POUR LA SUITE", P["suite"], AMBER_DARK)
    card.title("t_ch", "CHIFFRES CLÉS", AMBER_DARK)
    v, o = card.repeated("ch", [(1, 2), (3, 7)], [(P["chiffres"] + P["ch_v"], 14, AMBER_DARK, True),
                                                  (P["ch_o"], 9.5, INK, False)])
    cell_valign(v, "center")
    cell_valign(o, "center")
    c = card.span("people", 1, 7)
    p = first_para(c)
    run(p, "PARTICIPANTS   ", size=7, color=GREY, bold=True, spacing=0.5)
    run(p, P["participants"], size=8.5, color=GREY)
    card.finish()
    section_label(doc, "CARTE DES THÈMES", after=4)
    para(doc, P["mindmap"], align="center", after=0)
    set_core_properties(doc, "Points clés · LinTO", "points-cles")
    doc.save(out)
    embed_fonts(out, inter_families())
    print("written", out)


if __name__ == "__main__":
    build(HERE.parent.parent / "templates" / "default" / "linto-points-cles.docx")
