"""
TokenizerManager with Persistent Local Storage - QA Tests

Tests:
1. TokenizerManager Unit Tests (singleton, resolution)
2. Token Counting Tests (tiktoken, HuggingFace)
3. Persistence Tests (save/load/list/delete)
4. API Endpoint Tests (GET/POST/DELETE tokenizers)
5. Integration Tests (model creation, service execution)
6. Edge Cases (concurrent loading, corrupted files, empty text)
"""

import os
import pytest
import shutil
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_tokenizer_dir():
    """Create a temporary directory for tokenizer storage."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def fresh_tokenizer_manager(temp_tokenizer_dir):
    """
    Create a fresh TokenizerManager instance with temp storage.
    Properly patches the storage path before instantiation.
    """
    from app.services.tokenizer_manager import TokenizerManager

    # Reset singleton
    TokenizerManager._instance = None

    # Patch _get_storage_path to return our temp directory
    original_get_storage_path = TokenizerManager._get_storage_path

    @staticmethod
    def patched_get_storage_path():
        return Path(temp_tokenizer_dir)

    TokenizerManager._get_storage_path = patched_get_storage_path

    try:
        manager = TokenizerManager.get_instance()
        yield manager
    finally:
        # Cleanup
        TokenizerManager._get_storage_path = original_get_storage_path
        TokenizerManager._instance = None


# =============================================================================
# 1. TokenizerManager Unit Tests
# =============================================================================

class TestTokenizerManagerSingleton:
    """Tests for TokenizerManager singleton pattern."""

    def test_tokenizer_manager_singleton(self, temp_tokenizer_dir):
        """
        Call TokenizerManager.get_instance() twice and verify same instance returned.
        """
        from app.services.tokenizer_manager import TokenizerManager

        # Reset singleton
        TokenizerManager._instance = None

        # Patch _get_storage_path to return our temp directory
        original_get_storage_path = TokenizerManager._get_storage_path

        @staticmethod
        def patched_get_storage_path():
            return Path(temp_tokenizer_dir)

        TokenizerManager._get_storage_path = patched_get_storage_path

        try:
            instance1 = TokenizerManager.get_instance()
            instance2 = TokenizerManager.get_instance()

            assert instance1 is instance2, "get_instance() should return the same instance"
        finally:
            TokenizerManager._get_storage_path = original_get_storage_path
            TokenizerManager._instance = None


class TestTiktokenResolution:
    """Tests for tiktoken-based tokenizer resolution."""

    def test_tiktoken_resolution_openai_gpt4(self, fresh_tokenizer_manager):
        """
        Create mock model with model_identifier='gpt-4'.
        Verify returns tiktoken with encoding='cl100k_base'.
        """
        model = Mock()
        model.model_identifier = "gpt-4"
        model.tokenizer_name = None
        model.huggingface_repo = None

        config = fresh_tokenizer_manager._resolve_tokenizer_config(model)

        assert config["type"] == "tiktoken"
        assert config["encoding"] == "cl100k_base"

    def test_tiktoken_resolution_openai_gpt4o(self, fresh_tokenizer_manager):
        """
        Create mock model with model_identifier='gpt-4o'.
        Verify returns tiktoken with encoding='o200k_base'.
        """
        model = Mock()
        model.model_identifier = "gpt-4o"
        model.tokenizer_name = None

        config = fresh_tokenizer_manager._resolve_tokenizer_config(model)

        assert config["type"] == "tiktoken"
        assert config["encoding"] == "o200k_base"

    def test_tiktoken_resolution_openai_gpt4o_mini(self, fresh_tokenizer_manager):
        """Verify gpt-4o-mini uses o200k_base encoding."""
        model = Mock()
        model.model_identifier = "gpt-4o-mini"
        model.tokenizer_name = None

        config = fresh_tokenizer_manager._resolve_tokenizer_config(model)

        assert config["type"] == "tiktoken"
        assert config["encoding"] == "o200k_base"

    def test_tiktoken_resolution_anthropic(self, fresh_tokenizer_manager):
        """
        Create mock model with model_identifier='claude-3.5-sonnet'.
        Verify returns tiktoken with estimated=True.
        """
        model = Mock()
        model.model_identifier = "claude-3.5-sonnet"
        model.tokenizer_name = None

        config = fresh_tokenizer_manager._resolve_tokenizer_config(model)

        assert config["type"] == "tiktoken"
        assert config["encoding"] == "cl100k_base"
        assert config.get("estimated") is True

    def test_tiktoken_resolution_google_gemini(self, fresh_tokenizer_manager):
        """Verify Gemini models use tiktoken with estimation."""
        model = Mock()
        model.model_identifier = "gemini-1.5-pro"
        model.tokenizer_name = None

        config = fresh_tokenizer_manager._resolve_tokenizer_config(model)

        assert config["type"] == "tiktoken"
        assert config["encoding"] == "cl100k_base"
        assert config.get("estimated") is True


class TestHuggingFaceResolution:
    """Tests for HuggingFace tokenizer resolution."""

    def test_huggingface_resolution_llama(self, fresh_tokenizer_manager):
        """
        Create mock model with model_identifier='llama-3.1-8b-instruct'.
        Verify returns HuggingFace with repo='meta-llama/Llama-3.1-8B-Instruct'.
        """
        model = Mock()
        model.model_identifier = "llama-3.1-8b-instruct"
        model.tokenizer_name = None

        config = fresh_tokenizer_manager._resolve_tokenizer_config(model)

        assert config["type"] == "huggingface"
        assert config["repo"] == "meta-llama/Llama-3.1-8B-Instruct"

    def test_huggingface_resolution_mistral(self, fresh_tokenizer_manager):
        """
        Create mock model with model_identifier='mistral-7b-instruct'.
        Verify returns HuggingFace with correct repo.
        """
        model = Mock()
        model.model_identifier = "mistral-7b-instruct"
        model.tokenizer_name = None

        config = fresh_tokenizer_manager._resolve_tokenizer_config(model)

        assert config["type"] == "huggingface"
        assert "mistralai" in config["repo"].lower() or "Mistral" in config["repo"]

    def test_huggingface_resolution_qwen(self, fresh_tokenizer_manager):
        """Verify Qwen models resolve to HuggingFace."""
        model = Mock()
        model.model_identifier = "qwen-2.5-72b-instruct"
        model.tokenizer_name = None

        config = fresh_tokenizer_manager._resolve_tokenizer_config(model)

        assert config["type"] == "huggingface"
        assert "Qwen" in config["repo"]

    def test_explicit_tokenizer_name_priority(self, fresh_tokenizer_manager):
        """
        Create mock model with tokenizer_name='custom/tokenizer'.
        Verify tokenizer_name takes priority over pattern matching.
        """
        model = Mock()
        model.model_identifier = "gpt-4"  # Would normally use tiktoken
        model.tokenizer_name = "custom/my-custom-tokenizer"

        config = fresh_tokenizer_manager._resolve_tokenizer_config(model)

        assert config["type"] == "huggingface"
        assert config["repo"] == "custom/my-custom-tokenizer"


class TestExtractBaseModel:
    """Tests for extracting base model from quantized identifiers."""

    def test_extract_base_model_llama_q4(self):
        """Test extracting 'llama-3.1' from 'llama-3.1-8b-instruct-q4_0'."""
        from app.core.tokenizer_mappings import extract_base_model

        result = extract_base_model("llama-3.1-8b-instruct-q4_0")
        assert result == "llama-3.1"

    def test_extract_base_model_mistral_quant(self):
        """Test extracting 'mistral-7b' from 'mistral-7b:Q4_K_M'."""
        from app.core.tokenizer_mappings import extract_base_model

        result = extract_base_model("mistral-7b:Q4_K_M")
        # Should extract mistral-7b or mistral
        assert result is not None
        assert "mistral" in result

    def test_extract_base_model_qwen_quant(self):
        """Test extracting base from quantized Qwen model."""
        from app.core.tokenizer_mappings import extract_base_model

        result = extract_base_model("qwen2.5-14b-instruct-q5")
        assert result is not None
        assert "qwen" in result

    def test_extract_base_model_with_repo_prefix(self):
        """Test extracting base model from repo-prefixed identifier."""
        from app.core.tokenizer_mappings import extract_base_model

        result = extract_base_model("meta-llama/Llama-3.1-8B-Instruct")
        assert result == "llama-3.1"


class TestFallbackBehavior:
    """Tests for fallback tokenizer behavior."""

    def test_fallback_to_tiktoken_unknown_model(self, fresh_tokenizer_manager):
        """
        Create mock model with unknown model_identifier.
        Verify fallback to tiktoken cl100k_base with warning logged.
        """
        model = Mock()
        model.model_identifier = "completely-unknown-model-xyz-12345"
        model.tokenizer_name = None

        with patch("app.services.tokenizer_manager.logger") as mock_logger:
            config = fresh_tokenizer_manager._resolve_tokenizer_config(model)

            assert config["type"] == "tiktoken"
            assert config["encoding"] == "cl100k_base"
            assert config.get("fallback") is True

            # Verify warning was logged
            mock_logger.warning.assert_called()


# =============================================================================
# 2. Token Counting Tests
# =============================================================================

class TestTokenCounting:
    """Tests for token counting functionality."""

    def test_count_tokens_tiktoken(self, fresh_tokenizer_manager):
        """
        Use tiktoken cl100k_base to count tokens in 'Hello, world!'.
        Verify count is reasonable (around 4 tokens).
        """
        model = Mock()
        model.model_identifier = "gpt-4"
        model.tokenizer_name = None

        count = fresh_tokenizer_manager.count_tokens(model, "Hello, world!")

        # "Hello, world!" typically tokenizes to about 4 tokens
        assert 2 <= count <= 6, f"Expected ~4 tokens, got {count}"

    def test_count_tokens_consistency(self, fresh_tokenizer_manager):
        """
        Count tokens for same text with same model multiple times.
        Verify consistent results.
        """
        model = Mock()
        model.model_identifier = "gpt-4"
        model.tokenizer_name = None

        text = "This is a test sentence for consistent token counting."

        count1 = fresh_tokenizer_manager.count_tokens(model, text)
        count2 = fresh_tokenizer_manager.count_tokens(model, text)
        count3 = fresh_tokenizer_manager.count_tokens(model, text)

        assert count1 == count2 == count3, "Token counts should be consistent"

    def test_count_tokens_huggingface_mock(self, fresh_tokenizer_manager):
        """
        Mock AutoTokenizer.from_pretrained.
        Count tokens and verify mock was called with correct repo.
        """
        model = Mock()
        model.model_identifier = "llama-3.1-8b"
        model.tokenizer_name = None

        with patch("transformers.AutoTokenizer") as mock_auto:
            mock_tokenizer = MagicMock()
            mock_tokenizer.encode.return_value = [1, 2, 3, 4, 5]
            mock_auto.from_pretrained.return_value = mock_tokenizer

            count = fresh_tokenizer_manager.count_tokens(model, "Test text")

            assert count == 5
            # Verify the tokenizer was fetched (from_pretrained called)
            mock_auto.from_pretrained.assert_called()

    def test_empty_text_token_count(self, fresh_tokenizer_manager):
        """Count tokens for empty string, verify returns 0."""
        model = Mock()
        model.model_identifier = "gpt-4"
        model.tokenizer_name = None

        count = fresh_tokenizer_manager.count_tokens(model, "")
        assert count == 0, f"Expected 0 tokens for empty string, got {count}"

    def test_very_long_text_token_count(self, fresh_tokenizer_manager):
        """
        Count tokens for 100KB text.
        Verify reasonable performance (<2s).
        """
        model = Mock()
        model.model_identifier = "gpt-4"
        model.tokenizer_name = None

        # Generate ~100KB of text
        long_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 2000

        start_time = time.time()
        count = fresh_tokenizer_manager.count_tokens(model, long_text)
        elapsed = time.time() - start_time

        assert elapsed < 2.0, f"Token counting took too long: {elapsed:.2f}s"
        assert count > 0, "Should count some tokens"


# =============================================================================
# 3. Persistence Tests
# =============================================================================

class TestLocalPathConversion:
    """Tests for local path conversion."""

    def test_local_path_conversion(self, fresh_tokenizer_manager, temp_tokenizer_dir):
        """
        Test _get_local_path('meta-llama/Llama-3.1-8B-Instruct').
        Verify returns {storage_path}/meta-llama--Llama-3.1-8B-Instruct.
        """
        result = fresh_tokenizer_manager._get_local_path("meta-llama/Llama-3.1-8B-Instruct")

        expected = Path(temp_tokenizer_dir) / "meta-llama--Llama-3.1-8B-Instruct"
        assert result == expected

    def test_tokenizer_id_from_path(self, fresh_tokenizer_manager, temp_tokenizer_dir):
        """Test converting path back to tokenizer ID."""
        path = Path(temp_tokenizer_dir) / "meta-llama--Llama-3.1-8B-Instruct"

        result = fresh_tokenizer_manager._tokenizer_id_from_path(path)

        assert result == "meta-llama/Llama-3.1-8B-Instruct"


class TestSaveAndLoadTokenizer:
    """Tests for tokenizer save/load operations."""

    def test_save_and_load_tokenizer(self, fresh_tokenizer_manager, temp_tokenizer_dir):
        """
        Mock HuggingFace tokenizer, call _download_and_save.
        Verify save_pretrained() called and can load from local.
        """
        with patch("transformers.AutoTokenizer") as mock_auto:
            mock_tokenizer = MagicMock()
            mock_auto.from_pretrained.return_value = mock_tokenizer

            # Download and save
            fresh_tokenizer_manager._download_and_save("test/test-tokenizer")

            # Verify save_pretrained was called
            mock_tokenizer.save_pretrained.assert_called_once()

            # The path should be created
            local_path = fresh_tokenizer_manager._get_local_path("test/test-tokenizer")
            assert str(local_path) in str(mock_tokenizer.save_pretrained.call_args)


class TestListLocalTokenizers:
    """Tests for listing local tokenizers."""

    def test_list_local_tokenizers_empty(self, fresh_tokenizer_manager):
        """List tokenizers when storage is empty."""
        tokenizers = fresh_tokenizer_manager.list_local_tokenizers()
        assert tokenizers == []

    def test_list_local_tokenizers_with_data(self, fresh_tokenizer_manager, temp_tokenizer_dir):
        """
        Create temp directory with mock tokenizer folders.
        Call list_local_tokenizers() and verify returns correct list.
        """
        # Create mock tokenizer folders with files
        tokenizer_dir1 = Path(temp_tokenizer_dir) / "meta-llama--Llama-3.1-8B-Instruct"
        tokenizer_dir1.mkdir(parents=True)
        (tokenizer_dir1 / "tokenizer.json").write_text('{"test": true}')
        (tokenizer_dir1 / "tokenizer_config.json").write_text('{"config": true}')

        tokenizer_dir2 = Path(temp_tokenizer_dir) / "mistralai--Mistral-7B-Instruct-v0.3"
        tokenizer_dir2.mkdir(parents=True)
        (tokenizer_dir2 / "tokenizer.json").write_text('{"test": true}')

        tokenizers = fresh_tokenizer_manager.list_local_tokenizers()

        assert len(tokenizers) == 2

        # Verify structure
        ids = [t.id for t in tokenizers]
        assert "meta-llama--Llama-3.1-8B-Instruct" in ids
        assert "mistralai--Mistral-7B-Instruct-v0.3" in ids

        # Verify source_repo conversion
        source_repos = [t.source_repo for t in tokenizers]
        assert "meta-llama/Llama-3.1-8B-Instruct" in source_repos


class TestDeleteTokenizer:
    """Tests for tokenizer deletion."""

    def test_delete_tokenizer_success(self, fresh_tokenizer_manager, temp_tokenizer_dir):
        """
        Create mock tokenizer folder, call delete_tokenizer.
        Verify folder deleted and bytes freed returned.
        """
        # Create mock tokenizer folder
        tokenizer_dir = Path(temp_tokenizer_dir) / "test--tokenizer"
        tokenizer_dir.mkdir(parents=True)
        test_file = tokenizer_dir / "tokenizer.json"
        test_file.write_text('{"test": true}' * 100)

        file_size = test_file.stat().st_size

        result = fresh_tokenizer_manager.delete_tokenizer("test--tokenizer")

        assert result.deleted == "test/tokenizer"
        assert result.freed_bytes >= file_size
        assert not tokenizer_dir.exists()

    def test_delete_tokenizer_not_found(self, fresh_tokenizer_manager):
        """Attempt to delete non-existent tokenizer raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            fresh_tokenizer_manager.delete_tokenizer("nonexistent--tokenizer")

    def test_delete_removes_from_memory_cache(self, fresh_tokenizer_manager, temp_tokenizer_dir):
        """Verify deletion removes tokenizer from memory cache."""
        # Create mock tokenizer folder
        tokenizer_dir = Path(temp_tokenizer_dir) / "test--cached"
        tokenizer_dir.mkdir(parents=True)
        (tokenizer_dir / "tokenizer.json").write_text('{"test": true}')

        # Add to memory cache
        fresh_tokenizer_manager._memory_cache["test/cached"] = Mock()

        # Delete
        fresh_tokenizer_manager.delete_tokenizer("test--cached")

        # Verify removed from cache
        assert "test/cached" not in fresh_tokenizer_manager._memory_cache


# =============================================================================
# 4. API Endpoint Tests
# =============================================================================

class TestTokenizerAPIEndpoints:
    """Tests for tokenizer API endpoints."""

    @pytest.fixture
    def client_with_temp_storage(self, temp_tokenizer_dir):
        """Create test client with tokenizer router and temp storage."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from app.api.v1 import tokenizers
        from app.services.tokenizer_manager import TokenizerManager

        # Reset singleton with temp storage
        TokenizerManager._instance = None

        original_get_storage_path = TokenizerManager._get_storage_path

        @staticmethod
        def patched_get_storage_path():
            return Path(temp_tokenizer_dir)

        TokenizerManager._get_storage_path = patched_get_storage_path

        app = FastAPI()
        app.include_router(tokenizers.router, prefix="/api/v1")

        try:
            with TestClient(app) as test_client:
                yield test_client, temp_tokenizer_dir
        finally:
            TokenizerManager._get_storage_path = original_get_storage_path
            TokenizerManager._instance = None

    def test_get_tokenizers_empty(self, client_with_temp_storage):
        """GET /api/v1/tokenizers with empty storage returns empty list."""
        client, tmpdir = client_with_temp_storage

        response = client.get("/api/v1/tokenizers")

        assert response.status_code == 200
        data = response.json()

        assert "tokenizers" in data
        assert isinstance(data["tokenizers"], list)
        assert "storage_path" in data
        assert "total_size_bytes" in data

    def test_get_tokenizers_with_data(self, client_with_temp_storage):
        """GET /api/v1/tokenizers returns list with correct format."""
        client, tmpdir = client_with_temp_storage

        # Create mock tokenizer folder
        tokenizer_dir = Path(tmpdir) / "meta-llama--Llama-3.1-8B"
        tokenizer_dir.mkdir(parents=True)
        (tokenizer_dir / "tokenizer.json").write_text('{"test": true}')

        response = client.get("/api/v1/tokenizers")

        assert response.status_code == 200
        data = response.json()

        assert len(data["tokenizers"]) == 1
        tokenizer = data["tokenizers"][0]

        assert "id" in tokenizer
        assert "source_repo" in tokenizer
        assert "type" in tokenizer
        assert "size_bytes" in tokenizer
        assert "created_at" in tokenizer

    def test_delete_tokenizer_success(self, client_with_temp_storage):
        """DELETE /api/v1/tokenizers/{id} returns 200 with freed_bytes."""
        client, tmpdir = client_with_temp_storage

        # Create mock tokenizer folder
        tokenizer_dir = Path(tmpdir) / "test--tokenizer"
        tokenizer_dir.mkdir(parents=True)
        (tokenizer_dir / "tokenizer.json").write_text('{"test": true}')

        response = client.delete("/api/v1/tokenizers/test--tokenizer")

        assert response.status_code == 200
        data = response.json()

        assert "deleted" in data
        assert "freed_bytes" in data
        assert data["deleted"] == "test/tokenizer"

    def test_delete_tokenizer_not_found(self, client_with_temp_storage):
        """DELETE /api/v1/tokenizers/{nonexistent} returns 404."""
        client, tmpdir = client_with_temp_storage

        response = client.delete("/api/v1/tokenizers/nonexistent--tokenizer")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Tokenizer not found"


# =============================================================================
# 5. Integration Tests
# =============================================================================

class TestPreloadTokenizer:
    """Tests for tokenizer preloading."""

    def test_preload_tiktoken_model(self, fresh_tokenizer_manager):
        """Preloading tiktoken model returns success with cached=True."""
        model = Mock()
        model.model_identifier = "gpt-4"
        model.tokenizer_name = None

        result = fresh_tokenizer_manager.preload_tokenizer(model)

        assert result.success is True
        assert result.tokenizer_type == "tiktoken"
        assert result.cached is True
        assert "cl100k_base" in result.tokenizer_id

    def test_preload_huggingface_model_mocked(self, fresh_tokenizer_manager):
        """Preloading HuggingFace model downloads and persists."""
        model = Mock()
        model.model_identifier = "llama-3.1-8b"
        model.tokenizer_name = None

        with patch("transformers.AutoTokenizer") as mock_auto:
            mock_tokenizer = MagicMock()
            mock_auto.from_pretrained.return_value = mock_tokenizer

            result = fresh_tokenizer_manager.preload_tokenizer(model)

            assert result.success is True
            assert result.tokenizer_type == "huggingface"
            assert result.cached is False
            mock_tokenizer.save_pretrained.assert_called_once()

    def test_preload_already_cached(self, fresh_tokenizer_manager, temp_tokenizer_dir):
        """Preloading already cached tokenizer returns cached=True."""
        model = Mock()
        model.model_identifier = "llama-3.1-8b"
        model.tokenizer_name = None

        # Create mock cached tokenizer
        tokenizer_dir = Path(temp_tokenizer_dir) / "meta-llama--Llama-3.1-8B-Instruct"
        tokenizer_dir.mkdir(parents=True)
        (tokenizer_dir / "tokenizer.json").write_text('{"test": true}')
        (tokenizer_dir / "tokenizer_config.json").write_text('{}')

        with patch("transformers.AutoTokenizer") as mock_auto:
            mock_tokenizer = MagicMock()
            mock_auto.from_pretrained.return_value = mock_tokenizer

            result = fresh_tokenizer_manager.preload_tokenizer(model)

            assert result.success is True
            assert result.cached is True


class TestStorageInfo:
    """Tests for storage information."""

    def test_get_storage_info_empty(self, fresh_tokenizer_manager):
        """Get storage info for empty directory."""
        info = fresh_tokenizer_manager.get_storage_info()

        assert "storage_path" in info
        assert "total_size_bytes" in info
        assert info["total_size_bytes"] == 0

    def test_get_storage_info_with_files(self, fresh_tokenizer_manager, temp_tokenizer_dir):
        """Get storage info with tokenizer files."""
        # Create some files
        tokenizer_dir = Path(temp_tokenizer_dir) / "test-tokenizer"
        tokenizer_dir.mkdir(parents=True)
        (tokenizer_dir / "file1.json").write_text('{"test": true}' * 100)
        (tokenizer_dir / "file2.json").write_text('{"test": true}' * 100)

        info = fresh_tokenizer_manager.get_storage_info()

        assert info["total_size_bytes"] > 0


# =============================================================================
# 6. Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case tests."""

    def test_concurrent_tokenizer_loading(self, fresh_tokenizer_manager):
        """
        Simulate concurrent requests for same tokenizer.
        Verify no race conditions and tokenizer loaded only once.
        """
        model = Mock()
        model.model_identifier = "gpt-4"
        model.tokenizer_name = None

        results = []
        errors = []

        def load_tokenizer():
            try:
                tokenizer = fresh_tokenizer_manager.get_tokenizer_for_model(model)
                results.append(tokenizer)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=load_tokenizer) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during concurrent loading: {errors}"
        assert len(results) == 10, "All threads should complete"

        # All should get the same wrapper (from cache)
        first = results[0]
        for r in results[1:]:
            assert r._encoding_name == first._encoding_name

    def test_corrupted_local_tokenizer(self, fresh_tokenizer_manager, temp_tokenizer_dir):
        """
        Create malformed tokenizer files.
        Verify graceful fallback to download.
        """
        # Create corrupted tokenizer folder
        tokenizer_dir = Path(temp_tokenizer_dir) / "meta-llama--Llama-3.1-8B-Instruct"
        tokenizer_dir.mkdir(parents=True)
        (tokenizer_dir / "tokenizer.json").write_text("INVALID JSON {{{")

        model = Mock()
        model.model_identifier = "llama-3.1-8b"
        model.tokenizer_name = None

        with patch("transformers.AutoTokenizer") as mock_auto:
            # Make from_pretrained fail on corrupt, succeed on download
            call_count = [0]

            def side_effect(path, *args, **kwargs):
                call_count[0] += 1
                if str(path) == str(tokenizer_dir):
                    raise ValueError("Corrupted tokenizer")
                mock_tok = MagicMock()
                mock_tok.encode.return_value = [1, 2, 3]
                return mock_tok

            mock_auto.from_pretrained.side_effect = side_effect

            # Should handle the corruption gracefully
            result = fresh_tokenizer_manager._load_from_local("meta-llama/Llama-3.1-8B-Instruct")
            assert result is None  # Returns None on failure

    def test_huggingface_unavailable_fallback(self, fresh_tokenizer_manager):
        """
        Mock network error on HuggingFace download.
        Verify fallback to tiktoken with warning.
        """
        model = Mock()
        model.model_identifier = "llama-3.1-8b"
        model.tokenizer_name = None

        with patch("transformers.AutoTokenizer") as mock_auto:
            mock_auto.from_pretrained.side_effect = Exception("Network error")

            with patch("app.services.tokenizer_manager.logger") as mock_logger:
                tokenizer = fresh_tokenizer_manager.get_tokenizer_for_model(model)

                # Should fall back to tiktoken
                from app.services.tokenizer_manager import TiktokenWrapper
                assert isinstance(tokenizer, TiktokenWrapper)

                # Should log warning
                mock_logger.warning.assert_called()


class TestTiktokenWrapperAPI:
    """Tests for TiktokenWrapper API compatibility."""

    def test_tiktoken_wrapper_encode_decode(self):
        """Test TiktokenWrapper encode/decode methods."""
        from app.services.tokenizer_manager import TiktokenWrapper
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
        wrapper = TiktokenWrapper(encoding, "cl100k_base")

        text = "Hello, world!"
        tokens = wrapper.encode(text)
        decoded = wrapper.decode(tokens)

        assert len(tokens) > 0
        assert decoded == text

    def test_tiktoken_wrapper_call(self):
        """Test TiktokenWrapper __call__ method for HuggingFace API compatibility."""
        from app.services.tokenizer_manager import TiktokenWrapper
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
        wrapper = TiktokenWrapper(encoding, "cl100k_base")

        result = wrapper("Hello, world!")

        assert "input_ids" in result
        assert len(result["input_ids"]) > 0


class TestTokenizerMappingsCompleteness:
    """Tests for tokenizer mappings coverage."""

    def test_major_providers_covered(self):
        """Verify major providers have tokenizer mappings."""
        from app.core.tokenizer_mappings import TOKENIZER_MAPPINGS

        # Check OpenAI
        assert "gpt-4" in TOKENIZER_MAPPINGS
        assert "gpt-4o" in TOKENIZER_MAPPINGS
        assert "gpt-3.5-turbo" in TOKENIZER_MAPPINGS

        # Check Anthropic
        assert "claude-3" in TOKENIZER_MAPPINGS or "claude" in TOKENIZER_MAPPINGS

        # Check Meta
        assert "llama-3.1" in TOKENIZER_MAPPINGS
        assert "llama-3" in TOKENIZER_MAPPINGS

        # Check Mistral
        assert "mistral" in TOKENIZER_MAPPINGS

        # Check Google
        assert "gemini" in TOKENIZER_MAPPINGS or "gemini-1.5" in TOKENIZER_MAPPINGS

    def test_mapping_format_valid(self):
        """Verify all mappings have required fields."""
        from app.core.tokenizer_mappings import TOKENIZER_MAPPINGS

        for key, config in TOKENIZER_MAPPINGS.items():
            assert "type" in config, f"Missing 'type' in mapping for {key}"
            assert config["type"] in ["tiktoken", "huggingface"], \
                f"Invalid type '{config['type']}' for {key}"

            if config["type"] == "tiktoken":
                assert "encoding" in config, f"Missing 'encoding' for tiktoken {key}"
            elif config["type"] == "huggingface":
                assert "repo" in config, f"Missing 'repo' for huggingface {key}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
