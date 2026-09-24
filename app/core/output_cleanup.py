"""Deterministic cleanup of an LLM output before it is stored.

Models such as Mistral Small sometimes wrap the whole answer in a Markdown code block
(```markdown ... ```) despite the prompt; Studio then shows raw Markdown in its editor.
Only a fence wrapping the whole answer is removed: code blocks inside the text are kept.
"""
import re

_OPENING = re.compile(r"^\s*```[A-Za-z0-9_-]*\s*$")
_CLOSING = re.compile(r"^\s*```\s*$")


def strip_wrapping_fence(text: str) -> str:
    if not text:
        return text
    lines = text.strip("\n").split("\n")
    if not lines or not _OPENING.match(lines[0]):
        return text
    body = lines[1:]
    if body and _CLOSING.match(body[-1]):
        body = body[:-1]
    elif any(_CLOSING.match(l) for l in body):
        return text  # the first fence closes inside the answer: it is a real code block
    return "\n".join(body).strip("\n")
