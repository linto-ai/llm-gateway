#!/usr/bin/env python3
"""strip_wrapping_fence: only a fence wrapping the whole answer is removed."""
from app.core.output_cleanup import strip_wrapping_fence


def test_wrapping_fence_removed():
    assert strip_wrapping_fence("```markdown\n## En bref\ntexte\n```") == "## En bref\ntexte"
    assert strip_wrapping_fence("\n```\n## A\n```\n") == "## A"


def test_unclosed_wrapping_fence_removed():
    assert strip_wrapping_fence("```md\n## A\nb") == "## A\nb"


def test_inner_code_block_kept():
    text = "```bash\nls\n```\n## Suite\ntexte"
    assert strip_wrapping_fence(text) == text
    plain = "## A\n```python\nx = 1\n```\n"
    assert strip_wrapping_fence(plain) == plain


def test_empty_and_plain():
    assert strip_wrapping_fence("") == ""
    assert strip_wrapping_fence("## A") == "## A"
