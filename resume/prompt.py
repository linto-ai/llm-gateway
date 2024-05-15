class Prompt:
    """
    The Prompt class is used to generate chat prompts for a conversation.
    """

    def __init__(self):
        """
        Initialize the Prompt class.
        """
        pass

    def get_chat_prompt(self, prompt: str, input_text: str) -> list[dict]:
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