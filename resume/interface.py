from resume.dictionnaires import Dictionary, read_epitran_dictionary
from resume.transcriptions import Transcription
from resume.utils import load_prompts, read_file_to_string

PROMPTS_DIR = 'prompts/'

class Interface:
    """Interface class for the resume module. Main use is llm-gateway"""

    def __init__(self, api_key, api_base, logger = None) -> None:
        self.api_key = api_key
        self.api_base = api_base
        self.logger = logger

    def generate_resume(self, cr_type : str, model_name : str, transcription : Transcription):
        trans = Transcription(transcription)
        trans.clean_original_file()
        trans.chuncked_transcription = trans.chunck_turns()
        if self.logger:
            self.logger.info("Cleaning the transcription and balise noms")
        # Cleaning the transcription and balise noms
        trans.apply_map(self.api_key, self.api_base, read_file_to_string('../resume/'+PROMPTS_DIR+'clean.txt'), max_call=5, model="meta-llama-3-8b-instruct")
        if self.logger:
            self.logger.info("Cleaning the names")
        # Clean the name with epitran

        epi_dic = Dictionary(read_epitran_dictionary('../transcription_db/noms_acteurs/acteurs_phonetic.csv'))

        modif = trans.clean_noms(epi_dic, threshold=0.8)
        if self.logger:
            self.logger.info(f"Noms modifiés : {modif}")

        if cr_type == 'cri':
            if self.logger:
                self.logger.info("Génération du CRA")
            return self.generate_cri(trans, model_name)
        elif cr_type == 'cra':
            if self.logger:
                self.logger.info("Génération du CRA")
            return self.generate_cra(trans, model_name)
        elif cr_type == 'cred':
            if self.logger:
                self.logger.info("Génération du CRED")
            return self.generate_cred(trans, model_name)
        else:
            if self.logger:
                self.logger.error(f"Format de CR non reconnu : {cr_type}")
        pass

    def generate_cri(self, transcription : Transcription, model_name : str) -> list[dict]:
        transcription.apply_map(self.api_key, self.api_base, PROMPTS['CRI'], max_call=5, model=model_name)
        return transcription.transcription

    def generate_cra(self, transcription : Transcription, model_name : str) -> list[dict]:
        transcription.apply_map(self.api_key, self.api_base, PROMPTS['CRA'], max_call=5, model=model_name)
        return transcription.transcription

    def generate_cred(self, transcription : Transcription, model_name : str) -> list[dict]:
        transcription.apply_map(self.api_key, self.api_base, PROMPTS['CRED'], max_call=5, model=model_name)
        return transcription.transcription

