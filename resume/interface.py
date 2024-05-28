class Interface:
    """Interface class for the resume module. Main use is llm-gateway"""
    def __init__(self, api_key, api_base) -> None:
        self.api_key = api_key
        self.api_base = api_base

    def generate_resume(self, cr_type, model_name, transcription):
        if cr_type == 'cri':
            return self.generate_cri(transcription, cr_type, model_name)
        pass

    def generate_cri(self, transcription, cr_type, model_name) -> list[dict]:
    ### Il faut faire en sorte que le format qui arrive ici est de la bonne forme sinon l'interfacer
        return None


