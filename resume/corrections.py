import csv
import epitran
import argparse
import os
from tqdm import tqdm
import Levenshtein


class Dictionary:
    def __init__(self, epitran_dict, epitran_instance: str = 'fra-Latn-p'):
        self.epitran_instance = epitran.Epitran(epitran_instance)
        self.epitran_dict = epitran_dict

    def get_best_match_with_score(self, noum_words: str) -> tuple[float, str]:
        """
        Returns the best match for a given word in the epitran dictionary along with the score.
        The score is the normalized Jaro-Winkler score.
            Args:
                noum_words (str): The word to be matched.
            Returns:
                tuple[float, str]: The normalized Jaro-Winkler score and the matched word.
        """
        results = [(Levenshtein.ratio(noum_words, self.epitran_dict[key]), self.epitran_dict[key]) for key in
                   self.epitran_dict]
        max_result = max(results, key=lambda x: x[0])
        return max_result


def generate_dictionary_epitran(txt_file: str, csv_output: 'str') -> None:
    """
    Generates a dictionary with phonetic transcriptions of words using Epitran.
    Args:
        txt_file (str): The path to the text file containing the names.
        csv_output (str): The path to the CSV file to save the dictionary.
    """
    epi = epitran.Epitran('fra-Latn-p')  # French language code for Epitran
    phonetic_dict = {}

    with open(txt_file, 'r') as file:
        for line in file:
            word = line.strip()  # Remove newline characters
            phonetic = epi.transliterate(word)
            phonetic_dict[word] = phonetic

    with open(csv_output, 'w') as file:
        for word, phonetic in phonetic_dict.items():
            file.write(f"{word};{phonetic}\n")
    return None


def read_epitran_dictionary(file_path):
    """
    Reads the CSV file and returns a dictionary with names phonetic transcriptions as keys.
    """
    epitran_dict = {}
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        for row in reader:
            if row:
                correct_word = row[0]
                ipa_transcription = row[1]
                epitran_dict[ipa_transcription] = correct_word
    return epitran_dict
