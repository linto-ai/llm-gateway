import asyncio
import json
from datetime import time
import re

from config import create_parser
from resume.dictionnaires import generate_dictionary_epitran, Dictionary, read_epitran_dictionary
from resume.resumer_llm import summarized_text
from resume.transcriptions import Transcription


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
def read_file_to_string(file_path):
    with open(file_path, 'r') as file:
        return file.read()


def reformat_in(transcription):
    """
    Reformat the transcription to the format that the interface can understand
    """
    lines = transcription.split('\n')
    result = []
    for i, line in enumerate(lines):
        match = re.match(r'(.*?):\s(.*)', line)
        if match:
            speaker, text = match.groups()
            result.append({'speaker': speaker, 'start': i, 'text': text})
    return result


PROMPT_CLEAN = read_file_to_string('prompts/clean.txt')
if __name__ == "__main__":
    create_trans = True
    parser = create_parser()
    args = parser.parse_args()
    trans = Transcription(reformat_in(read_file_to_string('../transcription_db/exemple.txt')))
    trans.clean_original_file()
    trans.transcription = trans.transcription[:4]
    trans.chuncked_transcription = trans.chunck_turns()
    trans.apply_map(args.api_key, args.api_base, PROMPT_CLEAN, max_call=5, model =  "meta-llama-3-70b-instruct")
    with open('../transcription_db/exemple_clean.json', 'w') as file:
        print('écriture du fichier')
        json.dump(trans.transcription, file, indent=4)

    epi_dic = Dictionary(read_epitran_dictionary('../transcription_db/noms_acteurs/acteurs_phonetic.csv'))

    modif = trans.clean_noms(epi_dic, threshold=0.8)

    with open('../transcription_db/exemple_correct_names.json', 'w') as file:
        print('écriture du fichier')
        json.dump(trans.transcription, file, indent=4)

    print(modif)