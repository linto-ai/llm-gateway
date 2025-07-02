from typing import List, Optional, Tuple
import logging
import re
import spacy
nlp = spacy.load("fr_core_news_sm")

class Chunker:
    def __init__(self, tokenizer, createNewTurnAfter: int):
        self.tokenizer = tokenizer
        self.createNewTurnAfter = createNewTurnAfter
        self.logger = logging.getLogger("Chunker")
        
    @staticmethod
    def get_speaker(line: str, speaker: Optional[str] = None )  -> Tuple[str, str]:
        pattern = r"^[A-Za-z0-9\s\-éèêëàâäôöùûüçïîÿæœñ]+ ?: ?"
        match = re.match(pattern, line)
        if match:
            return line, match.group(0)
        else:
            if speaker:
                line = speaker + line
            else:
                line = "(?) : " + line
            return line, speaker

    def get_splits(self, content: str) -> List[str]:
        """
        Splits the input content into turns based on token limits and sentence segmentation.
        Creates a new turn if token count exceeds createNewTurnAfter

        :param content: The text content to be split into chunks
        :return: A list of strings representing the split turns
        """
        lines = [ line for line in content.splitlines() if line.strip() != ""]
        speaker = "(?)"
        newTurns = []
        tokenCount = 0  # Initialize token counter
        
        for line in lines:
            tokenCount = 0
            # Get speaker name
            line, speaker = self.get_speaker(line, speaker)
            tokens = self.tokenizer(line)["input_ids"]
            tokenCount = len(tokens)

            if tokenCount > self.createNewTurnAfter:
                doc = nlp(line[len(speaker):].strip())  # Process the remaining line with spaCy (without speaker)
                # initialize new turn and token count
                currentTurn = speaker
                speaker_tokens = self.tokenizer(currentTurn)["input_ids"]
                tokenCount = len(speaker_tokens)
                # Segment the line into sentences using spaCy
                for i,sentence in enumerate(doc.sents):
                    sentence_text = sentence.text.strip()
                    if sentence_text.strip() == "":
                        continue
                    # Tokenize the sentence to count tokens                   
                    tokens = self.tokenizer(sentence_text)["input_ids"]

                    if tokenCount + len(tokens) > self.createNewTurnAfter:
                        # If token count exceeds the limit, add the sentence and reset token count
                        newTurns.append(currentTurn)
                        currentTurn = speaker + sentence_text
                        tokenCount = len(speaker_tokens)  # Reset token count after adding a new turn
                    else:
                        currentTurn += sentence_text
                        tokenCount += len(tokens)
                # Add the last turn
                newTurns.append(currentTurn)
            else:
                newTurns.append(line)
        
        return newTurns
    
    
    def consolidate_turns(self, turns: List[str]) -> List[str]:
        """
        Consolidates multiple turns by the same speaker into a single turn.
        
        :param turns: List of turns to be consolidated
        :return: A list of consolidated turns
        """
        self.logger.info("Consolidating turns process started.")
        if not turns:
            return []
        consolidated_turns = []
        current_speaker = None
        current_turn = []
        speaker = "(?)"

        for turn in turns:
            content, speaker = self.get_speaker(turn, speaker)
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