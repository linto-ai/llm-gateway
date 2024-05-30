import json
import re

RESUME_TYPE = ['refine', 'map_reduce']


def load_file(file_path: str) -> str:
    """
    Reads a file and returns its content.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The content of the file.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def load_prompts(prompts_file: str) -> dict:
    """
    Loads prompts from a file.

    Args:
        prompts_file (str): The path to the prompts file.

    Returns:
        dict: The loaded prompts.
    """
    with open(prompts_file, "r") as file:
        prompts = json.loads(file.read())
    return prompts


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """
    Splits a given text into chunks of a specified size with a specified overlap.

    Args:
        text (str): The text to be split.
        chunk_size (int): The desired size of each chunk.
        chunk_overlap (int): The desired overlap between chunks.

    Returns:
        list[str]: A list of text chunks.
    """
    chunks = []
    for i in range(0, len(text), chunk_size - chunk_overlap):
        chunks.append(text[i:i + chunk_size])
    return chunks


def get_chat_prompt(prompt: str, input_text: str) -> list[dict]:
    """
    Generate a chat prompt for a conversation.

    Args:
        prompt (str): The initial prompt for the conversation.
        input_text (str): The user's input text for the conversation.

    Returns:
        list[dict]: A list of dictionaries representing the chat prompt.
    """
    chat_prompt = [
        {"role": "system",
         "content": "Vous êtes un assistant spécialisé dans le résumé de conversations en francais et vous parlez uniquement francais dans une langage similaire ce celui qui vous ai donné."},
        {"role": "user",
         "content": prompt + "### Veuillez retourner le texte modifié en l'encadrant avec les balises <TEXTE> et </TEXTE>. Assurez-vous que tout le texte modifié est inclus entre ces balises."},
        {"role": "user", "content": "<TEXTE>" + input_text + "</TEXTE>"},
        {"role": "assistant", "content": "<TEXTE>"}
    ]
    return chat_prompt

def find_string_in_text(text: str, pattern: str) -> str:
    """
    Finds a string in a text using a regular expression pattern.

    Args:
        text (str): The text to search in.
        pattern (str): The regular expression pattern to match.

    Returns:
        str: The matched string.
    """
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    return matches

def get_text_inside_tags(text: str) -> str:
    pattern = r'<TEXTE>(.*?)</TEXTE>'
    try:
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)[-1]
        return matches
    except:
        print('*** Probleme de balise ***')
        return pattern

def read_file_to_string(file_path):
    with open(file_path, 'r') as file:
        return file.read()