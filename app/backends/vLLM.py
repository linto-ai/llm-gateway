from .backend import LLMBackend
from typing import List, Tuple
from openai import OpenAI


class VLLM(LLMBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = kwargs.get('api_key')
        self.api_base = kwargs.get('api_base')
        self.logger.info(f"API Key: {self.api_key}")
        self.logger.info(f"API Base: {self.api_base}")
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)

    def get_generation(self, turns: List[str]):
        self.progressiveSummary = []
        total_token_count = self.promptTokenCount
        new_turns_to_summarize = []
        summarized_turns = []
        # If we have 2 prompt fields, we contextualize the prompt with the last self.summaryTurns turns  
        if self.promptFields == 2:
            summarized_turns = self.progressiveSummary[-self.summaryTurns:]
            total_token_count += sum(len(self.tokenizer(turn)) for turn in summarized_turns)
        i = 0
        while i < len(turns):
            turn = turns[i]
            turn_token_count = len(self.tokenizer(turn))
            # Add a *0.15 buffer to the token count to ensure we don't go over the limit. Due to token count being an approximation (local token count vs. API token count)
            # @TODO : again, we shall use relevant tokenizer from the model name. But auto-tokenizer is not available for some models
            if (total_token_count + turn_token_count)*1.15 > self.totalContextLength - self.maxGenerationLength or len(new_turns_to_summarize) == self.maxNewTurns:
                if self.promptFields == 2:
                    filled_prompt = self.prompt.format('\n'.join(summarized_turns), '\n'.join(new_turns_to_summarize))
                else:
                    filled_prompt = self.prompt.format('\n'.join(new_turns_to_summarize))
                response = self.publish(filled_prompt)
                if response is None:
                    return None
                response_turns = response.split('\n')
                self.progressiveSummary.extend(response_turns)
                # calculate percentage of turns handled
                percentage_handled = round((i / len(turns)) * 100, 2)
                self.updateTask(self.task_id, percentage_handled)
                # Reset for next batch
                new_turns_to_summarize = []
                total_token_count = self.promptTokenCount
                if self.promptFields == 2:
                    summarized_turns = self.progressiveSummary[-self.summaryTurns:]
                    total_token_count += sum(len(self.tokenizer(turn)) for turn in summarized_turns)
            else:
                new_turns_to_summarize.append(turn)
                total_token_count += turn_token_count
                i += 1

        return self.progressiveSummary
    
    def publish(self, content: str):
        try:
            chat_response = self.client.chat.completions.create(
                model=self.modelName,
                
                messages=[
                    {"role": "user", "content": content}
                ],
                temperature=self.temperature,
                top_p=self.top_p,
                max_tokens=self.maxGenerationLength
            )
            return chat_response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error publishing: {e}")
            return None
