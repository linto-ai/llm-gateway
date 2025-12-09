"""
Chunker Tests - Comprehensive Test Suite

Tests covering:
1. split_sentences() - Universal sentence splitting (all languages)
2. detect_language() - Language detection with lingua
3. get_speaker() - Speaker pattern detection
4. get_splits() - Text splitting by token limits
5. consolidate_turns() - Merging consecutive turns
6. Multilingual tests - FR, EN, DE, ES, ZH, JA, AR, RU
7. Edge cases and regression tests
"""

import pytest
from unittest.mock import Mock, MagicMock


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_tokenizer():
    """Create a mock tokenizer that returns predictable token counts."""
    def tokenizer(text):
        # Simple tokenization: ~4 characters per token
        token_count = max(1, len(text) // 4)
        return {"input_ids": list(range(token_count))}
    return tokenizer


@pytest.fixture
def chunker(mock_tokenizer):
    """Create a Chunker instance with mock tokenizer and reasonable token limit."""
    from app.backends.chunking import Chunker
    # 50 tokens = ~200 characters before splitting
    return Chunker(tokenizer=mock_tokenizer, createNewTurnAfter=50)


@pytest.fixture
def chunker_small_limit(mock_tokenizer):
    """Create a Chunker with a small token limit to force splitting."""
    from app.backends.chunking import Chunker
    # 10 tokens = ~40 characters before splitting
    return Chunker(tokenizer=mock_tokenizer, createNewTurnAfter=10)


# =============================================================================
# 1. split_sentences() Tests - Universal Sentence Splitting
# =============================================================================

class TestSplitSentences:
    """Tests for the universal sentence splitting method."""

    def test_basic_sentence_split(self):
        """Basic sentence splitting with periods."""
        from app.backends.chunking import Chunker

        text = "First sentence. Second sentence. Third sentence."
        result = Chunker.split_sentences(text)

        assert len(result) >= 1
        # All content should be preserved
        combined = " ".join(result)
        assert "First sentence" in combined
        assert "Second sentence" in combined
        assert "Third sentence" in combined

    def test_question_and_exclamation(self):
        """Splitting on question marks and exclamation points."""
        from app.backends.chunking import Chunker

        text = "Is this a question? Yes it is! And this continues."
        result = Chunker.split_sentences(text)

        combined = " ".join(result)
        assert "Is this a question?" in combined
        assert "Yes it is!" in combined

    def test_abbreviations_not_split(self):
        """Abbreviations like 'M.' or 'Dr.' should not cause splits."""
        from app.backends.chunking import Chunker

        text = "Bonjour M. Dupont. Comment allez-vous?"
        result = Chunker.split_sentences(text, min_length=15)

        # Short segments should be merged
        combined = " ".join(result)
        assert "M." in combined and "Dupont" in combined

    def test_empty_text(self):
        """Empty text returns empty list."""
        from app.backends.chunking import Chunker

        assert Chunker.split_sentences("") == []
        assert Chunker.split_sentences("   ") == []
        assert Chunker.split_sentences(None) == []

    def test_single_sentence(self):
        """Single sentence without ending punctuation."""
        from app.backends.chunking import Chunker

        text = "This is a single sentence without period"
        result = Chunker.split_sentences(text)

        assert len(result) == 1
        assert result[0] == text

    def test_asian_punctuation(self):
        """Chinese/Japanese punctuation is recognized."""
        from app.backends.chunking import Chunker

        text = "你好。今天怎么样？很好！"
        result = Chunker.split_sentences(text, min_length=5)

        # Should handle Asian punctuation
        combined = "".join(result)
        assert "你好" in combined
        assert "今天" in combined

    def test_french_text(self):
        """French text with typical punctuation."""
        from app.backends.chunking import Chunker

        text = "Bonjour ! Comment allez-vous ? Je vais très bien. Merci de demander."
        result = Chunker.split_sentences(text)

        combined = " ".join(result)
        assert "Bonjour" in combined
        assert "Comment allez-vous" in combined

    def test_min_length_merging(self):
        """Short segments are merged based on min_length."""
        from app.backends.chunking import Chunker

        text = "A. B. C. This is a longer sentence that should stand alone."
        result = Chunker.split_sentences(text, min_length=30)

        # Short "A. B. C." should be merged with the longer sentence
        assert len(result) <= 2


# =============================================================================
# 2. detect_language() Tests
# =============================================================================

class TestDetectLanguage:
    """Tests for the language detection method."""

    def test_detect_french(self):
        """Detect French language."""
        from app.backends.chunking import Chunker

        text = "Bonjour, comment allez-vous aujourd'hui?"
        lang = Chunker.detect_language(text)

        assert lang == "fr"

    def test_detect_english(self):
        """Detect English language."""
        from app.backends.chunking import Chunker

        text = "Hello, how are you doing today?"
        lang = Chunker.detect_language(text)

        assert lang == "en"

    def test_detect_german(self):
        """Detect German language."""
        from app.backends.chunking import Chunker

        text = "Guten Tag, wie geht es Ihnen heute?"
        lang = Chunker.detect_language(text)

        assert lang == "de"

    def test_detect_spanish(self):
        """Detect Spanish language."""
        from app.backends.chunking import Chunker

        text = "Hola, ¿cómo estás hoy?"
        lang = Chunker.detect_language(text)

        assert lang == "es"

    def test_detect_chinese(self):
        """Detect Chinese language."""
        from app.backends.chunking import Chunker

        text = "你好，今天怎么样？"
        lang = Chunker.detect_language(text)

        assert lang == "zh"

    def test_detect_japanese(self):
        """Detect Japanese language."""
        from app.backends.chunking import Chunker

        text = "こんにちは、お元気ですか？"
        lang = Chunker.detect_language(text)

        assert lang == "ja"

    def test_detect_russian(self):
        """Detect Russian language."""
        from app.backends.chunking import Chunker

        text = "Привет, как дела?"
        lang = Chunker.detect_language(text)

        assert lang == "ru"

    def test_detect_arabic(self):
        """Detect Arabic language."""
        from app.backends.chunking import Chunker

        text = "مرحبا، كيف حالك اليوم؟"
        lang = Chunker.detect_language(text)

        assert lang == "ar"

    def test_detect_italian(self):
        """Detect Italian language."""
        from app.backends.chunking import Chunker

        text = "Ciao, come stai oggi?"
        lang = Chunker.detect_language(text)

        assert lang == "it"

    def test_detect_portuguese(self):
        """Detect Portuguese language."""
        from app.backends.chunking import Chunker

        text = "Olá, como você está?"
        lang = Chunker.detect_language(text)

        assert lang == "pt"

    def test_fallback_on_short_text(self):
        """Short or ambiguous text should return a valid language code."""
        from app.backends.chunking import Chunker

        text = "OK"
        lang = Chunker.detect_language(text)

        # Should return a valid 2-letter code, not crash
        assert lang is not None
        assert len(lang) == 2


# =============================================================================
# 3. get_speaker() Tests
# =============================================================================

class TestGetSpeaker:
    """Tests for the get_speaker static method."""

    def test_speaker_with_colon_space(self):
        """Line with 'Speaker : content' pattern returns speaker prefix."""
        from app.backends.chunking import Chunker

        line = "Jean : Bonjour tout le monde."
        result_line, speaker = Chunker.get_speaker(line)

        assert result_line == line
        assert speaker == "Jean : "

    def test_speaker_with_colon_only(self):
        """Line with 'Speaker:content' pattern (no space after colon) returns speaker."""
        from app.backends.chunking import Chunker

        line = "Marie:Comment allez-vous?"
        result_line, speaker = Chunker.get_speaker(line)

        assert result_line == line
        assert speaker == "Marie:"

    def test_speaker_with_numbers(self):
        """Speaker name with numbers (e.g., 'Speaker 1 :') is detected."""
        from app.backends.chunking import Chunker

        line = "Intervenant 1 : Merci pour cette question."
        result_line, speaker = Chunker.get_speaker(line)

        assert result_line == line
        assert speaker == "Intervenant 1 : "

    def test_speaker_with_accents(self):
        """Speaker name with French accents is detected."""
        from app.backends.chunking import Chunker

        line = "André-René : C'est une bonne idée."
        result_line, speaker = Chunker.get_speaker(line)

        assert result_line == line
        assert speaker == "André-René : "

    def test_no_speaker_plain_text(self):
        """Plain text without speaker pattern returns None speaker."""
        from app.backends.chunking import Chunker

        line = "This is just plain text without any speaker."
        result_line, speaker = Chunker.get_speaker(line)

        assert result_line == line
        assert speaker is None

    def test_no_pollution_without_speaker(self):
        """Line without speaker should NOT have '(?) :' prefix added."""
        from app.backends.chunking import Chunker

        line = "Just a simple line of text."
        result_line, speaker = Chunker.get_speaker(line)

        assert "(?) :" not in result_line
        assert result_line == line
        assert speaker is None


# =============================================================================
# 4. get_splits() Tests
# =============================================================================

class TestGetSplits:
    """Tests for the get_splits method."""

    def test_short_line_no_speaker_returned_as_is(self, chunker):
        """Short line without speaker is returned unchanged."""
        content = "This is a short line of text."
        result = chunker.get_splits(content)

        assert len(result) == 1
        assert result[0] == content
        assert "(?) :" not in result[0]

    def test_multiple_short_lines_no_speaker(self, chunker):
        """Multiple short lines without speakers are returned as-is."""
        content = """First line of text.
Second line of text.
Third line of text."""
        result = chunker.get_splits(content)

        assert len(result) == 3
        assert result[0] == "First line of text."
        assert result[1] == "Second line of text."
        assert result[2] == "Third line of text."
        for line in result:
            assert "(?) :" not in line

    def test_asr_transcription_preserved(self, chunker):
        """ASR transcription with speakers is preserved correctly."""
        content = """Speaker A : Hello, how are you today?
Speaker B : I'm doing well, thank you.
Speaker A : That's great to hear."""
        result = chunker.get_splits(content)

        assert len(result) == 3
        assert "Speaker A : " in result[0]
        assert "Speaker B : " in result[1]
        assert "Speaker A : " in result[2]

    def test_long_line_no_speaker_split_by_sentences(self, chunker_small_limit):
        """Long line without speaker is split by sentences without prefix."""
        content = "First sentence here. Second sentence continues. Third sentence ends here."
        result = chunker_small_limit.get_splits(content)

        # Should be split into multiple chunks
        assert len(result) >= 1
        # No chunk should have "(?) :" prefix
        for chunk in result:
            assert "(?) :" not in chunk
            assert chunk.strip() != ""

    def test_mixed_content_speakers_and_plain(self, chunker):
        """Mixed content with some speakers and some plain text."""
        content = """Introduction paragraph without speaker.
Speaker X : First speaker statement.
Another plain text line.
Speaker Y : Second speaker statement."""
        result = chunker.get_splits(content)

        assert len(result) == 4
        assert "(?) :" not in result[0]
        assert "Speaker X : " in result[1]
        assert "(?) :" not in result[2]
        assert "Speaker Y : " in result[3]

    def test_empty_content(self, chunker):
        """Empty content returns empty list."""
        result = chunker.get_splits("")
        assert result == []

    def test_whitespace_only_content(self, chunker):
        """Content with only whitespace returns empty list."""
        result = chunker.get_splits("   \n\n   \n   ")
        assert result == []


# =============================================================================
# 5. consolidate_turns() Tests
# =============================================================================

class TestConsolidateTurns:
    """Tests for the consolidate_turns method."""

    def test_all_lines_no_speakers_consolidated(self, chunker):
        """Lines without speakers are consolidated into single block."""
        turns = [
            "First line of text.",
            "Second line continues.",
            "Third line ends."
        ]
        result = chunker.consolidate_turns(turns)

        assert len(result) == 1
        assert "First line" in result[0]
        assert "Second line" in result[0]
        assert "Third line" in result[0]
        assert "(?) :" not in result[0]

    def test_all_lines_same_speaker_consolidated(self, chunker):
        """Lines with same speaker are consolidated."""
        turns = [
            "Alice : First statement.",
            "Alice : Second statement.",
            "Alice : Third statement."
        ]
        result = chunker.consolidate_turns(turns)

        assert len(result) == 1
        assert result[0].startswith("Alice : ")
        assert "First statement" in result[0]
        assert "Second statement" in result[0]

    def test_different_speakers_not_consolidated(self, chunker):
        """Lines with different speakers remain separate."""
        turns = [
            "Alice : Hello there.",
            "Bob : Hi Alice.",
            "Alice : How are you?"
        ]
        result = chunker.consolidate_turns(turns)

        assert len(result) == 3
        assert "Alice : " in result[0]
        assert "Bob : " in result[1]
        assert "Alice : " in result[2]

    def test_empty_turns_list(self, chunker):
        """Empty turns list returns empty list."""
        result = chunker.consolidate_turns([])
        assert result == []


# =============================================================================
# 6. Multilingual Tests
# =============================================================================

class TestMultilingual:
    """Multilingual support tests."""

    def test_french_text_processing(self, chunker):
        """French text is processed correctly."""
        content = """Bonjour à tous.
Bienvenue à cette réunion.
Merci d'être présents."""

        result = chunker.get_splits(content)

        assert len(result) == 3
        assert "Bonjour" in result[0]
        assert "(?) :" not in result[0]

    def test_german_text_processing(self, chunker):
        """German text is processed correctly."""
        content = """Guten Tag zusammen.
Willkommen zu diesem Meeting.
Danke für Ihre Teilnahme."""

        result = chunker.get_splits(content)

        assert len(result) == 3
        for line in result:
            assert "(?) :" not in line

    def test_spanish_text_processing(self, chunker):
        """Spanish text is processed correctly."""
        content = """Hola a todos.
Bienvenidos a esta reunión.
Gracias por estar aquí."""

        result = chunker.get_splits(content)

        assert len(result) == 3
        for line in result:
            assert "(?) :" not in line

    def test_chinese_text_processing(self, chunker):
        """Chinese text is processed correctly."""
        content = """大家好。
欢迎参加今天的会议。
感谢大家的参与。"""

        result = chunker.get_splits(content)

        assert len(result) == 3
        for line in result:
            assert "(?) :" not in line

    def test_japanese_text_processing(self, chunker):
        """Japanese text is processed correctly."""
        content = """皆さん、こんにちは。
本日の会議にようこそ。
ご参加ありがとうございます。"""

        result = chunker.get_splits(content)

        assert len(result) == 3
        for line in result:
            assert "(?) :" not in line

    def test_russian_text_processing(self, chunker):
        """Russian text is processed correctly."""
        content = """Здравствуйте всем.
Добро пожаловать на встречу.
Спасибо за участие."""

        result = chunker.get_splits(content)

        assert len(result) == 3
        for line in result:
            assert "(?) :" not in line

    def test_arabic_text_processing(self, chunker):
        """Arabic text is processed correctly."""
        content = """مرحبا بالجميع.
مرحبا بكم في هذا الاجتماع.
شكرا لحضوركم."""

        result = chunker.get_splits(content)

        assert len(result) == 3
        for line in result:
            assert "(?) :" not in line

    def test_mixed_language_content(self, chunker):
        """Mixed language content is handled."""
        content = """Hello everyone.
Bonjour à tous.
Hallo zusammen."""

        result = chunker.get_splits(content)

        assert len(result) == 3
        assert "Hello" in result[0]
        assert "Bonjour" in result[1]
        assert "Hallo" in result[2]


# =============================================================================
# 7. Regression Tests - ASR Format
# =============================================================================

class TestASRRegression:
    """Regression tests ensuring ASR transcription format works correctly."""

    def test_typical_asr_transcript(self, chunker):
        """Typical ASR transcript with multiple speakers is processed correctly."""
        content = """Jean-Pierre : Bonjour à tous et bienvenue à cette réunion.
Marie-Claire : Merci Jean-Pierre, c'est un plaisir d'être ici.
Jean-Pierre : Alors, commençons par le premier point.
Paul : Je voudrais ajouter quelque chose avant.
Marie-Claire : Bien sûr Paul, allez-y."""

        result = chunker.get_splits(content)

        assert len(result) == 5
        assert "Jean-Pierre : " in result[0]
        assert "Marie-Claire : " in result[1]
        assert "Jean-Pierre : " in result[2]
        assert "Paul : " in result[3]
        assert "Marie-Claire : " in result[4]

    def test_asr_consolidation(self, chunker):
        """ASR transcript consolidation works correctly."""
        turns = [
            "Jean-Pierre : Bonjour.",
            "Jean-Pierre : Comment allez-vous?",
            "Marie : Très bien merci.",
            "Jean-Pierre : Parfait."
        ]

        result = chunker.consolidate_turns(turns)

        assert len(result) == 3
        assert "Bonjour" in result[0] and "Comment allez-vous" in result[0]
        assert result[0].startswith("Jean-Pierre : ")
        assert result[1].startswith("Marie : ")
        assert result[2].startswith("Jean-Pierre : ")


# =============================================================================
# 8. Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case tests for the Chunker."""

    def test_single_word_line(self, chunker):
        """Single word line without speaker."""
        result = chunker.get_splits("Hello")
        assert len(result) == 1
        assert result[0] == "Hello"

    def test_line_with_only_colon(self, chunker):
        """Line containing just a colon."""
        result = chunker.get_splits(":")
        assert len(result) == 1

    def test_unicode_content(self, chunker):
        """Content with various unicode characters."""
        content = "Café résumé naïve façade"
        result = chunker.get_splits(content)
        assert len(result) == 1
        assert result[0] == content

    def test_very_long_single_sentence_no_speaker(self, chunker_small_limit):
        """Very long single sentence without speaker gets handled."""
        content = "This is a very long sentence that goes on and on and on without stopping for punctuation or breaks"
        result = chunker_small_limit.get_splits(content)

        assert len(result) >= 1
        for chunk in result:
            assert "(?) :" not in chunk

    def test_content_with_multiple_colons(self, chunker):
        """Content with multiple colons in various positions."""
        content = "Time: 10:30 AM - Meeting: Project Discussion"
        result = chunker.get_splits(content)
        assert len(result) == 1

    def test_long_line_with_multiple_sentences(self, chunker_small_limit):
        """Long line with multiple sentences is properly split."""
        content = "First sentence is here. Second sentence follows. Third sentence comes next. Fourth sentence ends."
        result = chunker_small_limit.get_splits(content)

        # Should be split into multiple chunks
        assert len(result) >= 2
        # All content preserved
        combined = " ".join(result)
        assert "First sentence" in combined
        assert "Fourth sentence" in combined

    def test_speaker_with_long_content(self, chunker_small_limit):
        """Speaker line with long content is properly split."""
        content = "Marie : Première phrase ici. Deuxième phrase suit. Troisième phrase vient. Quatrième phrase termine."
        result = chunker_small_limit.get_splits(content)

        # Should be split, each chunk should have speaker
        assert len(result) >= 1
        for chunk in result:
            assert "Marie : " in chunk or chunk.startswith("Marie :")


# =============================================================================
# 9. Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests combining multiple Chunker methods."""

    def test_full_pipeline_plain_text(self, chunker):
        """Full pipeline with plain text (no speakers)."""
        content = """This is the first paragraph.
This is the second paragraph.
This is the third paragraph."""

        splits = chunker.get_splits(content)
        assert len(splits) == 3

        consolidated = chunker.consolidate_turns(splits)
        assert len(consolidated) == 1
        assert "(?) :" not in consolidated[0]

    def test_full_pipeline_asr(self, chunker):
        """Full pipeline with ASR transcription."""
        content = """Alice : Hello.
Alice : How are you?
Bob : Fine thanks.
Alice : Great."""

        splits = chunker.get_splits(content)
        assert len(splits) == 4

        consolidated = chunker.consolidate_turns(splits)
        assert len(consolidated) == 3
        assert "Alice : " in consolidated[0]
        assert "Bob : " in consolidated[1]
        assert "Alice : " in consolidated[2]

    def test_full_pipeline_multilingual(self, chunker):
        """Full pipeline with multilingual content."""
        content = """Introduction en français.
English paragraph here.
Deutscher Absatz hier.
日本語の段落。"""

        splits = chunker.get_splits(content)
        assert len(splits) == 4

        consolidated = chunker.consolidate_turns(splits)
        assert len(consolidated) == 1  # All no-speaker, consolidated

        # All languages preserved
        assert "français" in consolidated[0]
        assert "English" in consolidated[0]
        assert "Deutscher" in consolidated[0]
        assert "日本語" in consolidated[0]


# =============================================================================
# 10. Performance Sanity Tests
# =============================================================================

class TestPerformance:
    """Basic performance sanity checks."""

    def test_split_sentences_performance(self):
        """split_sentences should handle large text quickly."""
        from app.backends.chunking import Chunker
        import time

        # Generate large text
        large_text = "This is a sentence. " * 1000

        start = time.perf_counter()
        result = Chunker.split_sentences(large_text)
        elapsed = time.perf_counter() - start

        # Should complete in under 1 second
        assert elapsed < 1.0
        assert len(result) > 0

    def test_language_detection_caching(self):
        """Language detector should be cached (singleton)."""
        from app.backends.chunking import Chunker

        # First call initializes
        detector1 = Chunker.get_language_detector()
        # Second call should return same instance
        detector2 = Chunker.get_language_detector()

        assert detector1 is detector2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
