from .backend import LLMBackend
from typing import List, Tuple
from openai import OpenAI, AsyncOpenAI
import asyncio


class VLLM(LLMBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = kwargs.get('api_key')
        self.api_base = kwargs.get('api_base')
        self.logger.info(f"API Key: {self.api_key}")
        self.logger.info(f"API Base: {self.api_base}")
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)
        self.async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)
        self.semaphore = asyncio.Semaphore(3) 

        
    async def process_turns(self, summarized_turns, new_turns_to_summarize, i, turns):
        if self.promptFields == 2:
            filled_prompt = self.prompt.format('\n'.join(summarized_turns), '\n'.join(new_turns_to_summarize))
            response = self.publish(filled_prompt)
        else:
            filled_prompt = self.prompt.format('\n'.join(new_turns_to_summarize))
            response = await self.async_publish(filled_prompt)
        if response is None:
            return None
        response_turns = [res for res in response.split('\n') if res.strip() != '']
        self.progressiveSummary.extend(response_turns)
        # calculate percentage of turns handled
        percentage_handled = round((i / len(turns)) * 100, 2)
        self.updateTask(self.task_id, percentage_handled)

        return self.progressiveSummary[-self.summaryTurns:] if self.promptFields == 2 else summarized_turns

    async def reduce_summary(self, summary):
        if self.promptFields == 2:
            filled_prompt = self.prompt.format('','\n'.join(summary))
            response = self.publish(filled_prompt)
        else :
            filled_prompt = self.prompt.format('\n'.join(summary))
            response = await self.async_publish(filled_prompt)

        if response is None:
            return None
        response_turns = [res for res in response.split('\n') if res.strip() != '']
        return response_turns

    def consolidate_turns(self, turns: List[str]) -> List[str]:
        if not turns:
            return []

        consolidated_turns = []
        current_speaker = None
        current_turn = []

        for turn in turns:
            content, speaker = self.get_speaker(turn)
            # Remove speaker from content
            content = content[len(speaker):].strip()
            
            if speaker == current_speaker:
                current_turn.append(content)
            else:
                if current_turn:
                    consolidated_turns.append(f"{current_speaker} : {' '.join(current_turn)}")
                current_speaker = speaker
                current_turn = [content]

        if current_turn:
            consolidated_turns.append(f"{current_speaker}: {' '.join(current_turn)}")

        return consolidated_turns


    async def get_generation(self, turns: List[str]):
        self.progressiveSummary = []
        total_token_count = self.promptTokenCount
        new_turns_to_summarize = []
        summarized_turns = []
        i = 0
        # Synchronous processing if Refined Summary
        if self.promptFields == 2: 
            while i < len(turns):
                turn = turns[i]
                turn_token_count = len(self.tokenizer(turn))
                # Add a *0.15 buffer to the token count to ensure we don't go over the limit. Due to token count being an approximation (local token count vs. API token count)
                # @TODO : again, we shall use relevant tokenizer from the model name. But auto-tokenizer is not available for some models
                if (total_token_count + turn_token_count)*1.15 > self.totalContextLength - self.maxGenerationLength or len(new_turns_to_summarize) == self.maxNewTurns:
                    # Process current batch of turns
                    summarized_turns = await self.process_turns(summarized_turns, new_turns_to_summarize, i, turns)
                    # Reset for next batch
                    new_turns_to_summarize = []
                    total_token_count = self.promptTokenCount
                    if self.promptTokenCount == 2 :
                        total_token_count += sum(len(self.tokenizer(turn)) for turn in summarized_turns)
                else:
                    new_turns_to_summarize.append(turn)
                    total_token_count += turn_token_count
                    i += 1

            # Process remaining turns if any
            if new_turns_to_summarize:
                summarized_turns  = await self.process_turns(summarized_turns, new_turns_to_summarize, i, turns)
        
        # Asynchronous processing if not Map Reduce Summary
        else: 
            batches = []
            # Gather turns for async processing
            while i < len(turns):
                turn = turns[i]
                turn_token_count = len(self.tokenizer(turn))

                if (total_token_count + turn_token_count) * 1.15 > self.totalContextLength - self.maxGenerationLength or len(new_turns_to_summarize) == self.maxNewTurns:
                    # Store the current batch
                    if new_turns_to_summarize:
                        batches.append(new_turns_to_summarize.copy())  # Store a copy of the current batch

                    # Reset for the next batch
                    new_turns_to_summarize = []
                    total_token_count = self.promptTokenCount
                    if self.promptTokenCount == 2:
                        total_token_count += sum(len(self.tokenizer(turn)) for turn in summarized_turns)
                else:
                    new_turns_to_summarize.append(turn)
                    total_token_count += turn_token_count
                    i += 1
            # Process remaining turns if any
            if new_turns_to_summarize:
                batches.append(new_turns_to_summarize)
            # Process batches asynchronously
            async with self.semaphore:
                tasks = [self.process_turns([],batch, i, turns) for batch in batches]
                await asyncio.gather(*tasks)


        # Reduce summary
        if self.reduceSummary :
            total_token_count = self.promptTokenCount + sum(len(self.tokenizer(turn)) for turn in self.progressiveSummary)
            if total_token_count < self.totalContextLength - self.maxGenerationLength:
                self.progressiveSummary = await self.reduce_summary(self.progressiveSummary)
            else :
                return self.get_generation(self.progressiveSummary)
        
        # consolidate turns for progressive summary
        if self.consolidateSummary:
            self.progressiveSummary = self.consolidate_turns(self.progressiveSummary)

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

    async def async_publish(self, content: str):
        try:
            chat_response = await self.async_client.chat.completions.create(
                model=self.modelName,
                messages=[{"role": "user", "content": content}],
                temperature=self.temperature,
                top_p=self.top_p,
                max_tokens=self.maxGenerationLength
            )
            return chat_response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error publishing: {e}")
            return None