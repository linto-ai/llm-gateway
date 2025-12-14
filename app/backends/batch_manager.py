from datetime import datetime
from.openai_adapter import OpenAIAdapter
import logging
from celery.result import AsyncResult
from celery.exceptions import TaskRevokedError
from typing import Optional, Dict, Any, List

class BatchManager:
    def __init__(self, task_data: dict, tokenizer, prompt: str, prompt_token_count: int, reduce_prompt:str , celery_task):
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
        self.reduce_prompt = reduce_prompt
        self.task_id = task_data['task_id']
        self.celery_task = celery_task
        self.total_retries = 0

        # Create adapter with retry callback to update Celery state
        self.openai_adapter = OpenAIAdapter(task_data, retry_callback=self._on_llm_retry)

        # Logger for BatchManager
        self.logger = logging.getLogger("BatchManager")

        # Token metrics tracking
        self.pass_metrics: List[Dict[str, Any]] = []
        self.current_pass_number = 0

        # Cost estimation rate from flavor (None = no cost estimation)
        self.cost_per_1k_tokens = task_data["backendParams"].get("estimated_cost_per_1k_tokens")

        # Phase tracking for multi-step processing
        # Phases: "processing", "reducing", "generating_document"
        self.current_phase: str = "processing"

    def check_if_revoked(self) -> None:
        """Check if the task has been revoked and raise TaskRevokedError if so.

        This should be called at strategic points (between batches, before LLM calls)
        to allow graceful cancellation of long-running tasks.
        """
        # Check Celery's revoked tasks list

        # inspect().revoked() returns dict of worker -> revoked task ids
        # For faster check, we use abortable tasks pattern with Redis
        try:
            from app.http_server.celery_app import redis_client
            is_revoked = redis_client.sismember("revoked_tasks", self.task_id)
            if is_revoked:
                self.logger.info(f"Task {self.task_id} was revoked - stopping execution")
                raise TaskRevokedError(f"Task {self.task_id} was revoked")
        except Exception as e:
            # If Redis check fails, continue (don't break task execution)
            if isinstance(e, TaskRevokedError):
                raise
            self.logger.debug(f"Could not check revocation status: {e}")

    def _record_pass_metrics(
        self,
        pass_type: str,
        start_time: datetime,
        usage: Dict[str, int],
        input_chars: int,
        output_chars: int
    ) -> None:
        """Record metrics for a completed pass."""
        self.current_pass_number += 1
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        metrics = {
            "pass_number": self.current_pass_number,
            "pass_type": pass_type,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_ms": duration_ms,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "input_chars": input_chars,
            "output_chars": output_chars,
            "estimated_cost": self._estimate_cost(usage),
        }
        self.pass_metrics.append(metrics)

        # Update Celery state with metrics
        self._update_task_with_metrics()

    def _estimate_cost(self, usage: Dict[str, int]) -> Optional[float]:
        """Estimate cost based on flavor's configured cost_per_1k_tokens."""
        # If no cost rate configured on flavor, skip cost estimation
        if self.cost_per_1k_tokens is None:
            return None

        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = prompt_tokens + completion_tokens

        if total_tokens == 0:
            return None

        # Use flavor's configured rate (cost per 1K tokens)
        cost = (total_tokens / 1000.0) * self.cost_per_1k_tokens
        return round(cost, 6)

    def _get_cumulative_metrics(self) -> Optional[Dict[str, Any]]:
        """Calculate cumulative metrics across all passes."""
        if not self.pass_metrics:
            return None

        total_prompt = sum(p["prompt_tokens"] for p in self.pass_metrics)
        total_completion = sum(p["completion_tokens"] for p in self.pass_metrics)
        total_duration = sum(p["duration_ms"] for p in self.pass_metrics)
        total_cost = sum(p["estimated_cost"] or 0 for p in self.pass_metrics)
        num_passes = len(self.pass_metrics)

        return {
            "passes": self.pass_metrics,
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_prompt + total_completion,
            "total_duration_ms": total_duration,
            "total_estimated_cost": round(total_cost, 6) if total_cost > 0 else None,
            "avg_tokens_per_pass": (total_prompt + total_completion) / num_passes if num_passes > 0 else 0,
            "avg_duration_per_pass_ms": total_duration / num_passes if num_passes > 0 else 0,
        }

    def _update_task_with_metrics(self) -> None:
        """Update Celery task state with current metrics."""
        cumulative = self._get_cumulative_metrics()
        current_pass = self.pass_metrics[-1] if self.pass_metrics else None

        # Build current pass metrics for WebSocket
        current_pass_metrics = None
        if current_pass:
            current_pass_metrics = {
                "pass_number": current_pass["pass_number"],
                "pass_type": current_pass["pass_type"],
                "prompt_tokens": current_pass["prompt_tokens"],
                "completion_tokens": current_pass["completion_tokens"],
                "duration_ms": current_pass["duration_ms"],
            }

        # Build cumulative metrics for WebSocket
        cumulative_metrics = None
        if cumulative:
            cumulative_metrics = {
                "total_tokens": cumulative["total_tokens"],
                "total_prompt_tokens": cumulative["total_prompt_tokens"],
                "total_completion_tokens": cumulative["total_completion_tokens"],
                "total_duration_ms": cumulative["total_duration_ms"],
                "total_estimated_cost": cumulative["total_estimated_cost"],
            }

        # Get current progress
        result = AsyncResult(self.task_id)
        current_meta = result.info if isinstance(result.info, dict) else {}

        self.celery_task.update_state(
            state='PROGRESS',
            meta={
                'completed_turns': current_meta.get('completed_turns', 0),
                'total_turns': self.total_turns if hasattr(self, 'total_turns') else 0,
                'percentage': current_meta.get('percentage', 0),
                'phase': self.current_phase,
                'current_pass_metrics': current_pass_metrics,
                'cumulative_metrics': cumulative_metrics,
                'token_metrics': cumulative,  # Full metrics for storage
                'total_retries': self.total_retries,
            }
        )

    def _on_llm_retry(self, attempt: int, max_attempts: int, delay: float, error_type: str, error_message: str):
        """
        Callback invoked when LLM API call is being retried.
        Updates Celery task state with retry information for WebSocket clients.
        """
        self.total_retries += 1

        # Get current progress state
        result = AsyncResult(self.task_id)
        current_meta = result.info if isinstance(result.info, dict) else {}

        # Update state with retry info
        retry_meta = {
            **current_meta,
            'retry_info': {
                'attempt': attempt,
                'max_attempts': max_attempts,
                'delay_seconds': delay,
                'error_type': error_type,
                'error_message': error_message[:200],
            },
            'total_retries': self.total_retries,
            'event_type': 'retry',
        }

        self.celery_task.update_state(state='PROGRESS', meta=retry_meta)
        self.logger.info(f"Task {self.task_id}: LLM retry {attempt}/{max_attempts} ({error_type})")


    def run_single_pass(self, content: str) -> list:
        """
        Process entire content in a single LLM call without batching.

        This is used for single_pass processing mode where the content is expected
        to fit within the context window. The context validation should happen
        BEFORE reaching this method (in the API layer).

        Args:
            content (str): The full content to process.

        Returns:
            list: The processed output as a list of turns/lines.
        """
        self.logger.info(f"Running single pass for task {self.task_id}")

        # Set up progress tracking for single pass
        self.total_turns = 1
        self.celery_task.update_state(
            state='PROGRESS',
            meta={'completed_turns': 0, 'total_turns': 1, 'phase': 'processing'}
        )

        # Check for revocation before LLM call
        self.check_if_revoked()

        # Fill prompt with the full content (single placeholder)
        filled_prompt = self.prompt.format(content)
        input_chars = len(filled_prompt)

        # Track timing for metrics
        start_time = datetime.utcnow()

        # Make single LLM call with usage tracking
        try:
            result = self.openai_adapter.publish(filled_prompt, return_usage=True)
            if isinstance(result, tuple):
                response, usage = result
            else:
                response = result
                usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        except Exception as e:
            self.logger.error(f"Error in single pass: {e}")
            raise

        # Handle None response
        if response is None:
            self.logger.warning(f"Single pass returned None for task {self.task_id}")
            return []

        output_chars = len(response)

        # Record pass metrics (single pass = one "initial" pass)
        self._record_pass_metrics("single_pass", start_time, usage, input_chars, output_chars)

        # Update progress to complete
        self.celery_task.update_state(
            state='PROGRESS',
            meta={'completed_turns': 1, 'total_turns': 1, 'percentage': 100, 'phase': 'processing'}
        )

        self.logger.info(f"Single pass completed for task {self.task_id}: {output_chars} chars output")

        # Return response as a list of lines (consistent with batch methods)
        response_turns = [res for res in response.split('\n') if res.strip() != '']
        return response_turns

    def get_prompt(self, summarized_turns: list, new_turns_to_summarize: list, reduce_prompt=None) -> str:
        """
        Constructs the prompt by inserting summarized turns and new turns.

        Args:
            summarized_turns (list): The previously summarized turns.
            new_turns_to_summarize (list): The new turns to be summarized.

        Returns:
            str: The formatted prompt with turns inserted.
        """
        # Use the reduce prompt if provided
        if reduce_prompt is not None:
            return reduce_prompt.format('\n'.join(new_turns_to_summarize))
        # Format the prompt based on the number of fields (e.g., two fields or one)
        if self.promptFields == 2:
            return self.prompt.format('\n'.join(summarized_turns), '\n'.join(new_turns_to_summarize))
        return self.prompt.format('\n'.join(new_turns_to_summarize))


    def publish_turns(self, summarized_turns: list, new_turns_to_summarize: list, pass_type: str = "continuation") -> list:
        """
        Synchronously publishes a batch of turns by formatting the prompt, sending it to OpenAI, and processing the response.

        Args:
            summarized_turns (list): The previously summarized turns.
            new_turns_to_summarize (list): The new turns to be summarized.
            pass_type (str): Type of pass for metrics tracking.

        Returns:
            list: The updated list of summarized turns.
        """
        # Inject new turns into the prompt
        filled_prompt = self.get_prompt(summarized_turns, new_turns_to_summarize)
        input_chars = len(filled_prompt)

        # Track timing for metrics
        start_time = datetime.utcnow()

        # Publish the prompt with usage tracking
        try:
            result = self.openai_adapter.publish(filled_prompt, return_usage=True)
            if isinstance(result, tuple):
                response, usage = result
            else:
                response = result
                usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        except Exception as e:
            self.logger.error(f"Error publishing: {e}")
            raise

        # Handle None response
        if response is None:
            return self.progressive_summary + ['' for i in range(len(new_turns_to_summarize))]

        output_chars = len(response)

        # Record pass metrics
        self._record_pass_metrics(pass_type, start_time, usage, input_chars, output_chars)

        # Split the response into individual turns
        response_turns = [res for res in response.split('\n') if res.strip() != '']

        # Update the progressive summary
        self.progressive_summary.extend(response_turns)

        # Update the task progress
        self.update_task(len(new_turns_to_summarize))

        return self.progressive_summary[-self.summaryTurns:]

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
        total_token_count = self.prompt_token_count
        i = 0
        batch_number = 0

        # Calculate available space for content (excluding prompt and generation reserve)
        available_context = self.totalContextLength - self.maxGenerationLength
        # Maximum size for a single turn (must fit with prompt + buffer for summarized context)
        # We reserve ~20% of available space for summarized turns context
        max_single_turn_tokens = int((available_context - self.prompt_token_count) * 0.8)

        # Pre-process: split any turns that are too large to ever fit
        processed_turns = self._split_oversized_turns(turns, max_single_turn_tokens)

        self.total_turns = len(processed_turns)
        self.celery_task.update_state(state='PROGRESS', meta={'completed_turns': 0, 'total_turns': self.total_turns})

        # Process turn batches synchronously
        while i < len(processed_turns):
            # Check for task revocation before processing each batch
            self.check_if_revoked()

            turn = processed_turns[i]
            turn_token_count = len(self.tokenizer(turn)["input_ids"])

            # Safety check: if turn still can't fit after preprocessing, skip it
            if turn_token_count > available_context - self.prompt_token_count:
                self.logger.warning(
                    f"Skipping oversized turn {i}: {turn_token_count} tokens "
                    f"(max: {available_context - self.prompt_token_count}). "
                    f"Turn preview: {turn[:100]}..."
                )
                i += 1
                continue

            if (total_token_count + turn_token_count) > available_context or len(new_turns_to_summarize) == self.maxNewTurns:
                # Only process if we have turns to process (avoid empty batch loops)
                if new_turns_to_summarize:
                    # Determine pass type: first batch is "initial", rest are "continuation"
                    pass_type = "initial" if batch_number == 0 else "continuation"
                    batch_number += 1

                    # Process current batch of turns
                    summarized_turns = self.publish_turns(summarized_turns, new_turns_to_summarize, pass_type=pass_type)

                    # Check for revocation after each LLM call completes
                    self.check_if_revoked()

                    # Reset for next batch
                    new_turns_to_summarize = []
                    total_token_count = self.prompt_token_count + sum(len(self.tokenizer(t)["input_ids"]) for t in summarized_turns)
                else:
                    # Empty batch but turn still doesn't fit - this shouldn't happen after preprocessing
                    # but we handle it to prevent infinite loops
                    self.logger.error(
                        f"Turn {i} cannot fit even in empty batch: {turn_token_count} tokens. "
                        f"This indicates a configuration issue. Skipping turn."
                    )
                    i += 1
                    continue
            else:
                # Update current batch
                new_turns_to_summarize.append(turn)
                total_token_count += turn_token_count
                i += 1

        # Check before final batch
        self.check_if_revoked()

        # Process remaining turns if any
        if new_turns_to_summarize:
            pass_type = "initial" if batch_number == 0 else "continuation"
            summarized_turns = self.publish_turns(summarized_turns, new_turns_to_summarize, pass_type=pass_type)

        return self.progressive_summary

    def _split_oversized_turns(self, turns: list, max_tokens: int) -> list:
        """
        Pre-process turns to split any that exceed max_tokens.

        Uses sentence-based splitting to break down oversized turns while
        preserving speaker prefixes.

        Args:
            turns: List of turns to process
            max_tokens: Maximum allowed tokens per turn

        Returns:
            List of turns with oversized ones split into smaller chunks
        """
        from .chunking import Chunker

        processed = []
        for turn in turns:
            turn_tokens = len(self.tokenizer(turn)["input_ids"])

            if turn_tokens <= max_tokens:
                processed.append(turn)
                continue

            # Turn is oversized - try to split by sentences
            self.logger.warning(
                f"Turn has {turn_tokens} tokens (max: {max_tokens}). Attempting to split."
            )

            # Extract speaker prefix if present
            speaker_prefix = ""
            content = turn
            speaker_match = Chunker.get_speaker(turn)
            if speaker_match[1]:  # Has speaker prefix
                speaker_prefix = speaker_match[1]
                content = turn[len(speaker_prefix):].strip()

            # Split content by sentences
            sentences = Chunker.split_sentences(content)

            if not sentences:
                # No sentence boundaries found - force split by token count
                self.logger.warning("No sentence boundaries found. Force-splitting by character chunks.")
                sub_turns = self._force_split_turn(turn, speaker_prefix, content, max_tokens)
                processed.extend(sub_turns)
                continue

            # Rebuild turns from sentences, respecting token limit
            current_turn = speaker_prefix
            current_tokens = len(self.tokenizer(speaker_prefix)["input_ids"]) if speaker_prefix else 0

            for sentence in sentences:
                sentence_tokens = len(self.tokenizer(sentence)["input_ids"])

                if current_tokens + sentence_tokens > max_tokens:
                    # Save current turn if non-empty
                    if current_turn.strip() and current_turn != speaker_prefix:
                        processed.append(current_turn.strip())
                    # Start new turn
                    current_turn = speaker_prefix + sentence
                    current_tokens = len(self.tokenizer(current_turn)["input_ids"])
                else:
                    # Add to current turn
                    if current_turn and not current_turn.endswith(" "):
                        current_turn += " "
                    current_turn += sentence
                    current_tokens += sentence_tokens

            # Don't forget the last turn
            if current_turn.strip() and current_turn != speaker_prefix:
                processed.append(current_turn.strip())

        if len(processed) != len(turns):
            self.logger.info(f"Split {len(turns)} turns into {len(processed)} turns")

        return processed

    def _force_split_turn(self, turn: str, speaker_prefix: str, content: str, max_tokens: int) -> list:
        """
        Force-split a turn that has no sentence boundaries.

        Splits by approximate character count based on token ratio.

        Args:
            turn: Original turn
            speaker_prefix: Speaker prefix to prepend to each chunk
            content: Content without speaker prefix
            max_tokens: Maximum tokens per chunk

        Returns:
            List of split turns
        """
        result = []
        prefix_tokens = len(self.tokenizer(speaker_prefix)["input_ids"]) if speaker_prefix else 0
        available_tokens = max_tokens - prefix_tokens

        # Estimate chars per token (rough approximation)
        total_tokens = len(self.tokenizer(content)["input_ids"])
        chars_per_token = len(content) / total_tokens if total_tokens > 0 else 4
        chunk_size = int(available_tokens * chars_per_token * 0.9)  # 90% to be safe

        # Split content into chunks
        for start in range(0, len(content), chunk_size):
            chunk = content[start:start + chunk_size].strip()
            if chunk:
                result.append(f"{speaker_prefix}{chunk}" if speaker_prefix else chunk)

        self.logger.info(f"Force-split turn into {len(result)} chunks")
        return result

    def reduce_summary(self, summary: list) -> list:
        """
        Apply the reduce prompt to the summary in a single pass.

        Takes the condensed summary from iterative processing and applies the
        reduce_prompt to produce the final formatted output. If the summary
        is too large to fit in context, returns it as-is with a warning.

        Args:
            summary (list): The summary lines from iterative processing.

        Returns:
            list: The reduced/formatted summary as a list of lines.
        """
        self.logger.info(f"Reducing summary: {len(summary)} lines")
        self.current_phase = "reducing"

        # Check for task revocation
        self.check_if_revoked()

        # Calculate token count for summary
        summary_token_count = sum(
            len(self.tokenizer(line)["input_ids"]) for line in summary
        )
        total_token_count = self.prompt_token_count + summary_token_count
        available_context = self.totalContextLength - self.maxGenerationLength

        # Check if summary fits in context
        if total_token_count > available_context:
            self.logger.warning(
                f"Summary too large for reduce prompt ({total_token_count} tokens, "
                f"available: {available_context}). Returning summary without reduce formatting."
            )
            # Update task state with warning
            self.celery_task.update_state(
                state='PROGRESS',
                meta={
                    'completed_turns': self.total_turns if hasattr(self, 'total_turns') else 0,
                    'total_turns': self.total_turns if hasattr(self, 'total_turns') else 0,
                    'percentage': 100,
                    'phase': self.current_phase,
                    'warning': 'reduce_skipped_too_large',
                }
            )
            return summary

        # Update task state
        self.celery_task.update_state(
            state='PROGRESS',
            meta={
                'completed_turns': self.total_turns if hasattr(self, 'total_turns') else 0,
                'total_turns': self.total_turns if hasattr(self, 'total_turns') else 0,
                'percentage': 100,
                'phase': self.current_phase,
            }
        )

        # Apply reduce prompt in a single sync LLM call
        filled_prompt = self.reduce_prompt.format('\n'.join(summary))
        input_chars = len(filled_prompt)
        start_time = datetime.utcnow()

        try:
            result = self.openai_adapter.publish(filled_prompt, return_usage=True)
            if isinstance(result, tuple):
                response, usage = result
            else:
                response = result
                usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        except Exception as e:
            self.logger.error(f"Error in reduce: {e}")
            raise

        if response is None:
            self.logger.warning(f"Reduce returned None for task {self.task_id}")
            return summary

        output_chars = len(response)
        self._record_pass_metrics("reduce", start_time, usage, input_chars, output_chars)

        response_turns = [res for res in response.split('\n') if res.strip() != '']
        self.logger.info(f"Reduce complete: {len(response_turns)} lines output")
        return response_turns

    def get_final_metrics(self) -> Optional[Dict[str, Any]]:
        """Get the final cumulative metrics for this job."""
        return self._get_cumulative_metrics()

    def update_task(self, nb_turns):
        result = AsyncResult(self.task_id)
        completed_turns = result.info['completed_turns'] + nb_turns
        percentage = round(100 * completed_turns / self.total_turns) if self.total_turns > 0 else 0
        self.celery_task.update_state(
            state='PROGRESS',
            meta={
                'completed_turns': completed_turns,
                'total_turns': self.total_turns,
                'percentage': percentage,
                'phase': self.current_phase,
            }
        )
        self.logger.info(f"Task {self.task_id} progress updated : {percentage} % (phase: {self.current_phase})")

    
    @staticmethod
    def format_summary(summary: list) -> str:
        """Format the list of turns into a single string."""
        return "\n".join(summary)