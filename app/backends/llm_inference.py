import asyncio
from .backend import LLMBackend
from .batch_manager import BatchManager
from .document import DocGenerator

class LLMInferenceEngine(LLMBackend):
    def __init__(self, task_data: dict, celery_task):
        super().__init__(task_data)
        self.batch_manager = BatchManager(task_data,self.tokenizer, self.prompt, self.prompt_token_count, self.reduce_prompt, celery_task)
        if self.task_type == "document":
            self.doc_generator = DocGenerator(task_data, self.batch_manager.openai_adapter)

    def run(self) -> str:
        """
        Runs the summarization pipeline on the input content, processing it through different stages to generate a final summary.

        The method first chunks the input content and then processes it based on the value of `promptFields`:
        - If `promptFields` equals 2, the method performs synchronous processing using the batch manager.
        - If `promptFields` is not 2, the method uses asynchronous processing for batch processing.
        
        After processing, additional operations are applied:
        - If `reduceSummary` is `True`, the summary is further reduced using the batch manager.
        - If `consolidateSummary` is `True`, the summary is consolidated into fewer turns using the chunker.
        
        Finally, the method formats and returns the processed summary.

        Returns:
            str: The final formatted summary after processing, reduction, and consolidation, as required.
        """
        # Chunk input content
        chunked_content = self.chunker.get_splits(self.content)

        # Synchronous processing if Refined Summary
        if self.promptFields == 2: 
            self.summary = self.batch_manager.run_batches(chunked_content)
        
        # Asynchronous processing if Map Reduce Summary
        else: 
            self.summary = asyncio.run(self.batch_manager.run_async_batches(chunked_content))

        # Reduce summary
        if self.reduceSummary :
            self.summary = self.batch_manager.reduce_summary(self.summary)
        
        # consolidate turns for progressive summary
        if self.consolidateSummary:
            self.summary = self.chunker.consolidate_turns(self.summary)
        
        self.summary = self.batch_manager.format_summary(self.summary)
        
        if self.task_type == "document":
            self.summary = self.doc_generator.run(self.summary)

        return self.summary
