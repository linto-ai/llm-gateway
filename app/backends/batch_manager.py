import asyncio
from.openai_adapter import OpenAIAdapter
import logging
from itertools import chain
from conf import cfg_instance
from celery.result import AsyncResult

cfg = cfg_instance(cfg_name="config")

class BatchManager:
    def __init__(self, task_data: dict, tokenizer, prompt: str, prompt_token_count: int, celery_task):
        """
        Initializes the BatchManager with the task, tokenizer, and prompt-related parameters.

        Args:
            task (dict): Contains information about the task, including backend parameters and task ID.
            tokenizer (Tokenizer): The tokenizer to be used for tokenizing the input turns.
            prompt (str): The prompt template used for the summarization task.
            prompt_token_count (int): The number of tokens in the prompt.
        """
        self.tokenizer = tokenizer
        self.totalContextLength = task_data["backendParams"]['totalContextLength']
        self.maxGenerationLength = task_data["backendParams"]["maxGenerationLength"]
        self.prompt_token_count = prompt_token_count
        self.maxNewTurns = task_data["backendParams"]["maxNewTurns"]
        self.promptFields = task_data["fields"]
        self.summaryTurns = task_data["backendParams"]["summaryTurns"]
        self.prompt = prompt
        self.task_id = task_data['task_id']
        self.openai_adapter = OpenAIAdapter(task_data)
        self.celery_task = celery_task

        # Semaphore to control concurrent inferences
        self.semaphore = asyncio.Semaphore(cfg.semaphore.max_concurrent_inferences)

        # Logger for BatchManager
        self.logger = logging.getLogger("BatchManager")


    def get_prompt(self, summarized_turns: list, new_turns_to_summarize: list) -> str:
        """
        Constructs the prompt by inserting summarized turns and new turns.

        Args:
            summarized_turns (list): The previously summarized turns.
            new_turns_to_summarize (list): The new turns to be summarized.

        Returns:
            str: The formatted prompt with turns inserted.
        """
        # Format the prompt based on the number of fields (e.g., two fields or one)
        if self.promptFields == 2:
            return self.prompt.format('\n'.join(summarized_turns), '\n'.join(new_turns_to_summarize))
        return self.prompt.format('\n'.join(new_turns_to_summarize))


    def publish_turns(self, summarized_turns: list, new_turns_to_summarize: list) -> list:
        """
        Synchronously publishes a batch of turns by formatting the prompt, sending it to OpenAI, and processing the response.

        Args:
            summarized_turns (list): The previously summarized turns.
            new_turns_to_summarize (list): The new turns to be summarized.
            i (int): The index of the current turn in the list.
            turns (list): The full list of turns.

        Returns:
            list: The updated list of summarized turns.
        """
        # Inject new turns into the prompt
        filled_prompt = self.get_prompt(summarized_turns, new_turns_to_summarize)

        # Publish the prompt
        try :
            response = self.openai_adapter.publish(filled_prompt)
        
        except Exception as e:
            self.logger.error(f"Error publishing: {e}")
            raise
        
        # Handle None response
        if response is None:
            return self.progressive_summary + ['' for i in range(len(new_turns_to_summarize))]
        
        # Split the response into individual turns
        response_turns = [res for res in response.split('\n') if res.strip() != '']
        
        # Update the progressive summary
        self.progressive_summary.extend(response_turns)
        
        # Update the task progress
        self.update_task(len(new_turns_to_summarize))

        return self.progressive_summary[-self.summaryTurns:]
    

    async def publish_async_turns(self, new_turns_to_summarize: list) -> list:
        """
        Asynchronously publishes a batch of new turns to OpenAI.

        Args:
            new_turns_to_summarize (list): The new turns to be summarized.

        Returns:
            list: The list of turns returned by OpenAI.
        """
        # Inject new turns into the prompt
        filled_prompt = self.get_prompt([], new_turns_to_summarize)

        # Publish the prompt
        try :
            response = await self.openai_adapter.async_publish(filled_prompt)
        
        except Exception as e:
            self.logger.error(f"Error publishing: {e}")
            raise        
        
        # Handle None response
        if response is None:
            return self.progressive_summary + ['' for i in range(len(new_turns_to_summarize))]
        
        # Update the task progress
        self.update_task(len(new_turns_to_summarize))

        # Split the response into individual turns
        response_turns = [res for res in response.split('\n') if res.strip() != '']
        
        return response_turns
    

    def create_async_batches(self, turns: list) -> list:
        """
        Creates batches of turns for async, ensuring each batch does not exceed token limits.

        Args:
            turns (list): The list of turns to be batched.

        Returns:
            list: A list of batches, each containing a list of turns.
        """
        new_turns_to_summarize = []
        total_token_count=self.prompt_token_count
        batches = []
        i = 0
        # Gather turns for async processing
        while i < len(turns):
            turn = turns[i]
            turn_token_count = len(self.tokenizer(turn))

            # Check if the current batch is full
            if (total_token_count + turn_token_count) * 1.15 > self.totalContextLength - self.maxGenerationLength or len(new_turns_to_summarize) == self.maxNewTurns:
                # Store the current batch
                if new_turns_to_summarize:
                    batches.append(new_turns_to_summarize.copy())  # Store a copy of the current batch

                # Reset for the next batch
                new_turns_to_summarize = []
                total_token_count = self.prompt_token_count
            else:
                # Update the current batch
                new_turns_to_summarize.append(turn)
                total_token_count += turn_token_count
                i += 1
        
        # Gather remaining turns if any
        if new_turns_to_summarize:
            batches.append(new_turns_to_summarize)
        
        return batches

    async def run_async_batches(self, turns: list) -> list:
        """
        Processes the batches asynchronously.

        Args:
            turns (list): The list of turns to be processed.

        Returns:
            list: The combined list of processed turns from all batches.
        """
        # Create async batches
        batches = self.create_async_batches(turns)

        self.total_turns = len(turns)
        self.celery_task.update_state(state='PROGRESS', meta={'completed_turns': 0, 'total_turns': self.total_turns})

        # Use a semaphore to control the number of concurrent async tasks
        async with self.semaphore:
            tasks = [self.publish_async_turns(batch) for batch in batches]
        results = await asyncio.gather(*tasks)
        
        # Flatten the results to return a list of str
        results = list(chain.from_iterable(res for res in results if res is not None))

        return results

    def run_batches(self, turns: list) -> list:
        """
        Processes the batches synchronously.

        Args:
            turns (list): The list of turns to be processed.

        Returns:
            list: The final progressive summary after processing all batches.
        """
        self.progressive_summary = []
        new_turns_to_summarize = []
        summarized_turns = []
        total_token_count=self.prompt_token_count
        i = 0
        
        self.total_turns = len(turns)
        self.celery_task.update_state(state='PROGRESS', meta={'completed_turns': 0, 'total_turns': self.total_turns})
        # Process turn batches synchronously            
        while i < len(turns):
            turn = turns[i]
            turn_token_count = len(self.tokenizer(turn))
            if (total_token_count + turn_token_count)*1.15 > self.totalContextLength - self.maxGenerationLength or len(new_turns_to_summarize) == self.maxNewTurns:
                # Process current batch of turns
                summarized_turns = self.publish_turns(summarized_turns, new_turns_to_summarize)
                
                # Reset for next batch
                new_turns_to_summarize = []
                total_token_count = self.prompt_token_count + sum(len(self.tokenizer(turn)) for turn in summarized_turns)
            else:
                # Update current batch
                new_turns_to_summarize.append(turn)
                total_token_count += turn_token_count
                i += 1

        # Process remaining turns if any
        if new_turns_to_summarize:
            summarized_turns  = self.publish_turns(summarized_turns, new_turns_to_summarize) 

        return self.progressive_summary

    def reduce_summary(self, summary: list) -> str:
        """
        Publish summary if the total token count does not exceed the limit.

        Args:
            summary (list): The current summary to be reduced.

        Returns:
            str: The reduced summary.
        """
        self.logger.info("Reducing summary process started.")

        total_token_count = self.prompt_token_count + sum(len(self.tokenizer(turn)) for turn in summary)
        if total_token_count < self.totalContextLength - self.maxGenerationLength:
            return asyncio.run(self.publish_async_turns(summary))
        
        self.logger.info("Summary reduction input exceeds token limit.")
        return summary

    def update_task(self, nb_turns):
        result = AsyncResult(self.task_id)
        completed_turns = result.info['completed_turns'] + nb_turns
        self.celery_task.update_state(state='PROGRESS', meta={'completed_turns': completed_turns, 'total_turns': self.total_turns})


    
    @staticmethod
    def format_summary(summary: list) -> str:
        """Format the list of turns into a single string."""
        return "\n".join(summary)