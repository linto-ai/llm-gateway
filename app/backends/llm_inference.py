import json
import logging
import re
from .backend import LLMBackend
from .batch_manager import BatchManager

logger = logging.getLogger("llm_inference")


class LLMInferenceEngine(LLMBackend):
    def __init__(self, task_data: dict, celery_task):
        super().__init__(task_data)
        self.celery_task = celery_task
        self.batch_manager = BatchManager(task_data,self.tokenizer, self.prompt, self.prompt_token_count, self.reduce_prompt, celery_task)

        # Store extraction prompt if provided
        self.extraction_prompt_content = task_data.get("prompt_extraction_content")

        # Store extraction fields from templates (includes template placeholders)
        self.extraction_fields = task_data.get("extraction_fields")

        # Store categorization prompt and context if provided
        self.categorization_prompt_content = task_data.get("prompt_categorization_content")
        self.context = task_data.get("context")  # Contains tags, metadata for categorization

        # Store processing mode (default: iterative for long document processing)
        self.processing_mode = task_data.get("backendParams", {}).get("processing_mode", "iterative")

    def run(self) -> dict:
        """
        Runs the summarization pipeline on the input content, processing it through different stages to generate a final summary.

        Processing is determined by the `processing_mode` setting:
        - single_pass: Send entire content in ONE LLM call (no batching). Best for short documents.
        - iterative: Process in sequential batches with rolling context. Requires 2 placeholders ({}{}).

        After processing, additional operations are applied:
        - If `reduceSummary` is `True`, the summary is further reduced using the batch manager.
        - If `consolidateSummary` is `True`, the summary is consolidated into fewer turns using the chunker.

        Finally, the method formats and returns the processed summary with token metrics.

        Returns:
            dict: Contains 'output' (the final summary), 'token_metrics' (processing metrics),
                  and optionally 'extracted_metadata' (from extraction prompt).
        """
        logger.info(f"Processing mode: {self.processing_mode}, promptFields: {self.promptFields}")

        # SINGLE PASS: Send entire content in ONE LLM call
        if self.processing_mode == "single_pass":
            logger.info("Using single_pass mode - sending entire content in one LLM call")
            self.summary = self.batch_manager.run_single_pass(self.content)

        # ITERATIVE: Sequential batching with rolling context (requires 2 placeholders)
        else:
            # Chunk input content
            chunked_content = self.chunker.get_splits(self.content)
            self.summary = self.batch_manager.run_batches(chunked_content)

        # Reduce summary (optional consolidation step)
        if self.reduceSummary and self.processing_mode != "single_pass":
            self.summary = self.batch_manager.reduce_summary(self.summary)

        # consolidate turns for progressive summary
        if self.consolidateSummary:
            self.summary = self.chunker.consolidate_turns(self.summary)

        self.summary = self.batch_manager.format_summary(self.summary)

        # Run placeholder extraction if configured
        extracted_metadata = {}
        if self.extraction_prompt_content:
            extracted_metadata = self._run_extraction(self.summary)

        # Run categorization if configured (prompt + context with tags)
        categorization_result = {}
        if self.categorization_prompt_content and self.context:
            categorization_result = self._run_categorization(self.summary)

        # Return dict with output, token metrics, and extracted metadata
        return {
            'output': self.summary,
            'token_metrics': self.batch_manager.get_final_metrics(),
            'extracted_metadata': extracted_metadata,
            'categorization': categorization_result
        }

    def _run_extraction(self, output: str) -> dict:
        """
        Run placeholder extraction using the extraction prompt.

        Args:
            output: The main output to extract metadata from

        Returns:
            Dict of extracted metadata fields
        """
        try:
            # Check if output fits in context for extraction
            output_tokens = len(self.batch_manager.tokenizer(output)["input_ids"])
            extraction_prompt_tokens = len(self.batch_manager.tokenizer(self.extraction_prompt_content)["input_ids"])
            total_tokens = output_tokens + extraction_prompt_tokens
            available_context = self.batch_manager.totalContextLength - 2000  # Reserve 2000 for extraction response

            if total_tokens > available_context:
                logger.warning(
                    f"Output too large for extraction ({total_tokens} tokens, "
                    f"available: {available_context}). Skipping extraction."
                )
                return {"_extraction_warning": "skipped_too_large"}

            # Update phase to indicate extraction
            self.batch_manager.current_phase = "extracting"
            if self.celery_task:
                self.celery_task.update_state(
                    state='PROGRESS',
                    meta={
                        'phase': 'extracting',
                        'extraction_status': 'running'
                    }
                )

            logger.info(f"Starting placeholder extraction for task {self.task_id}")

            # Use extraction fields from templates if available, otherwise use defaults
            fields_to_extract = self.extraction_fields or [
                "title", "summary", "participants", "date", "topics",
                "action_items", "sentiment", "language", "key_points"
            ]
            logger.info(f"Extracting fields: {fields_to_extract}")

            # Build extraction prompt
            extraction_prompt = self.extraction_prompt_content

            # The prompt may contain literal JSON examples with braces, so we can't use .format()
            # Instead, find the TWO {} placeholders at the end and replace them manually
            # Pattern: "Document a analyser:\n{}\n\nPlaceholders a extraire:\n{}"

            # Count occurrences of standalone {} (not part of {{}} or named placeholders)
            # Replace the last two {} occurrences with our values
            placeholder_positions = []
            i = 0
            while i < len(extraction_prompt):
                if extraction_prompt[i:i+2] == "{}":
                    # Check it's not part of a named placeholder like {name}
                    placeholder_positions.append(i)
                    i += 2
                else:
                    i += 1

            if len(placeholder_positions) >= 2:
                # Replace from end to avoid position shifts
                # Replace the last {} with metadata_fields
                pos2 = placeholder_positions[-1]
                extraction_prompt = extraction_prompt[:pos2] + json.dumps(fields_to_extract) + extraction_prompt[pos2+2:]
                # Replace the second-to-last {} with output
                pos1 = placeholder_positions[-2]
                extraction_prompt = extraction_prompt[:pos1] + output + extraction_prompt[pos1+2:]
            else:
                # Fallback to {{placeholder}} style
                extraction_prompt = extraction_prompt.replace("{{output}}", output)
                extraction_prompt = extraction_prompt.replace("{{metadata_fields}}", json.dumps(fields_to_extract))

            # Call LLM for extraction using the batch manager's adapter (sync)
            from datetime import datetime
            start_time = datetime.utcnow()
            input_chars = len(extraction_prompt)

            response, usage = self.batch_manager.openai_adapter.publish(
                content=extraction_prompt,
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=2000,
                return_usage=True
            )

            output_chars = len(response) if response else 0

            # Record extraction pass metrics
            self.batch_manager._record_pass_metrics(
                "extraction", start_time, usage, input_chars, output_chars
            )

            logger.info(f"Extraction response length: {output_chars} chars")
            logger.debug(f"Extraction response preview: {response[:200] if response else 'EMPTY'}")

            # Handle empty response
            if not response or not response.strip():
                logger.warning(f"Empty extraction response for task {self.task_id}")
                return {"_extraction_error": "LLM returned empty response"}

            # Parse JSON response
            metadata = self._parse_json_response(response)
            logger.info(f"Extracted {len(metadata)} metadata fields for task {self.task_id}")

            return metadata

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction response as JSON: {e}")
            return {"_extraction_error": f"JSON parse error: {str(e)}"}
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return {"_extraction_error": str(e)}

    def _parse_json_response(self, response: str) -> dict:
        """
        Parse JSON from LLM response, handling markdown code blocks.

        Args:
            response: LLM response string

        Returns:
            Parsed JSON dict

        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        logger.debug(f"Raw response to parse: {response[:500] if response else 'EMPTY'}")
        text = response.strip()

        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            text = "\n".join(lines)

        # Also try to extract JSON from within the text if it's wrapped
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            text = json_match.group()
            logger.debug(f"Extracted JSON: {text[:200]}")
        else:
            logger.warning(f"No JSON object found in response: {text[:200]}")

        return json.loads(text)

    def _run_categorization(self, output: str) -> dict:
        """
        Run document categorization using the categorization prompt and context tags.

        The categorization prompt uses {context[input]} and {context[tags]} placeholders.

        Args:
            output: The main output (document) to categorize

        Returns:
            Dict with matched_tags, suggested_tags, and confidence scores
        """
        try:
            # Check if output fits in context for categorization
            output_tokens = len(self.batch_manager.tokenizer(output)["input_ids"])
            categorization_prompt_tokens = len(self.batch_manager.tokenizer(self.categorization_prompt_content)["input_ids"])
            total_tokens = output_tokens + categorization_prompt_tokens
            available_context = self.batch_manager.totalContextLength - 2000  # Reserve 2000 for categorization response

            if total_tokens > available_context:
                logger.warning(
                    f"Output too large for categorization ({total_tokens} tokens, "
                    f"available: {available_context}). Skipping categorization."
                )
                return {"_categorization_warning": "skipped_too_large"}

            # Update phase to indicate categorization
            self.batch_manager.current_phase = "categorizing"
            if self.celery_task:
                self.celery_task.update_state(
                    state='PROGRESS',
                    meta={
                        'phase': 'categorizing',
                        'categorization_status': 'running'
                    }
                )

            logger.info(f"Starting document categorization for task {self.task_id}")

            # Build categorization prompt by substituting context placeholders
            categorization_prompt = self.categorization_prompt_content

            # Get tags from context (expected format: list of {name, description} objects)
            tags = self.context.get("tags", [])
            if not tags:
                logger.warning("No tags provided in context for categorization")
                return {"_categorization_error": "No tags provided in context"}

            # Substitute placeholders: {context[input]} and {context[tags]}
            # The document to categorize (can be original content or processed output)
            input_text = self.context.get("input", output)

            # Replace {context[input]} with the input text
            if "{context[input]}" in categorization_prompt:
                categorization_prompt = categorization_prompt.replace("{context[input]}", input_text)
            elif "{{context[input]}}" in categorization_prompt:
                categorization_prompt = categorization_prompt.replace("{{context[input]}}", input_text)

            # Replace {context[tags]} with JSON-formatted tags
            tags_json = json.dumps(tags, ensure_ascii=False, indent=2)
            if "{context[tags]}" in categorization_prompt:
                categorization_prompt = categorization_prompt.replace("{context[tags]}", tags_json)
            elif "{{context[tags]}}" in categorization_prompt:
                categorization_prompt = categorization_prompt.replace("{{context[tags]}}", tags_json)

            logger.debug(f"Categorization prompt (first 500 chars): {categorization_prompt[:500]}")

            # Call LLM for categorization using the batch manager's adapter (sync)
            from datetime import datetime
            start_time = datetime.utcnow()
            input_chars = len(categorization_prompt)

            response, usage = self.batch_manager.openai_adapter.publish(
                content=categorization_prompt,
                temperature=0.1,  # Low temperature for consistent categorization
                max_tokens=2000,
                return_usage=True
            )

            output_chars = len(response) if response else 0

            # Record categorization pass metrics
            self.batch_manager._record_pass_metrics(
                "categorization", start_time, usage, input_chars, output_chars
            )

            logger.info(f"Categorization response length: {output_chars} chars")
            logger.debug(f"Categorization response preview: {response[:200] if response else 'EMPTY'}")

            # Handle empty response
            if not response or not response.strip():
                logger.warning(f"Empty categorization response for task {self.task_id}")
                return {"_categorization_error": "LLM returned empty response"}

            # Parse JSON response
            result = self._parse_json_response(response)
            logger.info(f"Categorization completed for task {self.task_id}: {len(result.get('matched_tags', []))} matched tags")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse categorization response as JSON: {e}")
            return {"_categorization_error": f"JSON parse error: {str(e)}"}
        except Exception as e:
            logger.error(f"Document categorization failed: {e}")
            return {"_categorization_error": str(e)}
