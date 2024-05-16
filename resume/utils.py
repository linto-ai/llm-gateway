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
