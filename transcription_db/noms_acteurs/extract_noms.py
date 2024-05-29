import os
import json

from resume.dictionnaires import generate_dictionary_epitran


def extract_names_from_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        prenom = data['acteur']['etatCivil']['ident']['prenom']
        nom = data['acteur']['etatCivil']['ident']['nom']
        return f"{prenom} {nom}", nom

directory_path = 'acteurs'  # replace with your directory path
output_file_path = 'acteurs_list.txt'  # replace with your output file path

with open(output_file_path, 'w') as output_file:
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            full_name, last_name = extract_names_from_file(os.path.join(directory_path, filename))
            output_file.write(f"{full_name}\n")
            output_file.write(f"{last_name}\n")

generate_dictionary_epitran('acteurs_list.txt', 'acteurs_phonetic.csv')
