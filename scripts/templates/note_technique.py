"""Build the « Note technique » template. Run: python scripts/templates/note_technique.py -> templates/default/linto-note-technique.docx"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from docx_kit import *  # noqa: E402,F403

PURPLE, PURPLE_DARK = "6D28D9", "4C1D95"

P = {
    "titre": "{{titre: sujet technique traité en 4 à 9 mots, sans date, déduit de la section En bref}}",
    "accroche": "{{accroche: une phrase de 30 mots maximum : le problème et ce qui est tranché, tirée de la section En bref}}",
    "nb_options": "{{nb_options: nombre de puces de la section Options étudiées, en chiffres, 0 si Aucune}}",
    "nb_decisions": "{{nb_decisions: nombre de puces de la section Décisions actées, en chiffres, 0 si aucune décision}}",
    "nb_actions": "{{nb_actions: nombre de puces de la section Plan d'action, en chiffres}}",
    "nb_risques": "{{nb_risques: nombre de puces de la section Risques, en chiffres, 0 si Aucun}}",
    "contexte": "{{contexte: la section Contexte et problème, 4 puces au maximum, une par ligne commençant par • suivi d'un espace, 16 mots maximum chacune}}",
    "constats": "{{constats: les constats les plus importants de la section Constats, 5 au maximum, une par ligne commençant par • suivi d'un espace, chiffre clé en gras, 16 mots maximum chacun}}",
    "options": "{{options: les options de la section Options étudiées, 5 au maximum, les retenues d'abord}}",
    "opt_n": "{{options.option: nom court de l'option, 6 mots maximum}}",
    "opt_a": "{{options.apports: ce qu'elle apporte, 14 mots maximum}}",
    "opt_l": "{{options.limites: ses limites, 14 mots maximum}}",
    "opt_s": "{{options.statut: exactement Retenue, Écartée ou À étudier}}",
    "decisions": "{{decisions: les décisions de la section Décisions actées, 4 au maximum, une par ligne commençant par • suivi d'un espace, 18 mots maximum, Aucune décision actée si la section est vide}}",
    "actions": "{{actions: les actions de la section Plan d'action, 8 au maximum}}",
    "act_p": "{{actions.porteur: nom du porteur tel qu'écrit}}",
    "act_a": "{{actions.action: l'action, 16 mots maximum}}",
    "act_e": "{{actions.echeance: l'échéance telle qu'écrite, ou non fixée}}",
    "risques": "{{risques: les risques de la section Risques, 4 au maximum, les plus graves d'abord}}",
    "rsk_r": "{{risques.risque: le risque, 12 mots maximum}}",
    "rsk_i": "{{risques.impact: l'impact, 12 mots maximum}}",
    "rsk_p": "{{risques.parade: la parade discutée, 12 mots maximum, ou non discutée}}",
    "questions": "{{questions: les questions de la section Questions ouvertes, 4 au maximum, une par ligne commençant par • suivi d'un espace, 15 mots maximum chacune, Aucune si la section est vide}}",
    "composants": "{{composants: les éléments de la section Composants et références, 6 au maximum, un par ligne commençant par • suivi d'un espace, le nom en gras puis son rôle en 6 mots maximum}}",
}


def build(out):
    doc = service_document(P["titre"], ["{{conversation_name}}", "{{organization_name}}", "Note du {{job_date}}"])
    card = Card(doc, ["pad", "header", "gap", "tiles", "gap", "context", "gap", "t_opt", "h_opt", "opt", "gap",
                      "decisions", "gap", "t_act", "h_act", "act", "gap", "t_rsk", "h_rsk", "rsk", "gap", "bottom", "pad"])
    card.header("header", "NOTE TECHNIQUE", P["accroche"], color=PURPLE)
    card.tiles("tiles", [("OPTIONS ÉTUDIÉES", P["nb_options"], 20), ("DÉCISIONS", P["nb_decisions"], 20),
                         ("ACTIONS", P["nb_actions"], 20), ("RISQUES", P["nb_risques"], 20)],
               accent=PURPLE, value_color=PURPLE_DARK)
    card.panel("context", 1, 3, "CONTEXTE ET PROBLÈME", P["contexte"], GREY)
    card.panel("context", 5, 7, "CONSTATS", P["constats"], PURPLE)
    card.title("t_opt", "OPTIONS ÉTUDIÉES", PURPLE_DARK)
    spans = [(1, 2), (3, 4), (5, 6), (7, 7)]
    card.columns("h_opt", spans, ["OPTION", "APPORTS", "LIMITES", "STATUT"], fill=PURPLE_DARK)
    card.repeated("opt", spans, [(P["options"] + P["opt_n"], 9, INK, True), (P["opt_a"], 8.5, INK, False),
                                 (P["opt_l"], 8.5, INK, False), (P["opt_s"], 9, PURPLE, True)])
    card.panel("decisions", 1, 7, "DÉCISIONS ACTÉES", P["decisions"], LINTO_GREEN)
    card.title("t_act", "PLAN D'ACTION", INK)
    spans = [(1, 1), (2, 5), (6, 7)]
    card.columns("h_act", spans, ["PORTEUR", "ACTION", "ÉCHÉANCE"])
    card.repeated("act", spans, [(P["actions"] + P["act_p"], 9, INK, True), (P["act_a"], 9, INK, False),
                                 (P["act_e"], 9, PURPLE, False)])
    card.title("t_rsk", "RISQUES", ALERT_RED)
    spans = [(1, 3), (4, 5), (6, 7)]
    card.columns("h_rsk", spans, ["RISQUE", "IMPACT", "PARADE"], fill=ALERT_RED)
    card.repeated("rsk", spans, [(P["risques"] + P["rsk_r"], 9, INK, True), (P["rsk_i"], 8.5, INK, False),
                                 (P["rsk_p"], 8.5, INK, False)])
    card.panel("bottom", 1, 3, "QUESTIONS OUVERTES", P["questions"], AMBER)
    card.panel("bottom", 5, 7, "COMPOSANTS ET RÉFÉRENCES", P["composants"], PURPLE_DARK)
    card.finish()
    section_label(doc, "NOTE DÉTAILLÉE")
    para(doc, "{{output}}")
    set_core_properties(doc, "Note technique · LinTO", "note-technique")
    doc.save(out)
    embed_fonts(out, inter_families())
    print("written", out)


if __name__ == "__main__":
    build(HERE.parent.parent / "templates" / "default" / "linto-note-technique.docx")
