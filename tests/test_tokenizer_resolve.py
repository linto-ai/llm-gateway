"""
TokenizerManager.load: the non-hanging, non-raising resolve path (2.5.2).

These are the offline-safe guarantees that keep a Celery worker from wedging on
tokenizer resolution. They run with no network.
"""

import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.tokenizer_manager import (
    TokenizerManager,
    TiktokenWrapper,
    HuggingFaceWrapper,
)


@pytest.fixture
def manager():
    """Fresh manager with temp writable cache and temp bundled dir."""
    cache_dir = tempfile.mkdtemp()
    bundled_dir = tempfile.mkdtemp()

    TokenizerManager._instance = None
    # Save the real staticmethod descriptors so we restore them intact (a bare
    # function would turn into a bound method and break other tests' __init__).
    orig = {
        name: TokenizerManager.__dict__[name]
        for name in ("_get_storage_path", "_get_bundled_path")
    }
    TokenizerManager._get_storage_path = staticmethod(lambda: Path(cache_dir))
    TokenizerManager._get_bundled_path = staticmethod(lambda: Path(bundled_dir))

    try:
        mgr = TokenizerManager.get_instance()
        yield mgr
    finally:
        for name, desc in orig.items():
            setattr(TokenizerManager, name, desc)
        TokenizerManager._instance = None
        shutil.rmtree(cache_dir, ignore_errors=True)
        shutil.rmtree(bundled_dir, ignore_errors=True)


def test_load_tiktoken_name(manager):
    tok = manager.load("cl100k_base")
    assert isinstance(tok, TiktokenWrapper)


def test_offline_unknown_repo_falls_back_without_download(manager):
    """Offline + not bundled/cached -> tiktoken estimate, no network, no raise."""
    manager._is_offline = lambda: True

    with patch("transformers.AutoTokenizer") as mock_auto:
        tok = manager.load("some-org/never-heard-of-this")
        assert isinstance(tok, TiktokenWrapper)
        mock_auto.from_pretrained.assert_not_called()


def test_bundled_resolves_without_download(manager):
    """A baked-in tokenizer loads from the bundled dir, no download attempted."""
    repo = "mistralai/Mistral-7B-Instruct-v0.3"
    bundled_path = manager._get_bundled_local_path(repo)
    bundled_path.mkdir(parents=True)
    (bundled_path / "tokenizer.json").write_text("{}")

    with patch("transformers.AutoTokenizer") as mock_auto:
        loaded = MagicMock()
        loaded.encode.return_value = [1, 2, 3]
        mock_auto.from_pretrained.return_value = loaded

        tok = manager.load(repo)

        assert isinstance(tok, HuggingFaceWrapper)
        # loaded from the bundled path, never from the bare repo id
        called_arg = str(mock_auto.from_pretrained.call_args.args[0])
        assert str(bundled_path) == called_arg


def test_download_failure_falls_back_and_never_raises(manager):
    """A raising download degrades to tiktoken, never propagates."""
    with patch("transformers.AutoTokenizer") as mock_auto:
        mock_auto.from_pretrained.side_effect = Exception("boom / network")
        tok = manager.load("some-org/some-repo")
        assert isinstance(tok, TiktokenWrapper)


def test_download_timeout_falls_back(manager):
    """A download that overruns the bound is abandoned, resolution falls back."""
    manager._download_timeout = lambda: 0.2

    def slow(*args, **kwargs):
        time.sleep(3)
        return MagicMock()

    with patch("transformers.AutoTokenizer") as mock_auto:
        mock_auto.from_pretrained.side_effect = slow
        start = time.time()
        tok = manager.load("some-org/slow-repo")
        elapsed = time.time() - start
        assert isinstance(tok, TiktokenWrapper)
        assert elapsed < 2.0, f"load did not honor the download bound: {elapsed:.2f}s"


def test_cache_shadows_bundled_in_listing(manager):
    """Same id in cache and bundled appears once, cache wins, bundled flagged."""
    repo = "mistralai/Mistral-7B-Instruct-v0.3"
    for base in (manager._get_bundled_local_path(repo), manager._get_local_path(repo)):
        base.mkdir(parents=True)
        (base / "tokenizer.json").write_text("{}")

    listed = manager.list_local_tokenizers()
    matching = [t for t in listed if t.source_repo == repo]
    assert len(matching) == 1
    assert matching[0].bundled is False  # writable cache shadows bundled


def test_bundled_only_is_flagged(manager):
    repo = "mistralai/Mistral-Small-24B-Instruct-2501"
    base = manager._get_bundled_local_path(repo)
    base.mkdir(parents=True)
    (base / "tokenizer.json").write_text("{}")

    listed = manager.list_local_tokenizers()
    matching = [t for t in listed if t.source_repo == repo]
    assert len(matching) == 1
    assert matching[0].bundled is True


def test_backend_load_tokenizer_delegates(manager):
    """backend._load_tokenizer routes through the same non-raising path."""
    from app.backends.backend import LLMBackend

    backend = LLMBackend.__new__(LLMBackend)  # skip __init__
    import logging
    backend.logger = logging.getLogger("test")

    tok = backend._load_tokenizer("cl100k_base")
    assert isinstance(tok, TiktokenWrapper)
