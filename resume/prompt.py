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

class Prompt:
    """
    The Prompt class is used to generate chat prompts for a conversation.
    """

    def __init__(self):
        """
        Initialize the Prompt class.
        """
        pass


BASIC_PROMPT_MAP="Résume moi ce bout de transcription d'une réunion professionelle en quatre lignes maximum. Ne rentre pas dans les détails, mais donne moi toujours des phrases ou l'on sait de quoi et de qui l'on parle. Garde une cohérence dans les phrases grace à tes connaissance, cela doit toujouts être logique. Il s'agit d'une transcription et que celle ci peut-être partiellement incorecte. Chaque sujet serra séparé par un '\n'."
BASIC_PROMPT_REDUCE="Tu disposes de plusieurs résumés issus de differents extraits d'une réunion professionelle venant d'une transcription. \n ### Fais une phrase pour présenter le sujet général de la réunion. \n ### Regroupe les résumés par thèmes de taille similaires (maximum quatre thèmes) supprime les doublons et synthétise. \n Prend soin d'avoir une cohérence, on doit toujours pouvroi savoir de qui et de quoi on parle.\n"
