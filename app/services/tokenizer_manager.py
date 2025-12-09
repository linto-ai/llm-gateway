#!/usr/bin/env python3
"""
TokenizerManager: Central tokenizer management with memory cache + disk persistence.

This singleton manages tokenizer loading, caching, and persistence for LLM models.
It supports both tiktoken (for OpenAI/Anthropic/Google) and HuggingFace tokenizers.
"""

import os
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
    ):
        self.id = id
        self.source_repo = source_repo
        self.type = tokenizer_type
        self.size_bytes = size_bytes
        self.created_at = created_at


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

    def __init__(self):
        """Initialize TokenizerManager (private, use get_instance())."""
        # Memory caches
        self._memory_cache: Dict[str, Any] = {}  # HuggingFace tokenizers
        self._tiktoken_cache: Dict[str, TiktokenWrapper] = {}  # tiktoken encodings

        # Storage path (resolved once on init)
        self.TOKENIZER_STORAGE_PATH = self._get_storage_path()

        # Ensure storage directory exists
        self.TOKENIZER_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

        logger.info(f"TokenizerManager initialized with storage: {self.TOKENIZER_STORAGE_PATH}")

    @classmethod
    def get_instance(cls) -> "TokenizerManager":
        """Get the singleton instance of TokenizerManager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _get_local_path(self, tokenizer_id: str) -> Path:
        """Get the local storage path for a tokenizer."""
        # Replace slashes with double dashes for filesystem safety
        safe_id = tokenizer_id.replace("/", "--")
        return self.TOKENIZER_STORAGE_PATH / safe_id

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
            logger.error(f"Failed to load tiktoken encoding {encoding_name}: {e}")
            raise

    def _load_from_local(self, tokenizer_id: str) -> Optional[HuggingFaceWrapper]:
        """Load a HuggingFace tokenizer from local storage."""
        local_path = self._get_local_path(tokenizer_id)

        if not local_path.exists():
            return None

        try:
            from transformers import AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(str(local_path))
            wrapper = HuggingFaceWrapper(tokenizer, tokenizer_id)
            self._memory_cache[tokenizer_id] = wrapper
            logger.debug(f"Loaded tokenizer from local storage: {tokenizer_id}")
            return wrapper
        except Exception as e:
            logger.error(f"Failed to load tokenizer from local: {tokenizer_id}: {e}")
            return None

    def _download_and_save(self, tokenizer_id: str) -> HuggingFaceWrapper:
        """Download a HuggingFace tokenizer and save to local storage."""
        from transformers import AutoTokenizer

        local_path = self._get_local_path(tokenizer_id)

        try:
            logger.info(f"Downloading tokenizer: {tokenizer_id}")
            tokenizer = AutoTokenizer.from_pretrained(tokenizer_id)

            # Save to local storage
            tokenizer.save_pretrained(str(local_path))
            logger.info(f"Saved tokenizer to: {local_path}")

            wrapper = HuggingFaceWrapper(tokenizer, tokenizer_id)
            self._memory_cache[tokenizer_id] = wrapper
            return wrapper
        except Exception as e:
            logger.error(f"Failed to download tokenizer {tokenizer_id}: {e}")
            raise

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

        # HuggingFace tokenizer
        repo = config["repo"]

        # Check memory cache
        if repo in self._memory_cache:
            return self._memory_cache[repo]

        # Check local storage
        local_tokenizer = self._load_from_local(repo)
        if local_tokenizer:
            return local_tokenizer

        # Download and save
        try:
            return self._download_and_save(repo)
        except Exception as e:
            logger.error(f"Failed to load HuggingFace tokenizer {repo}: {e}")
            # Fallback to tiktoken
            logger.warning(f"Falling back to tiktoken for model {model.model_identifier}")
            return self._load_tiktoken("cl100k_base")

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
        local_path = self._get_local_path(repo)

        # Check if already cached locally
        if local_path.exists():
            try:
                self._load_from_local(repo)
                return PreloadResult(
                    success=True,
                    model_identifier=model_identifier,
                    tokenizer_id=repo,
                    tokenizer_type="huggingface",
                    cached=True,
                    message="Tokenizer already cached locally",
                )
            except Exception as e:
                logger.warning(f"Cached tokenizer corrupted, re-downloading: {e}")

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
            logger.error(f"Failed to preload tokenizer for {model_identifier}: {e}")
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
        List all tokenizers persisted locally.

        Returns:
            List of TokenizerInfo objects
        """
        tokenizers = []

        if not self.TOKENIZER_STORAGE_PATH.exists():
            return tokenizers

        for path in self.TOKENIZER_STORAGE_PATH.iterdir():
            if path.is_dir():
                tokenizer_id = self._tokenizer_id_from_path(path)
                size_bytes = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                created_at = datetime.fromtimestamp(
                    path.stat().st_ctime, tz=timezone.utc
                )

                tokenizers.append(
                    TokenizerInfo(
                        id=path.name,  # Filesystem-safe ID (with --)
                        source_repo=tokenizer_id,  # Original repo name (with /)
                        tokenizer_type="huggingface",
                        size_bytes=size_bytes,
                        created_at=created_at,
                    )
                )

        return tokenizers

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
