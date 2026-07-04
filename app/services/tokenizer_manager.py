#!/usr/bin/env python3
"""
TokenizerManager: Central tokenizer management with memory cache + disk persistence.

This singleton manages tokenizer loading, caching, and persistence for LLM models.
It supports both tiktoken (for OpenAI/Anthropic/Google) and HuggingFace tokenizers.
"""

import os

# Force classic HTTP downloads (the xet CDN path has no usable timeout). Must be
# set before transformers is imported; Dockerfile sets the same, env can override.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "10")

import concurrent.futures
import logging
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Union

import tiktoken

from app.core.tokenizer_mappings import (
    get_tokenizer_config,
    get_fallback_tokenizer_config,
)

logger = logging.getLogger(__name__)

# Bounded-download executor: a download overrunning the timeout is abandoned by
# the caller (moves on to fallback), the thread unwinds when its HTTP call times out.
_DOWNLOAD_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="tok-download"
)


class TokenizerLoadError(Exception):
    """Tokenizer could not be loaded; caller falls back to tiktoken."""


# Built-in tiktoken encodings (no download / no I/O).
_TIKTOKEN_ENCODINGS = {"cl100k_base", "o200k_base", "p50k_base", "r50k_base"}


class TokenizerWrapper(Protocol):
    """Protocol for tokenizer wrapper compatibility."""

    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        ...

    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        ...


class TiktokenWrapper:
    """Wrapper for tiktoken encodings to match HuggingFace tokenizer API."""

    def __init__(self, encoding: tiktoken.Encoding, encoding_name: str):
        self._encoding = encoding
        self._encoding_name = encoding_name

    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self._encoding.encode(text)

    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self._encoding.decode(tokens)

    def __call__(self, text: str) -> dict:
        """Compatibility with HuggingFace tokenizer API."""
        return {"input_ids": self.encode(text)}

    @property
    def encoding_name(self) -> str:
        """Get the tiktoken encoding name."""
        return self._encoding_name


class HuggingFaceWrapper:
    """Wrapper for HuggingFace tokenizers."""

    def __init__(self, tokenizer, repo_id: str):
        self._tokenizer = tokenizer
        self._repo_id = repo_id

    def encode(self, text: str) -> list[int]:
        """Encode text to token IDs."""
        return self._tokenizer.encode(text)

    def decode(self, tokens: list[int]) -> str:
        """Decode token IDs to text."""
        return self._tokenizer.decode(tokens)

    def __call__(self, text: str) -> dict:
        """Compatibility with HuggingFace tokenizer API."""
        return self._tokenizer(text)

    @property
    def repo_id(self) -> str:
        """Get the HuggingFace repo ID."""
        return self._repo_id


class TokenizerInfo:
    """Information about a locally stored tokenizer."""

    def __init__(
        self,
        id: str,
        source_repo: str,
        tokenizer_type: str,
        size_bytes: int,
        created_at: datetime,
        bundled: bool = False,
    ):
        self.id = id
        self.source_repo = source_repo
        self.type = tokenizer_type
        self.size_bytes = size_bytes
        self.created_at = created_at
        self.bundled = bundled  # baked into the image (read-only) vs writable cache


class PreloadResult:
    """Result of tokenizer preload operation."""

    def __init__(
        self,
        success: bool,
        model_identifier: str,
        tokenizer_id: str,
        tokenizer_type: str,
        cached: bool,
        message: str,
    ):
        self.success = success
        self.model_identifier = model_identifier
        self.tokenizer_id = tokenizer_id
        self.tokenizer_type = tokenizer_type
        self.cached = cached
        self.message = message


class DeleteResult:
    """Result of tokenizer deletion."""

    def __init__(self, deleted: str, freed_bytes: int):
        self.deleted = deleted
        self.freed_bytes = freed_bytes


class TokenizerManager:
    """
    Singleton tokenizer manager with memory cache + disk persistence.

    Tokenizer Resolution Priority:
    1. Provider-specific (tiktoken) - No network required
    2. model.tokenizer_name - From provider API or manual config
    3. TOKENIZER_MAPPINGS - Known model families
    4. Extract base model - For quantized models
    5. Fallback - tiktoken cl100k_base with WARNING log
    """

    _instance: Optional["TokenizerManager"] = None
    _lock = threading.Lock()

    @staticmethod
    def _get_storage_path() -> Path:
        """Get tokenizer storage path from config or environment."""
        # Try to get from app config first
        try:
            from app.core.config import settings
            return Path(settings.tokenizer_storage_path)
        except Exception:
            pass
        # Fallback to environment variable or default
        return Path(os.getenv("TOKENIZER_STORAGE_PATH", "/var/www/data/tokenizers"))

    @staticmethod
    def _get_bundled_path() -> Path:
        """Get the read-only bundled (baked-in) tokenizer path."""
        try:
            from app.core.config import settings
            return Path(settings.tokenizer_bundled_path)
        except Exception:
            pass
        return Path(os.getenv("TOKENIZER_BUNDLED_PATH", "/opt/linto/tokenizers"))

    @staticmethod
    def _is_offline() -> bool:
        """Whether network fetches are disabled at job time."""
        try:
            from app.core.config import settings
            return bool(settings.tokenizer_offline)
        except Exception:
            return os.getenv("TOKENIZER_OFFLINE", "false").lower() in ("1", "true", "yes")

    @staticmethod
    def _download_timeout() -> int:
        """Hard cap (seconds) on a single tokenizer download."""
        try:
            from app.core.config import settings
            return int(settings.tokenizer_download_timeout)
        except Exception:
            return int(os.getenv("TOKENIZER_DOWNLOAD_TIMEOUT", "30"))

    def __init__(self):
        """Initialize TokenizerManager (private, use get_instance())."""
        # Memory caches
        self._memory_cache: Dict[str, Any] = {}  # HuggingFace tokenizers
        self._tiktoken_cache: Dict[str, TiktokenWrapper] = {}  # tiktoken encodings

        # Storage paths (resolved once on init)
        self.TOKENIZER_STORAGE_PATH = self._get_storage_path()  # writable cache / mount
        self.TOKENIZER_BUNDLED_PATH = self._get_bundled_path()  # read-only, baked

        # Only the writable cache is guaranteed to exist; bundled may be absent in dev.
        self.TOKENIZER_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"TokenizerManager initialized with storage: {self.TOKENIZER_STORAGE_PATH}, "
            f"bundled: {self.TOKENIZER_BUNDLED_PATH} "
            f"(exists={self.TOKENIZER_BUNDLED_PATH.exists()}), offline={self._is_offline()}"
        )

    @classmethod
    def get_instance(cls) -> "TokenizerManager":
        """Get the singleton instance of TokenizerManager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _get_local_path(self, tokenizer_id: str) -> Path:
        """Writable-cache path for a tokenizer (mount-friendly, downloads land here)."""
        # Replace slashes with double dashes for filesystem safety
        safe_id = tokenizer_id.replace("/", "--")
        return self.TOKENIZER_STORAGE_PATH / safe_id

    def _get_bundled_local_path(self, tokenizer_id: str) -> Path:
        """Read-only baked-in path for a tokenizer."""
        safe_id = tokenizer_id.replace("/", "--")
        return self.TOKENIZER_BUNDLED_PATH / safe_id

    def _find_on_disk(self, tokenizer_id: str) -> Optional[Path]:
        """Return the on-disk dir for a tokenizer, writable cache first then bundled."""
        cache_path = self._get_local_path(tokenizer_id)
        if cache_path.exists():
            return cache_path
        bundled_path = self._get_bundled_local_path(tokenizer_id)
        if bundled_path.exists():
            return bundled_path
        return None

    def _tokenizer_id_from_path(self, path: Path) -> str:
        """Convert path back to tokenizer ID."""
        return path.name.replace("--", "/")

    def _load_tiktoken(self, encoding_name: str) -> TiktokenWrapper:
        """Load a tiktoken encoding with caching."""
        if encoding_name in self._tiktoken_cache:
            return self._tiktoken_cache[encoding_name]

        try:
            encoding = tiktoken.get_encoding(encoding_name)
            wrapper = TiktokenWrapper(encoding, encoding_name)
            self._tiktoken_cache[encoding_name] = wrapper
            logger.debug(f"Loaded tiktoken encoding: {encoding_name}")
            return wrapper
        except Exception as e:
            logger.exception(f"Failed to load tiktoken encoding {encoding_name}: {e}")
            raise

    def _load_from_local(self, tokenizer_id: str) -> Optional[HuggingFaceWrapper]:
        """Load a HuggingFace tokenizer from disk (writable cache, then bundled)."""
        local_path = self._find_on_disk(tokenizer_id)
        if local_path is None:
            return None

        try:
            from transformers import AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(str(local_path))
            wrapper = HuggingFaceWrapper(tokenizer, tokenizer_id)
            self._memory_cache[tokenizer_id] = wrapper
            logger.debug(f"Loaded tokenizer from disk ({local_path}): {tokenizer_id}")
            return wrapper
        except Exception as e:
            logger.exception(f"Failed to load tokenizer from disk {local_path}: {tokenizer_id}: {e}")
            return None

    def _download_and_save(self, tokenizer_id: str) -> HuggingFaceWrapper:
        """Download a HuggingFace tokenizer to the writable cache, bounded by
        tokenizer_download_timeout. Raises TokenizerLoadError on timeout/failure."""
        local_path = self._get_local_path(tokenizer_id)
        timeout = self._download_timeout()

        def _do_download() -> Any:
            from transformers import AutoTokenizer
            logger.info(f"Downloading tokenizer: {tokenizer_id}")
            tokenizer = AutoTokenizer.from_pretrained(tokenizer_id)
            tokenizer.save_pretrained(str(local_path))
            return tokenizer

        future = _DOWNLOAD_EXECUTOR.submit(_do_download)
        try:
            tokenizer = future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()  # thread keeps running until its HTTP call times out, then exits
            raise TokenizerLoadError(
                f"Tokenizer download timed out after {timeout}s: {tokenizer_id}"
            )
        except Exception as e:
            raise TokenizerLoadError(f"Failed to download tokenizer {tokenizer_id}: {e}") from e

        logger.info(f"Saved tokenizer to: {local_path}")
        wrapper = HuggingFaceWrapper(tokenizer, tokenizer_id)
        self._memory_cache[tokenizer_id] = wrapper
        return wrapper

    def load(self, tokenizer_name: str) -> Union[TiktokenWrapper, HuggingFaceWrapper]:
        """Resolve a concrete tokenizer identifier to a wrapper. Never hangs,
        never raises: tiktoken name / memory / disk (cache then bundled) /
        bounded download (skipped when offline) / tiktoken estimate fallback."""
        # tiktoken encodings are built in, no I/O
        if tokenizer_name in self._tiktoken_cache or tokenizer_name in _TIKTOKEN_ENCODINGS:
            try:
                return self._load_tiktoken(tokenizer_name)
            except Exception:
                logger.warning(f"tiktoken '{tokenizer_name}' failed, using cl100k_base", exc_info=True)
                return self._load_tiktoken("cl100k_base")

        # HuggingFace repo
        if tokenizer_name in self._memory_cache:
            return self._memory_cache[tokenizer_name]

        local = self._load_from_local(tokenizer_name)
        if local:
            return local

        if self._is_offline():
            logger.warning(
                f"Tokenizer '{tokenizer_name}' not bundled/cached and offline mode is on; "
                "using tiktoken cl100k_base estimate"
            )
            return self._load_tiktoken("cl100k_base")

        try:
            return self._download_and_save(tokenizer_name)
        except Exception as e:
            logger.warning(
                f"Tokenizer '{tokenizer_name}' unavailable ({e}); using tiktoken cl100k_base estimate",
                exc_info=True,
            )
            return self._load_tiktoken("cl100k_base")

    def _resolve_tokenizer_config(self, model) -> Dict[str, Any]:
        """
        Resolve tokenizer configuration for a model.

        Priority:
        1. model.tokenizer_name - check TOKENIZER_MAPPINGS first, then treat as HuggingFace repo
        2. TOKENIZER_MAPPINGS lookup by model_identifier
        3. Extract base model from quantized identifier
        4. Fallback to tiktoken cl100k_base
        """
        model_identifier = model.model_identifier

        # Priority 1: model.tokenizer_name
        if model.tokenizer_name:
            # First check if it's a known tokenizer in our mappings (tiktoken or HuggingFace)
            config = get_tokenizer_config(model.tokenizer_name)
            if config:
                return config
            # Otherwise treat as HuggingFace repo (only if it looks like a repo with /)
            if "/" in model.tokenizer_name:
                return {
                    "type": "huggingface",
                    "repo": model.tokenizer_name,
                }
            # If not a known mapping and not a HuggingFace repo format, log warning and continue
            logger.warning(
                f"Unknown tokenizer_name '{model.tokenizer_name}' for model '{model_identifier}', "
                "trying model_identifier lookup"
            )

        # Priority 2 & 3: TOKENIZER_MAPPINGS lookup (handles base model extraction)
        config = get_tokenizer_config(model_identifier)
        if config:
            return config

        # Priority 4: Fallback
        logger.warning(
            f"No tokenizer mapping found for model '{model_identifier}', using fallback"
        )
        return get_fallback_tokenizer_config()

    def get_tokenizer_for_model(self, model) -> Union[TiktokenWrapper, HuggingFaceWrapper]:
        """
        Get a tokenizer for a model.

        Args:
            model: Model ORM object with model_identifier and tokenizer_name

        Returns:
            TokenizerWrapper (either TiktokenWrapper or HuggingFaceWrapper)
        """
        config = self._resolve_tokenizer_config(model)

        if config["type"] == "tiktoken":
            encoding_name = config["encoding"]
            if config.get("estimated"):
                logger.debug(
                    f"Using estimated tiktoken encoding for model {model.model_identifier}"
                )
            return self._load_tiktoken(encoding_name)

        # HuggingFace tokenizer: single non-hanging, non-raising path.
        return self.load(config["repo"])

    def count_tokens(self, model, text: str) -> int:
        """
        Count tokens in text using the appropriate tokenizer for the model.

        Args:
            model: Model ORM object
            text: Text to tokenize

        Returns:
            Number of tokens
        """
        tokenizer = self.get_tokenizer_for_model(model)
        return len(tokenizer.encode(text))

    def preload_tokenizer(self, model) -> PreloadResult:
        """
        Preload tokenizer for a model (download and persist if needed).

        Args:
            model: Model ORM object

        Returns:
            PreloadResult with success status and details
        """
        config = self._resolve_tokenizer_config(model)
        model_identifier = model.model_identifier

        if config["type"] == "tiktoken":
            encoding_name = config["encoding"]
            try:
                self._load_tiktoken(encoding_name)
                return PreloadResult(
                    success=True,
                    model_identifier=model_identifier,
                    tokenizer_id=encoding_name,
                    tokenizer_type="tiktoken",
                    cached=True,
                    message=f"Tiktoken encoding '{encoding_name}' loaded (built-in)",
                )
            except Exception as e:
                return PreloadResult(
                    success=False,
                    model_identifier=model_identifier,
                    tokenizer_id=encoding_name,
                    tokenizer_type="tiktoken",
                    cached=False,
                    message=f"Failed to load tiktoken encoding: {e}",
                )

        # HuggingFace tokenizer
        repo = config["repo"]

        # Check if already available on disk (writable cache or bundled)
        if self._find_on_disk(repo) is not None:
            try:
                self._load_from_local(repo)
                return PreloadResult(
                    success=True,
                    model_identifier=model_identifier,
                    tokenizer_id=repo,
                    tokenizer_type="huggingface",
                    cached=True,
                    message="Tokenizer already available on disk",
                )
            except Exception as e:
                logger.warning(f"Cached tokenizer corrupted, re-downloading: {e}", exc_info=True)

        # Download and save
        try:
            self._download_and_save(repo)
            return PreloadResult(
                success=True,
                model_identifier=model_identifier,
                tokenizer_id=repo,
                tokenizer_type="huggingface",
                cached=False,
                message="Tokenizer downloaded and persisted",
            )
        except Exception as e:
            logger.exception(f"Failed to preload tokenizer for {model_identifier}: {e}")
            return PreloadResult(
                success=False,
                model_identifier=model_identifier,
                tokenizer_id=repo,
                tokenizer_type="huggingface",
                cached=False,
                message=f"Failed to load tokenizer: {e}",
            )

    def list_local_tokenizers(self) -> List[TokenizerInfo]:
        """
        List tokenizers available on disk: writable cache plus baked-in bundled
        ones. A cache entry shadows a bundled one with the same id (same as
        resolution order), so each repo appears once.

        Returns:
            List of TokenizerInfo objects
        """
        by_id: Dict[str, TokenizerInfo] = {}

        # Bundled first so cache entries override them.
        for base_path, bundled in ((self.TOKENIZER_BUNDLED_PATH, True),
                                   (self.TOKENIZER_STORAGE_PATH, False)):
            if not base_path.exists():
                continue
            for path in base_path.iterdir():
                if not path.is_dir():
                    continue
                tokenizer_id = self._tokenizer_id_from_path(path)
                size_bytes = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                created_at = datetime.fromtimestamp(path.stat().st_ctime, tz=timezone.utc)
                by_id[path.name] = TokenizerInfo(
                    id=path.name,  # Filesystem-safe ID (with --)
                    source_repo=tokenizer_id,  # Original repo name (with /)
                    tokenizer_type="huggingface",
                    size_bytes=size_bytes,
                    created_at=created_at,
                    bundled=bundled,
                )

        return list(by_id.values())

    def delete_tokenizer(self, tokenizer_id: str) -> DeleteResult:
        """
        Delete a tokenizer from local storage.

        Args:
            tokenizer_id: Tokenizer ID (filesystem-safe format with --)

        Returns:
            DeleteResult with deleted ID and freed bytes

        Raises:
            FileNotFoundError: If tokenizer not found
        """
        # Handle both formats (-- and /)
        safe_id = tokenizer_id.replace("/", "--")
        local_path = self.TOKENIZER_STORAGE_PATH / safe_id

        if not local_path.exists():
            raise FileNotFoundError(f"Tokenizer not found: {tokenizer_id}")

        # Calculate size before deletion
        size_bytes = sum(f.stat().st_size for f in local_path.rglob("*") if f.is_file())

        # Remove from memory cache
        original_id = tokenizer_id.replace("--", "/")
        if original_id in self._memory_cache:
            del self._memory_cache[original_id]

        # Delete from disk
        shutil.rmtree(local_path)
        logger.info(f"Deleted tokenizer: {tokenizer_id} ({size_bytes} bytes freed)")

        return DeleteResult(
            deleted=original_id,
            freed_bytes=size_bytes,
        )

    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information."""
        total_size = 0
        if self.TOKENIZER_STORAGE_PATH.exists():
            total_size = sum(
                f.stat().st_size
                for f in self.TOKENIZER_STORAGE_PATH.rglob("*")
                if f.is_file()
            )

        return {
            "storage_path": str(self.TOKENIZER_STORAGE_PATH),
            "total_size_bytes": total_size,
        }
