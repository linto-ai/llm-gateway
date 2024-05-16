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
         "content": "Vous êtes un assistant spécialisé dans le résumé de conversations en francais et vous parlez uniquement francais dans un langage soutenu."},
        {"role": "user",
         "content": prompt},
        {"role": "user", "content": input_text},
    ]
    return chat_prompt
