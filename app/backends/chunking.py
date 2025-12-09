from typing import List, Optional, Tuple
import logging
import re


class Chunker:
    """
    Splits and consolidates text content into manageable chunks for LLM processing.

    Supports:
    - ASR transcription format (Speaker : text)
    - Generic text (emails, documents, articles)
    - All languages via universal sentence splitting
    """

    # Lazy-loaded language detector
    _detector = None

    def __init__(self, tokenizer, createNewTurnAfter: int):
        self.tokenizer = tokenizer
        self.createNewTurnAfter = createNewTurnAfter
        self.logger = logging.getLogger("Chunker")

    @classmethod
    def get_language_detector(cls):
        """Lazy-load the language detector (heavy initialization)."""
        if cls._detector is None:
            from lingua import LanguageDetectorBuilder
            cls._detector = LanguageDetectorBuilder.from_all_languages().build()
        return cls._detector

    @staticmethod
    def detect_language(text: str) -> str:
        """
        Detect the language of the given text.

        Returns ISO 639-1 code (e.g., 'fr', 'en', 'de') or 'en' as fallback.
        """
        detector = Chunker.get_language_detector()
        lang = detector.detect_language_of(text)
        if lang:
            return lang.iso_code_639_1.name.lower()
        return "en"

    @staticmethod
    def split_sentences(text: str, min_length: int = 20) -> List[str]:
        """
        Universal sentence splitting using punctuation patterns.

        Works for all languages using standard punctuation (. ! ? and Asian variants).
        Merges short segments to avoid splitting on abbreviations.

        Args:
            text: The text to split into sentences
            min_length: Minimum character length for a sentence (to handle abbreviations)

        Returns:
            List of sentences
        """
        if not text or not text.strip():
            return []

        # Split on sentence-ending punctuation (Western + Asian)
        # Handles: . ! ? 。 ！ ？ followed by whitespace or end
        pattern = r'(?<=[.!?。！？])\s+'
        parts = re.split(pattern, text.strip())

        # Merge short segments (likely abbreviations like "M." or "Dr.")
        result = []
        buffer = ""
        for part in parts:
            part = part.strip()
            if not part:
                continue
            buffer += (" " if buffer else "") + part
            if len(buffer) >= min_length:
                result.append(buffer)
                buffer = ""

        # Handle remaining buffer
        if buffer:
            if result:
                result[-1] += " " + buffer
            else:
                result.append(buffer)

        return result

    @staticmethod
    def get_speaker(line: str, speaker: Optional[str] = None) -> Tuple[str, Optional[str]]:
        """
        Extract speaker from a line of text.

        Returns (line, speaker) where speaker can be None if no pattern matches.
        If a speaker pattern is found, returns (original_line, speaker_prefix).
        If no speaker pattern matches, returns (original_line, None).
        """
        pattern = r"^[A-Za-z0-9\s\-éèêëàâäôöùûüçïîÿæœñ]+ ?: ?"
        match = re.match(pattern, line)
        if match:
            return line, match.group(0)
        else:
            # No speaker detected: return line as-is with None speaker
            return line, None

    def get_splits(self, content: str) -> List[str]:
        """
        Splits the input content into turns based on token limits and sentence segmentation.
        Creates a new turn if token count exceeds createNewTurnAfter.

        Handles both ASR transcription (with speaker prefixes) and generic text (no speakers).
        When no speaker is detected, lines are returned as-is or split by sentences without prefix.

        :param content: The text content to be split into chunks
        :return: A list of strings representing the split turns
        """
        lines = [line for line in content.splitlines() if line.strip() != ""]
        speaker = None  # Start with no speaker assumption
        newTurns = []

        for line in lines:
            # Get speaker name (may be None for generic text)
            line, speaker = self.get_speaker(line, speaker)
            tokens = self.tokenizer(line)["input_ids"]
            tokenCount = len(tokens)

            if tokenCount > self.createNewTurnAfter:
                # Calculate content offset based on whether speaker exists
                if speaker:
                    content_start = len(speaker)
                else:
                    content_start = 0

                # Split into sentences using universal regex-based approach
                sentences = self.split_sentences(line[content_start:].strip())

                # Initialize new turn and token count
                if speaker:
                    currentTurn = speaker
                    speaker_tokens = self.tokenizer(currentTurn)["input_ids"]
                    speaker_token_count = len(speaker_tokens)
                else:
                    currentTurn = ""
                    speaker_tokens = []
                    speaker_token_count = 0
                tokenCount = speaker_token_count

                # Process each sentence
                for sentence_text in sentences:
                    if not sentence_text:
                        continue
                    # Tokenize the sentence to count tokens
                    tokens = self.tokenizer(sentence_text)["input_ids"]

                    if tokenCount + len(tokens) > self.createNewTurnAfter:
                        # If token count exceeds the limit, save current turn and start new one
                        if currentTurn.strip():  # Only append non-empty turns
                            newTurns.append(currentTurn.strip())
                        if speaker:
                            currentTurn = speaker + sentence_text
                        else:
                            currentTurn = sentence_text
                        tokenCount = speaker_token_count + len(tokens)
                    else:
                        # Add space between sentences if needed
                        if currentTurn and not currentTurn.endswith(" "):
                            currentTurn += " "
                        currentTurn += sentence_text
                        tokenCount += len(tokens)

                # Add the last turn
                if currentTurn.strip():
                    newTurns.append(currentTurn.strip())
            else:
                newTurns.append(line)

        return newTurns


    def consolidate_turns(self, turns: List[str]) -> List[str]:
        """
        Consolidates multiple turns by the same speaker into a single turn.

        Handles both ASR transcription (with speaker prefixes) and generic text (no speakers).
        - Lines with speakers are consolidated by speaker (consecutive same-speaker lines merged).
        - Lines without speakers are consolidated together as a single block.

        :param turns: List of turns to be consolidated
        :return: A list of consolidated turns
        """
        self.logger.info("Consolidating turns process started.")
        if not turns:
            return []
        consolidated_turns = []
        current_speaker = None
        current_turn = []
        speaker = None  # Start with no speaker assumption

        for turn in turns:
            content, speaker = self.get_speaker(turn, speaker)
            # Remove speaker prefix from content if speaker exists
            if speaker:
                content = content[len(speaker):].strip()
            else:
                content = content.strip()

            if speaker == current_speaker:
                current_turn.append(content)
            else:
                if current_turn:
                    # Format output based on whether speaker exists
                    if current_speaker:
                        consolidated_turns.append(f"{current_speaker}{' '.join(current_turn)}")
                    else:
                        consolidated_turns.append(' '.join(current_turn))
                current_speaker = speaker
                current_turn = [content]

        if current_turn:
            # Format final output based on whether speaker exists
            if current_speaker:
                consolidated_turns.append(f"{current_speaker}{' '.join(current_turn)}")
            else:
                consolidated_turns.append(' '.join(current_turn))

        return consolidated_turns
