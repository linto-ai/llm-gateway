"""Build the « Brief commercial » template. Run: python scripts/templates/brief_commercial.py -> templates/default/linto-brief-commercial.docx"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from docx_kit import *  # noqa: E402,F403

BLUE, BLUE_DARK = "2B5797", "1E3F73"

P = {
    "compte": "{{compte: nom de l'organisation cliente, valeur de la ligne Organisation de la section Compte, sans forme juridique}}",
    "accroche": "{{accroche: une phrase de 30 mots maximum qui dit ce que veut le client et où en est l'affaire, tirée de la section En bref}}",
    "volumetrie": "{{volumetrie: valeur de la ligne Taille ou volumétrie de la section Compte, 4 mots maximum, par exemple 1 500 utilisateurs, non précisée sinon}}",
    "budget": "{{budget: budget ou montant principal cité dans la section Chiffres et calendrier, avec son unité, 4 mots maximum, non précisé sinon}}",
    "echeance": "{{echeance_client: date clé du client dans la section Chiffres et calendrier (appel d'offres, décision, mise en service), 6 mots maximum, non précisée sinon}}",
    "etape": "{{prochaine_etape: la section Prochaine étape en 12 mots maximum}}",
    "besoins": "{{besoins: les besoins de la section Besoin, 5 au maximum, un par ligne commençant par • suivi d'un espace, 14 mots maximum chacun}}",
    "interlocuteurs": "{{interlocuteurs: les interlocuteurs de la ligne Interlocuteurs de la section Compte, un par ligne commençant par • suivi d'un espace, le nom en gras puis la fonction si elle est dite, puis une dernière ligne • Existant : valeur de la ligne Existant}}",
    "objections": "{{objections: les objections de la section Objections et réponses, 6 au maximum, les plus bloquantes d'abord}}",
    "obj_o": "{{objections.objection: l'objection du client, 14 mots maximum}}",
    "obj_r": "{{objections.reponse: la réponse apportée, 18 mots maximum, ou Sans réponse}}",
    "engagements": "{{engagements: les engagements de la section Engagements, 6 au maximum}}",
    "eng_p": "{{engagements.porteur: nom de la personne qui porte l engagement ; si le compte rendu indique Vendeur, Client ou une organisation, écrire Participant non identifié}}",
    "eng_e": "{{engagements.engagement: l'engagement, 16 mots maximum}}",
    "eng_d": "{{engagements.echeance: l'échéance telle qu'écrite, ou non fixée}}",
    "references": "{{references: les références et arguments de la section Références et arguments, 5 au maximum, un par ligne commençant par • suivi d'un espace, le client ou le chiffre en gras, 16 mots maximum chacun}}",
    "vigilance": "{{vigilance: les points de la section Points de vigilance, 4 au maximum, un par ligne commençant par • suivi d'un espace, 15 mots maximum chacun, Aucun si la section est vide}}",
}


def build(out):
    doc = service_document(P["compte"], ["{{conversation_name}}", "{{organization_name}}", "Brief du {{job_date}}"])
    card = Card(doc, ["pad", "header", "gap", "tiles", "gap", "needs", "gap", "t_obj", "h_obj", "obj", "gap",
                      "t_eng", "h_eng", "eng", "gap", "bottom", "pad"])
    card.header("header", "BRIEF COMMERCIAL", P["accroche"], color=BLUE)
    card.tiles("tiles", [("VOLUMÉTRIE", P["volumetrie"], 14), ("BUDGET", P["budget"], 14),
                         ("ÉCHÉANCE CLIENT", P["echeance"], 11), ("PROCHAINE ÉTAPE", P["etape"], 9)],
               accent=BLUE, value_color=BLUE_DARK)
    card.panel("needs", 1, 3, "BESOINS DU CLIENT", P["besoins"], BLUE)
    card.panel("needs", 5, 7, "INTERLOCUTEURS", P["interlocuteurs"], GREY)
    card.title("t_obj", "OBJECTIONS ET RÉPONSES", AMBER)
    card.columns("h_obj", [(1, 3), (4, 7)], ["OBJECTION DU CLIENT", "RÉPONSE APPORTÉE"], fill=AMBER)
    card.repeated("obj", [(1, 3), (4, 7)], [(P["objections"] + P["obj_o"], 9, INK, True), (P["obj_r"], 9, INK, False)])
    card.title("t_eng", "ENGAGEMENTS", BLUE_DARK)
    card.columns("h_eng", [(1, 1), (2, 5), (6, 7)], ["PORTEUR", "ENGAGEMENT", "ÉCHÉANCE"], fill=BLUE_DARK)
    card.repeated("eng", [(1, 1), (2, 5), (6, 7)], [(P["engagements"] + P["eng_p"], 9, INK, True),
                                                    (P["eng_e"], 9, INK, False), (P["eng_d"], 9, BLUE, False)])
    card.panel("bottom", 1, 3, "RÉFÉRENCES ET ARGUMENTS", P["references"], LINTO_GREEN)
    card.panel("bottom", 5, 7, "POINTS DE VIGILANCE", P["vigilance"], ALERT_RED)
    card.finish()
    section_label(doc, "BRIEF DÉTAILLÉ")
    para(doc, "{{output}}")
    set_core_properties(doc, "Brief commercial · LinTO", "brief-commercial")
    doc.save(out)
    embed_fonts(out, inter_families())
    print("written", out)


if __name__ == "__main__":
    build(HERE.parent.parent / "templates" / "default" / "linto-brief-commercial.docx")
