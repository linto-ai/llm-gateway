import asyncio
import json
from datetime import time

import epitran

from config import create_parser
from corrections import generate_dictionary_epitran, Dictionary, read_epitran_dictionary
from summary import summarized_text
from transcriptions import Transcription


def main():
    """
    This function reads the configuration and calls the summarized_text function.
    """
    parser = create_parser()
    args = parser.parse_args()

    summarized_text(
        api_key=args.api_key,
        base_url=args.api_base,
        prompts_file=args.prompt_file,
        input_file=args.input_file,
        output_file=args.output_file,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        max_tokens=args.max_tokens
    )

PROMPT_CLEAN = "Je vais vous fournir un texte transcrit qui peut contenir des erreurs. \n### Veuillez corriger uniquement les erreurs d'orthographe, de grammaire et de ponctuation. ### Ne pas changer un mot sauf si celui ci rend la phrase incorrecte et que c'est certainement du a une erreur de restranscription. Le vocabulaire doit rester le même. \n### Entoure les prénoms et noms de famille avec des balises '<' et '>'. Ne mets pas de balises ailleurs et ne remplace aucun mot, les balises sont un ajout dans le texte. Utilise le contexte et ne mets des balises qu'aux noms de personnes. ### Contexte : Séance parlementaire au Sénat français. ### Donne le résultat directement sans introduction."

PROMPT_NOM = "Voici un texte issu d'une transciption. \n### Entoure les prénoms et noms de famille de personnes avec des balises '<' et '>'. Ne mets pas de balises ailleurs et ne remplace aucun mot, les balises sont un ajout dans le texte. Ne met pas de balise autour d'autre chose que des noms de personnes. "

PROMPT_LOCUTEUR = (" Voici un bout de transcription d'une séance parlementaire. "
                    "Il y a un président de séance et il parle souvent avec des formule du type 'La parole est à...', c'est lui qui dirige la séance"
                    "### Seul le président peu introduire des orateurs."
                    "### Si le président introduit un orateur retourne le nom de cet orateur dans des balises <SUIVANT> et <\SUIVANT>. Il ne peut y avoir qu'un unique orateur introduit."
                    "### Voici une sortie type: '<PRESIDENT> <SUIVANT> Eric Dupont <\SUIVANT>'. Respecte scrupuleusement ce format.")
if __name__ == "__main__":
    create_trans = True
    parser = create_parser()
    args = parser.parse_args()
    if create_trans:
        input_file = '../transcription_db/senat_test.json'
        with open(input_file, 'r') as file:
            dict_json = json.load(file)

        trans = Transcription(dict_json['segments'])
        trans.clean_original_file()
        trans.transcription = trans.transcription[:4]
        trans.chuncked_transcription = trans.chunck_turns()
        trans.apply_map(args.api_key, args.api_base, PROMPT_CLEAN, max_call=5, model =  "meta-llama-3-8b-instruct")
        with open('../transcription_db/senat_test_clean.json', 'w') as file:
            print('écriture du fichier')
            json.dump(trans.transcription, file, indent=4)

        epi_dic = Dictionary(read_epitran_dictionary('../transcription_db/noms_acteurs/acteurs_phonetic.csv'))

        modif = trans.clean_noms(epi_dic, threshold=0.8)

        print(modif)

        print(trans.transcription)
        with open('../transcription_db/senat_test_cri_v2.json', 'w') as file:
            print('\nEcriture du fichier\n')
            json.dump(trans.transcription, file, indent=4)

    input_file = '../transcription_db/senat_test_cri_v2.json'
    with open(input_file, 'r') as file:
        clean_trans = json.load(file)

    trans = Transcription(clean_trans)

    locuteurs = asyncio.run(trans.map_trancription(args.api_key, args.api_base, PROMPT_LOCUTEUR, max_call=5, model =  "meta-llama-3-8b-instruct"))

    print(locuteurs)





    def load_file_as_string(file_path):
        with open(file_path, 'r') as file:
            return file.read()


    # Remplacez 'acteurs_list.txt' par le chemin vers votre fichier

    file_content = load_file_as_string('../transcription_db/noms_acteurs/acteurs_list.txt')
    generate_dictionary_epitran('../transcription_db/noms_acteurs/acteurs_list.txt', '../transcription_db/noms_acteurs/acteurs_phonetic.csv')



    print("Modifications :")
    print(modif)

    # summarized_text(
    #     api_key=args.api_key,
    #     base_url=args.api_base,
    #     prompts_file="prompts.json",
    #     input_file="input_text.txt",
    #     output_file="resume.txt",
    #     chunk_size=1000,
    #     chunk_overlap=100,
    #     max_tokens=5000
    # )
