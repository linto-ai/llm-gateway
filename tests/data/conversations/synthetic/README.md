# Synthetic Conversation Test Data

## Overview

**Location:** `tests/data/conversations/synthetic/`

This directory contains synthetic conversation datasets in **plain text format** designed for testing diarization correction and speaker detection algorithms. The conversations explore the philosophical question "Why is there something instead of nothing?" through dialogue between five speakers representing different intellectual traditions.

**Purpose:** Enable comprehensive testing of:
- Diarization error detection and correction
- Speaker label mismatch identification
- Multi-speaker conversation processing
- Cross-language conversation analysis

**Generated:** 2025-11-24
**Format:** Plain text (.txt) files
**Method:** LLM-generated synthetic conversations

---

## File Structure

### Naming Convention

Files follow the pattern: `{language}_{error_variant}.txt`

- **Language:** `en` (English), `fr` (French), `mixed` (EN/FR code-switching)
- **Error Variant:** `perfect` (no errors), `diarization_errors` (sentence-splitting only), `full_errors` (both error types)

### Complete File List

| # | Filename | Language | Error Type | Description |
|---|----------|----------|------------|-------------|
| 1 | `en_perfect.txt` | English | None | Ground truth baseline |
| 2 | `en_diarization_errors.txt` | English | Diarization | Sentence splits across speakers |
| 3 | `en_full_errors.txt` | English | Both | Diarization + speaker label errors |
| 4 | `fr_perfect.txt` | French | None | Ground truth baseline |
| 5 | `fr_diarization_errors.txt` | French | Diarization | Sentence splits across speakers |
| 6 | `fr_full_errors.txt` | French | Both | Diarization + speaker label errors |
| 7 | `mixed_perfect.txt` | Mixed EN/FR | None | Ground truth baseline |
| 8 | `mixed_diarization_errors.txt` | Mixed EN/FR | Diarization | Sentence splits across speakers |
| 9 | `mixed_full_errors.txt` | Mixed EN/FR | Both | Diarization + speaker label errors |

---

## Plain Text Format Specification

### File Format Rules

**Encoding:** UTF-8 (required for French accents)

**Line Format:**
```
SpeakerName : dialogue text
```

- Each line is ONE speaker turn
- Format: Speaker name, space, colon, space, then dialogue text
- No line breaks within dialogue text
- **NO language prefixes** like "En français :" or "In English :"
- Natural conversation flow

### Format Examples

**English (en_perfect.txt):**
```
John : Good morning everyone. Today I'd like to explore perhaps the most fundamental question in philosophy: why is there something rather than nothing?
Marie : As a physicist, I find this question fascinating but also deeply frustrating. We can describe what exists, but the 'why' seems beyond empirical investigation.
Ahmed : From a theological perspective, the answer has always been clear. There is something because God willed it into existence.
Sofia : But that just pushes the question back one step. Why does God exist rather than not exist?
Chen : In Buddhist philosophy, we approach this differently. The question itself may rest on false assumptions about existence and non-existence.
```

**French (fr_perfect.txt):**
```
John : Permettez-moi d'ouvrir avec la fameuse formulation de Leibniz : Pourquoi y a-t-il quelque chose plutôt que rien ?
Marie : D'un point de vue scientifique, nous devons d'abord définir ce que nous entendons par 'rien'.
Ahmed : La tradition islamique postule que Dieu est l'être nécessaire dont l'existence ne requiert aucune explication.
Sofia : Quand nous observons le rayonnement cosmique de fond, nous voyons des preuves du Big Bang.
Chen : Dans la philosophie bouddhiste, nous parlons de vacuité, ou Śūnyatā.
```

**Mixed (mixed_perfect.txt):**
```
John : Permettez-moi d'ouvrir avec la fameuse formulation de Leibniz.
Marie : From a scientific perspective, we need to first define what we mean by 'nothing'.
Ahmed : The Islamic tradition, like many religious philosophies, posits that God is the necessary being.
Sofia : Quand nous observons le rayonnement cosmique de fond, nous voyons des preuves du Big Bang.
Chen : In Buddhist philosophy, we speak of emptiness, or Śūnyatā.
```
---

## Error Type Definitions

### 1. Perfect (No Errors)

**Characteristics:**
- No diarization errors
- No speaker label errors
- Each line is a complete speaker turn
- Natural conversation flow
- Serves as ground truth

**Example:**
```
John : I believe that quantum mechanics provides a compelling answer to this question.
Marie : But quantum mechanics only describes how things behave, not why they exist at all.
Ahmed : Perhaps both science and theology offer complementary perspectives on existence.
```

**Use Case:** Baseline for measuring correction algorithm accuracy

### 2. Diarization Errors Only

**What is a Diarization Error?**

A diarization error occurs when a single speaker's sentence is incorrectly split across multiple lines, with part of the sentence attributed to a different speaker.

**Example:**

```
Correct (from perfect file):
John : I believe that quantum mechanics provides a compelling answer to this question.

Diarization error (sentence split):
John : I believe that quantum mechanics provides a compelling
Ahmed : answer to this question.
```

**Error Pattern Examples:**
```
Speaker1 : The cosmological argument suggests that everything must have a
Speaker3 : cause, therefore the universe must have a first cause.

Speaker2 : From the perspective of quantum field theory, virtual particles can emerge
Speaker4 : from the vacuum without any apparent cause.

John : La question fondamentale n'est pas simplement de savoir
Marie : pourquoi il y a quelque chose, mais pourquoi il y a cet univers particulier.
```

**Characteristics:**
- 15-20 diarization errors per conversation
- Sentences split at unnatural boundaries (mid-phrase, before complements)
- Second part incorrectly assigned to different speaker
- Second part typically starts with lowercase (continues sentence)

**Detection Strategy:** Look for incomplete sentences, grammatical breaks, semantic continuity across lines

### 3. Full Errors (Diarization + Speaker Label)

**What is a Speaker Label Error?**

A speaker label error occurs when an entire turn is attributed to the wrong speaker, creating logical inconsistencies.

**Example Patterns:**

**Self-Identification Mismatch:**
```
Marie : As John, I must say I find this argument unconvincing.
(Marie labeled as speaking, but refers to herself as John - should be John speaking)
```

**Direct Address Confusion:**
```
Ahmed : Marie, what do you think about this cosmological argument?
(If labeled as Marie, she wouldn't ask herself a question - someone else is asking Marie)
```

**Role Inconsistency:**
```
Marie : From my theological training, I interpret creation ex nihilo as a necessary concept.
(Marie is a scientist, not theologian - this should be Ahmed speaking)

Sofia : As a philosopher specializing in ontology, I believe Leibniz was correct.
(Sofia is a cosmologist, not philosopher - this should be John speaking)
```

**Characteristics:**
- 15-20 diarization errors (sentence splits)
- PLUS 8-12 speaker label errors (entire turn misattributed)
- Total errors: ~25-30 per file
- Errors create semantic/pragmatic inconsistencies

**Example with both error types:**
```
John : Good point, Marie. Let me build on that by considering
Sofia : the implications of quantum uncertainty for ontology.
(Diarization error - sentence split)

Marie : John, I think your philosophical approach is too abstract.
(If labeled as Marie, address confusion - someone is asking John, not Marie speaking)

Ahmed : From my background in theoretical physics, I must object to that interpretation.
(Role inconsistency - Ahmed is theologian, not physicist - should be Marie or Sofia)
```

**Detection Strategy:** Named entity recognition, role-content matching, discourse analysis

---

## Speakers

All conversations feature the same five speakers with distinct intellectual backgrounds:

| ID | Name | Role | Background | Focus |
|----|------|------|------------|-------|
| 1 | John | Philosopher | Analytic philosophy, ontology | Logical arguments, Western philosophy |
| 2 | Marie | Scientist | Theoretical physicist, quantum mechanics | Empirical data, skeptical of metaphysics |
| 3 | Ahmed | Theologian | Comparative religion, Islamic philosophy | Religious perspectives, creation arguments |
| 4 | Sofia | Physicist | Cosmology, Big Bang theory | Cosmological models, mathematical frameworks |
| 5 | Chen | Metaphysician | Eastern philosophy, Buddhist ontology | Eastern philosophical contrasts, holistic thinking |

**Note:** All files use the same English names (John, Marie, Ahmed, Sofia, Chen) regardless of language.

---

## Dataset Statistics

| File | Language | Turns | Total Errors | Diarization | Speaker Label |
|------|----------|-------|--------------|-------------|---------------|
| en_perfect.txt | EN | 105 | 0 | 0 | 0 |
| en_diarization_errors.txt | EN | 119 | 26 | 26 | 0 |
| en_full_errors.txt | EN | 119 | 33 | 23 | 10 |
| fr_perfect.txt | FR | 105 | 0 | 0 | 0 |
| fr_diarization_errors.txt | FR | 119 | 26 | 26 | 0 |
| fr_full_errors.txt | FR | 119 | 33 | 23 | 10 |
| mixed_perfect.txt | Mixed | 105 | 0 | 0 | 0 |
| mixed_diarization_errors.txt | Mixed | 119 | 26 | 26 | 0 |
| mixed_full_errors.txt | Mixed | 119 | 33 | 23 | 10 |

**Note:** Diarization errors add extra turns (sentence splits), increasing total turn count.

---


**Date:** 2025-11-24
**Format:** Plain text (.txt) with UTF-8 encoding
**Original data:** LLM-generated synthetic conversations
**Conversion:** Automated extraction from JSON format

These fixtures are designed to be used in isolation or as part of a comprehensive test suite for diarization and speaker detection systems.
