import asyncio
import json
import re

from resume.dictionnaires import Dictionary
from resume.llm import LLM


class Transcription:
    """
    This class represents a transcription_db from a whisper transcription_db, it will allow us to manipulate it in a easy way
    to perform different operations ont it like parsing through LLMs, etc.
    """

    def __init__(self, transcription_json):
        self.original_transcription: list[dict] = group_by_speaker(transcription_json)
        self.transcription: list[dict] = self.original_transcription
        self.chuncked_transcription: list[dict] = self.chunck_turns()
        self.speaker = None

    def __len__(self):
        return len(self.chuncked_transcription)

    def __get__(self, i: int):
        return self.chuncked_transcription[i]

    def __iter__(self):
        return iter(self.chuncked_transcription)

    def __getitem__(self, i: int):
        return self.chuncked_transcription[i]

    def chunck_turns(self, max_length=4000):
        """
        This function will split the turns into smaller parts of max_length characters
        """
        chuncked_transcription = []
        for turn in self.transcription:
            splited = split_text_into_n_parts(turn['text'], len(turn['text']) // max_length + 1)
            for chunk in splited:
                chuncked_transcription.append({'speaker': turn['speaker'], 'text': chunk, 'start': turn['start']})
        return chuncked_transcription

    def reverse_chunck(self):
        """
        This function will reverse the chuncked transcription to the original format
        Used when modifying the chunked transcription to replace the original one
        """
        self.transcription = group_by_speaker(self.chuncked_transcription)

    def clean_original_file(self):
        """
        This function will clean the original file from the transcription by removing all the tags and regrouping the text
        by speaker
        """
        self.transcription = group_by_speaker(self.transcription)

    def get_transcription(self):
        """
        This function will return a copy of the transcription_db in a list of dictionaries format
        """
        trans = self.transcription.copy()
        for turn in trans:
            turn['text'] = ' '.join(turn['text'])
        return trans

    def save_transcription_as_json(self, file_path):
        """
        This function will save the transcription_db to a json file
        """
        with open(file_path, 'w') as file:
            json.dump(self.transcription, file, indent=4)

    def save_transcription_as_text(self, file_path):
        """
        This function will save the transcription_db to a text file
        """
        with open(file_path, 'w') as file:
            trans = self.get_transcription()
            for turn in trans:
                file.write(f"[{turn['speaker']}] [{turn['time']}]: {turn['text']}\n")

    def clean_noms(self, dictionary: Dictionary, threshold: float = 0.9) -> list:
        """
        Cleans the transcription by replacing all the tagged nouns with the best match from the dictionary.

        This function iterates over all transcriptions and finds all tagged nouns. For each noun, it finds the best match
        in the provided dictionary. If the match score is above the provided threshold, it replaces the noun with the best match.
        Otherwise, it removes the tags around the noun. It returns a list of modifications made.

        Args:
            dictionary (Dictionary): The dictionary to use for finding the best match.
            threshold (float, optional): The threshold for the match score. Defaults to 0.9.

        Returns:
            list: A list of modifications made in the format 'noun -> best_match'.
        """
        modifications = []

        # Iterate over all transcriptions
        for i in range(len(self.chuncked_transcription)):
            text = self.chuncked_transcription[i]['text']

            # Find all tagged nouns
            for match in re.finditer(r'<(.*?)>', text):
                noun = match.group(1)
                score, best_match = dictionary.get_best_match_with_score(noun)
                print(f'{noun} -> {best_match} ({score})')
                if score > threshold:
                    # Replace the noun with the best match
                    text = text.replace(f'<{noun}>', best_match)
                    modifications.append(f'{noun} -> {best_match}')
                else:
                    # Remove the tags around the noun
                    text = text.replace(f'<{noun}>', noun)

            self.chuncked_transcription[i]['text'] = text

        return modifications

    async def map_trancription(self, api_key: str, base_url: str, prompt: str, max_call: int = 5,
                               model: str = "meta-llama-3-8b-instruct") -> list:
        """
        Applies a prompt over a transcription asynchronously.

        This function takes an API key, base URL, prompt, maximum number of calls, and a model name. It uses these to map
        the transcription and return the responses.

        Args:
            api_key (str): The API key for OpenAI.
            base_url (str): The base URL for the OpenAI API.
            prompt (str): The prompt for the LLM.
            max_call (int, optional): The maximum number of API calls to make at once. Defaults to 5.
            model (str, optional): The model to use for the LLM. Defaults to "meta-llama-3-8b-instruct".

        Returns:
            list: A list of responses from the LLM.
        """
        from resume.resumer_llm import infer_llm_on_chunck

        # Initialize the LLM client
        llm = LLM(api_key=api_key, base_url=base_url, model=model)
        n = len(self)
        i = 0
        responses = []

        while i < n:
            result = await asyncio.gather(
                *[infer_llm_on_chunck(llm, prompt, turn, 6000) for turn in self[i:min(i + max_call, n)]])
            responses.extend(result)
            i += max_call

        return responses

    def replace_text(self, responses: list) -> None:
        """
        Replaces the text in the transcription with the responses.

        This function takes a list of responses (typically the result of a map_trancription)
        and replaces the text in the transcription with these responses.

        Args:
            responses (list): A list of responses to replace the text in the transcription.

        Returns:
            None
        """
        for turn in self.transcription:
            if responses:
                turn['text'] = responses.pop(0)['text']
            else:
                break

    def apply_map(self, api_key, base_url, prompt, max_call=5, model="meta-llama-3-8b-instruct"):
        """
        Applies a prompt over a transcription and replaces the text in the transcription with the responses.

        This function takes an API key, base URL, prompt, maximum number of calls, and a model name. It uses these to map
        the transcription and replace the text in the transcription with the responses. It then reverses the chunked
        transcription to the original format.

        Args:
            api_key (str): The API key for OpenAI.
            base_url (str): The base URL for the OpenAI API.
            prompt (str): The prompt for the LLM.
            max_call (int, optional): The maximum number of API calls to make at once. Defaults to 5.
            model (str, optional): The model to use for the LLM. Defaults to "meta-llama-3-8b-instruct".

        Returns:
            None
        """
        responses = asyncio.run(self.map_trancription(api_key, base_url, prompt, max_call, model))
        self.replace_text(responses)
        self.reverse_chunck()
        return None
    def speaker_to_int(self) -> None:
        """
        Converts the speaker in the transcription to int.
        """
        for turn in self.transcription:
            turn['speaker'] = speaker_to_int(turn['speaker'])
        for turn in self.chuncked_transcription:
            turn['speaker'] = speaker_to_int(turn['speaker'])


def group_by_speaker(data: list) -> list[dict]:
    """
    Groups the given data by speaker.

    This function takes a list of dictionaries where each dictionary represents a turn in a conversation.
    Each dictionary should have at least the keys 'speaker' and 'text'.
    The function groups the text by speaker, concatenating texts from the same speaker that appear consecutively.

    Args:
        data (list): A list of dictionaries where each dictionary represents a turn in a conversation.

    Returns:
        list: A list of dictionaries where each dictionary represents a grouped turn in the conversation speaker are converted to int.
    """
    grouped_data = []
    last_speaker = ''

    for item in data:
        speaker = item['speaker']
        if speaker == last_speaker:
            grouped_data[-1]['text'] += ' ' + item['text']
        else:
            grouped_data.append(
                {'speaker': speaker, 'text': item['text'], 'start': item['start']})
        last_speaker = speaker

    return grouped_data

def speaker_to_int(speaker: str) -> int:
    """
    Converts the given speaker string to an integer.

    This function takes a speaker string and converts it to an integer by extracting the numeric part of the string.

    Args:
        speaker (str): The speaker string to convert to an integer.

    Returns:
        int: The integer representation of the speaker string.
    """
    return int(speaker.split('_')[1])

def split_text_into_n_parts(text: str, n: int) -> list[str]:
    """
    Splits the given text into 'n' parts.

    This function takes a string and an integer 'n'. It splits the string into 'n' parts of approximately equal length.
    The splitting is done at sentence boundaries (i.e., '.', '!', '?') if possible, meaning sentences are not split across parts.

    Args:
        text (str): The text to be split.
        n (int): The number of parts to split the text into.

    Returns:
        list[str]: A list of strings representing the split parts of the text.
    """
    if n == 1:
        return [text]

    part_size = len(text) // n
    parts = []
    part_start = 0

    for i in range(len(text)):
        if text[i] in '.!?' and i - part_start >= part_size:
            parts.append(text[part_start:i + 1].strip())
            part_start = i + 1

    parts.append(text[part_start:].strip())  # Add the last part

    return parts
