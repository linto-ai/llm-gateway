"""Chat completions API tests - Sprint 062.

Tests for:
1. resolve_system_prompt() unit tests
2. ChatCompletionRequest / ChatMessage / ChatContext schema validation
3. POST /api/v1/chat/completions endpoint integration (mocked DB + provider)
"""
import json
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import ValidationError


# =============================================================================
# 1. Unit Tests: resolve_system_prompt()
# =============================================================================


class TestResolveSystemPrompt:
    """Test the resolve_system_prompt function directly."""

    def _resolve(self, template, **kwargs):
        from app.api.v1.chat import resolve_system_prompt
        from app.schemas.chat import ChatContext
        ctx = ChatContext(**kwargs)
        return resolve_system_prompt(template, ctx)

    def test_transcript_placeholder_replaced(self):
        result = self._resolve(
            "Here is the transcript:\n{transcript}",
            transcript="Alice: Hello\nBob: Hi",
        )
        assert "Alice: Hello\nBob: Hi" in result
        assert "{transcript}" not in result

    def test_summary_section_included_when_summary_present(self):
        result = self._resolve(
            "Transcript:\n{transcript}\n\n{summary_section}",
            transcript="Some text",
            summary="A short summary.",
        )
        assert "A short summary." in result
        assert "{summary_section}" not in result

    def test_summary_section_removed_when_summary_none(self):
        result = self._resolve(
            "Transcript:\n{transcript}\n\n{summary_section}",
            transcript="Some text",
            summary=None,
        )
        assert "{summary_section}" not in result

    def test_summary_section_removed_when_summary_empty(self):
        result = self._resolve(
            "Before\n{summary_section}\nAfter",
            transcript="Some text",
            summary="",
        )
        # Empty string is falsy, so summary_section should be removed
        assert "{summary_section}" not in result
        assert "Before" in result
        assert "After" in result

    def test_conversation_name_from_metadata(self):
        result = self._resolve(
            "You are analyzing: {conversation_name}",
            transcript="text",
            metadata={"conversation_name": "Team Standup"},
        )
        assert "Team Standup" in result
        assert "{conversation_name}" not in result

    def test_multiple_placeholders_replaced_in_one_pass(self):
        template = (
            "Conversation: {conversation_name}\n"
            "Date: {date}\n"
            "Transcript:\n{transcript}\n"
            "{summary_section}"
        )
        result = self._resolve(
            template,
            transcript="Alice: hi",
            summary="Short summary",
            metadata={"conversation_name": "Weekly", "date": "2026-02-24"},
        )
        assert "Weekly" in result
        assert "2026-02-24" in result
        assert "Alice: hi" in result
        assert "Short summary" in result
        assert "{conversation_name}" not in result
        assert "{date}" not in result
        assert "{transcript}" not in result
        assert "{summary_section}" not in result

    def test_missing_metadata_key_stays_as_is(self):
        result = self._resolve(
            "Hello {nonexistent} world",
            transcript="text",
        )
        # No metadata provided, so {nonexistent} should remain untouched
        assert "{nonexistent}" in result

    def test_metadata_with_none_value(self):
        result = self._resolve(
            "Name: {conversation_name}",
            transcript="text",
            metadata={"conversation_name": None},
        )
        # None values should become empty string
        assert "Name: " in result
        assert "{conversation_name}" not in result


# =============================================================================
# 2. Schema Validation Tests
# =============================================================================


class TestChatSchemas:
    """Test Pydantic schemas for chat completions."""

    def test_valid_request_parses(self):
        from app.schemas.chat import ChatCompletionRequest
        req = ChatCompletionRequest(
            flavor_id=uuid4(),
            messages=[{"role": "user", "content": "Hello"}],
            context={"transcript": "Alice: Hi"},
            max_tokens=4096,
        )
        assert len(req.messages) == 1
        assert req.messages[0].role == "user"
        assert req.context.transcript == "Alice: Hi"
        assert req.max_tokens == 4096

    def test_missing_flavor_id_raises(self):
        from app.schemas.chat import ChatCompletionRequest
        with pytest.raises(ValidationError) as exc:
            ChatCompletionRequest(
                messages=[{"role": "user", "content": "Hello"}],
                context={"transcript": "text"},
            )
        assert "flavor_id" in str(exc.value)

    def test_empty_messages_raises(self):
        from app.schemas.chat import ChatCompletionRequest
        with pytest.raises(ValidationError) as exc:
            ChatCompletionRequest(
                flavor_id=uuid4(),
                messages=[],
                context={"transcript": "text"},
            )
        errors_str = str(exc.value)
        assert "messages" in errors_str.lower() or "min_length" in errors_str.lower()

    def test_system_role_rejected(self):
        from app.schemas.chat import ChatMessage
        with pytest.raises(ValidationError) as exc:
            ChatMessage(role="system", content="You are a bot")
        assert "role" in str(exc.value).lower() or "pattern" in str(exc.value).lower()

    def test_empty_content_rejected(self):
        from app.schemas.chat import ChatMessage
        with pytest.raises(ValidationError) as exc:
            ChatMessage(role="user", content="")
        errors_str = str(exc.value)
        assert "content" in errors_str.lower() or "min_length" in errors_str.lower()

    def test_missing_transcript_raises(self):
        from app.schemas.chat import ChatCompletionRequest
        with pytest.raises(ValidationError) as exc:
            ChatCompletionRequest(
                flavor_id=uuid4(),
                messages=[{"role": "user", "content": "Hi"}],
                context={},
            )
        assert "transcript" in str(exc.value)

    def test_optional_fields_can_be_omitted(self):
        from app.schemas.chat import ChatCompletionRequest
        req = ChatCompletionRequest(
            flavor_id=uuid4(),
            messages=[{"role": "user", "content": "Hi"}],
            context={"transcript": "text"},
        )
        assert req.max_tokens is None
        assert req.context.summary is None
        assert req.context.metadata is None

    def test_max_tokens_zero_raises(self):
        from app.schemas.chat import ChatCompletionRequest
        with pytest.raises(ValidationError) as exc:
            ChatCompletionRequest(
                flavor_id=uuid4(),
                messages=[{"role": "user", "content": "Hi"}],
                context={"transcript": "text"},
                max_tokens=0,
            )
        errors_str = str(exc.value)
        assert "max_tokens" in errors_str.lower() or "greater" in errors_str.lower()

    def test_max_tokens_negative_raises(self):
        from app.schemas.chat import ChatCompletionRequest
        with pytest.raises(ValidationError):
            ChatCompletionRequest(
                flavor_id=uuid4(),
                messages=[{"role": "user", "content": "Hi"}],
                context={"transcript": "text"},
                max_tokens=-1,
            )

    def test_assistant_role_accepted(self):
        from app.schemas.chat import ChatMessage
        msg = ChatMessage(role="assistant", content="Sure, here is the info.")
        assert msg.role == "assistant"

    def test_user_role_accepted(self):
        from app.schemas.chat import ChatMessage
        msg = ChatMessage(role="user", content="What happened?")
        assert msg.role == "user"

    def test_invalid_role_rejected(self):
        from app.schemas.chat import ChatMessage
        with pytest.raises(ValidationError):
            ChatMessage(role="tool", content="Tool output")

    def test_context_with_summary_and_metadata(self):
        from app.schemas.chat import ChatContext
        ctx = ChatContext(
            transcript="Full transcript",
            summary="Brief summary",
            metadata={"conversation_name": "Standup", "date": "2026-02-24"},
        )
        assert ctx.transcript == "Full transcript"
        assert ctx.summary == "Brief summary"
        assert ctx.metadata["conversation_name"] == "Standup"

    def test_chat_token_usage_schema(self):
        from app.schemas.chat import ChatTokenUsage
        usage = ChatTokenUsage(
            prompt_tokens=1000,
            completion_tokens=42,
            total_tokens=1042,
        )
        assert usage.prompt_tokens == 1000
        assert usage.total_tokens == 1042

    def test_chat_token_event_schema(self):
        from app.schemas.chat import ChatTokenEvent
        evt = ChatTokenEvent(content="Hello")
        assert evt.content == "Hello"

    def test_chat_done_event_schema(self):
        from app.schemas.chat import ChatDoneEvent
        evt = ChatDoneEvent(
            usage={"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}
        )
        assert evt.usage.total_tokens == 120

    def test_chat_error_event_schema(self):
        from app.schemas.chat import ChatErrorEvent
        evt = ChatErrorEvent(error="Something went wrong")
        assert evt.error == "Something went wrong"

    def test_empty_transcript_rejected(self):
        from app.schemas.chat import ChatContext
        with pytest.raises(ValidationError):
            ChatContext(transcript="")

    def test_multiple_messages_accepted(self):
        from app.schemas.chat import ChatCompletionRequest
        req = ChatCompletionRequest(
            flavor_id=uuid4(),
            messages=[
                {"role": "user", "content": "Who attended?"},
                {"role": "assistant", "content": "Alice and Bob."},
                {"role": "user", "content": "What did they discuss?"},
            ],
            context={"transcript": "Alice: Let's discuss the plan."},
        )
        assert len(req.messages) == 3

    def test_flavor_id_must_be_uuid(self):
        from app.schemas.chat import ChatCompletionRequest
        with pytest.raises(ValidationError):
            ChatCompletionRequest(
                flavor_id="not-a-uuid",
                messages=[{"role": "user", "content": "Hi"}],
                context={"transcript": "text"},
            )


# =============================================================================
# 3. Endpoint Integration Tests (fully mocked DB + provider)
# =============================================================================


def _make_mock_flavor(
    flavor_id=None,
    system_prompt="You are a helpful assistant.\n{transcript}\n{summary_section}",
    model_identifier="gpt-test",
    api_base_url="https://api.test.com/v1",
    provider_id=None,
    max_generation_length=4096,
    temperature=0.7,
    top_p=0.9,
):
    """Create a mock ServiceFlavor with nested model and provider."""
    fid = flavor_id or uuid4()
    pid = provider_id or uuid4()

    mock_provider = MagicMock()
    mock_provider.id = pid
    mock_provider.api_base_url = api_base_url

    mock_model = MagicMock()
    mock_model.provider = mock_provider
    mock_model.provider_id = pid
    mock_model.model_name = "test-model"
    mock_model.model_identifier = model_identifier
    mock_model.max_generation_length = max_generation_length

    mock_flavor = MagicMock()
    mock_flavor.id = fid
    mock_flavor.model = mock_model
    mock_flavor.temperature = temperature
    mock_flavor.top_p = top_p
    mock_flavor.prompt_system_content = system_prompt

    return mock_flavor


class TestChatEndpoint:
    """Integration tests for POST /api/v1/chat/completions.

    Uses a minimal FastAPI app with the chat router. All DB queries and
    provider calls are mocked to avoid SQLite/JSONB incompatibility and
    external dependencies.
    """

    @pytest.fixture
    def chat_app(self):
        """Create a minimal FastAPI app with just the chat router."""
        from fastapi import FastAPI
        from app.api.v1 import chat as chat_api
        app = FastAPI()
        app.include_router(chat_api.router, prefix="/api/v1")
        return app

    @pytest.fixture
    def mock_flavor(self):
        return _make_mock_flavor()

    @pytest.fixture
    async def client(self, chat_app):
        """Create httpx async client with mocked DB dependency."""
        import httpx
        from app.api.dependencies import get_db

        mock_db = AsyncMock()

        async def override_get_db():
            yield mock_db

        chat_app.dependency_overrides[get_db] = override_get_db

        transport = httpx.ASGITransport(app=chat_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

        chat_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_valid_request_returns_sse(self, client, mock_flavor):
        """Valid request returns 200 with text/event-stream content type."""

        async def mock_stream_chat(messages, **kwargs):
            yield "Hello", None
            yield " world", None
            yield "", {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}

        with patch(
            "app.api.v1.chat._load_flavor_with_relations",
            new_callable=AsyncMock,
            return_value=mock_flavor,
        ), patch(
            "app.api.v1.chat.OpenAIAdapter",
        ) as MockAdapter, patch(
            "app.api.v1.chat.provider_service",
        ) as mock_ps:
            MockAdapter.return_value.stream_chat = mock_stream_chat
            mock_ps.get_decrypted_api_key = AsyncMock(return_value="sk-decrypted")

            resp = await client.post(
                "/api/v1/chat/completions",
                json={
                    "flavor_id": str(mock_flavor.id),
                    "messages": [{"role": "user", "content": "What was discussed?"}],
                    "context": {
                        "transcript": "Alice: Let's discuss the plan.",
                    },
                },
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

        body = resp.text
        assert "event: token" in body
        assert "event: done" in body

    @pytest.mark.asyncio
    async def test_nonexistent_flavor_returns_404(self, client):
        """Request with non-existent flavor_id returns 404."""
        with patch(
            "app.api.v1.chat._load_flavor_with_relations",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.post(
                "/api/v1/chat/completions",
                json={
                    "flavor_id": str(uuid4()),
                    "messages": [{"role": "user", "content": "Hello"}],
                    "context": {"transcript": "text"},
                },
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_body_returns_422(self, client):
        """Malformed request body returns 422."""
        resp = await client.post(
            "/api/v1/chat/completions",
            json={"bad_field": "value"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_flavor_without_system_prompt_returns_400(self, client):
        """Flavor with no system prompt template returns 400."""
        flavor_no_prompt = _make_mock_flavor(system_prompt=None)

        with patch(
            "app.api.v1.chat._load_flavor_with_relations",
            new_callable=AsyncMock,
            return_value=flavor_no_prompt,
        ), patch(
            "app.api.v1.chat.provider_service",
        ) as mock_ps:
            mock_ps.get_decrypted_api_key = AsyncMock(return_value="sk-decrypted")

            resp = await client.post(
                "/api/v1/chat/completions",
                json={
                    "flavor_id": str(flavor_no_prompt.id),
                    "messages": [{"role": "user", "content": "Hello"}],
                    "context": {"transcript": "text"},
                },
            )

        assert resp.status_code == 400
        assert "system prompt" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_flavor_with_empty_system_prompt_returns_400(self, client):
        """Flavor with empty string system prompt returns 400."""
        flavor_empty_prompt = _make_mock_flavor(system_prompt="")

        with patch(
            "app.api.v1.chat._load_flavor_with_relations",
            new_callable=AsyncMock,
            return_value=flavor_empty_prompt,
        ), patch(
            "app.api.v1.chat.provider_service",
        ) as mock_ps:
            mock_ps.get_decrypted_api_key = AsyncMock(return_value="sk-decrypted")

            resp = await client.post(
                "/api/v1/chat/completions",
                json={
                    "flavor_id": str(flavor_empty_prompt.id),
                    "messages": [{"role": "user", "content": "Hello"}],
                    "context": {"transcript": "text"},
                },
            )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_sse_stream_contains_token_and_done_events(self, client, mock_flavor):
        """Verify SSE format: event: token + data, event: done + usage."""

        async def mock_stream_chat(messages, **kwargs):
            yield "The", None
            yield " meeting", None
            yield "", {"prompt_tokens": 1200, "completion_tokens": 42, "total_tokens": 1242}

        with patch(
            "app.api.v1.chat._load_flavor_with_relations",
            new_callable=AsyncMock,
            return_value=mock_flavor,
        ), patch(
            "app.api.v1.chat.OpenAIAdapter",
        ) as MockAdapter, patch(
            "app.api.v1.chat.provider_service",
        ) as mock_ps:
            MockAdapter.return_value.stream_chat = mock_stream_chat
            mock_ps.get_decrypted_api_key = AsyncMock(return_value="sk-key")

            resp = await client.post(
                "/api/v1/chat/completions",
                json={
                    "flavor_id": str(mock_flavor.id),
                    "messages": [{"role": "user", "content": "Summary?"}],
                    "context": {"transcript": "Alice: Hello"},
                },
            )

        body = resp.text
        # Parse SSE events
        events = []
        current_event = None
        for line in body.split("\n"):
            if line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: "):
                events.append((current_event, line[6:]))
                current_event = None

        token_events = [e for e in events if e[0] == "token"]
        done_events = [e for e in events if e[0] == "done"]

        assert len(token_events) >= 1, "Expected at least one token event"
        assert len(done_events) == 1, "Expected exactly one done event"

        done_data = json.loads(done_events[0][1])
        assert "usage" in done_data
        assert done_data["usage"]["total_tokens"] == 1242

    @pytest.mark.asyncio
    async def test_empty_messages_returns_422(self, client):
        """Empty messages array returns 422."""
        resp = await client.post(
            "/api/v1/chat/completions",
            json={
                "flavor_id": str(uuid4()),
                "messages": [],
                "context": {"transcript": "text"},
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_system_role_in_messages_returns_422(self, client):
        """Message with role 'system' in the messages array returns 422."""
        resp = await client.post(
            "/api/v1/chat/completions",
            json={
                "flavor_id": str(uuid4()),
                "messages": [{"role": "system", "content": "You are a bot"}],
                "context": {"transcript": "text"},
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_flavor_with_no_model_returns_404(self, client):
        """Flavor found but with no model relation returns 404."""
        flavor_no_model = _make_mock_flavor()
        flavor_no_model.model = None

        with patch(
            "app.api.v1.chat._load_flavor_with_relations",
            new_callable=AsyncMock,
            return_value=flavor_no_model,
        ):
            resp = await client.post(
                "/api/v1/chat/completions",
                json={
                    "flavor_id": str(flavor_no_model.id),
                    "messages": [{"role": "user", "content": "Hello"}],
                    "context": {"transcript": "text"},
                },
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_flavor_with_no_provider_returns_404(self, client):
        """Flavor with model but no provider returns 404."""
        flavor_no_provider = _make_mock_flavor()
        flavor_no_provider.model.provider = None

        with patch(
            "app.api.v1.chat._load_flavor_with_relations",
            new_callable=AsyncMock,
            return_value=flavor_no_provider,
        ):
            resp = await client.post(
                "/api/v1/chat/completions",
                json={
                    "flavor_id": str(flavor_no_provider.id),
                    "messages": [{"role": "user", "content": "Hello"}],
                    "context": {"transcript": "text"},
                },
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_failed_api_key_decryption_returns_500(self, client, mock_flavor):
        """Failed API key decryption returns 500."""
        with patch(
            "app.api.v1.chat._load_flavor_with_relations",
            new_callable=AsyncMock,
            return_value=mock_flavor,
        ), patch(
            "app.api.v1.chat.provider_service",
        ) as mock_ps:
            mock_ps.get_decrypted_api_key = AsyncMock(return_value=None)

            resp = await client.post(
                "/api/v1/chat/completions",
                json={
                    "flavor_id": str(mock_flavor.id),
                    "messages": [{"role": "user", "content": "Hello"}],
                    "context": {"transcript": "text"},
                },
            )
        assert resp.status_code == 500

    @pytest.mark.asyncio
    async def test_streaming_error_yields_error_event(self, client, mock_flavor):
        """Provider error during streaming yields SSE error event."""

        async def mock_stream_chat_error(messages, **kwargs):
            raise RuntimeError("Provider connection failed")
            # Make it a generator
            yield  # pragma: no cover

        with patch(
            "app.api.v1.chat._load_flavor_with_relations",
            new_callable=AsyncMock,
            return_value=mock_flavor,
        ), patch(
            "app.api.v1.chat.OpenAIAdapter",
        ) as MockAdapter, patch(
            "app.api.v1.chat.provider_service",
        ) as mock_ps:
            MockAdapter.return_value.stream_chat = mock_stream_chat_error
            mock_ps.get_decrypted_api_key = AsyncMock(return_value="sk-key")

            resp = await client.post(
                "/api/v1/chat/completions",
                json={
                    "flavor_id": str(mock_flavor.id),
                    "messages": [{"role": "user", "content": "Hello"}],
                    "context": {"transcript": "text"},
                },
            )

        # Streaming response returns 200 but contains error event
        assert resp.status_code == 200
        body = resp.text
        assert "event: error" in body
        assert "Provider connection failed" in body

    @pytest.mark.asyncio
    async def test_context_with_summary_injected_into_prompt(self, client):
        """Verify summary context is passed through to the resolved prompt."""
        flavor = _make_mock_flavor(
            system_prompt="Transcript:\n{transcript}\n\nSummary:\n{summary_section}",
        )

        captured_messages = []

        async def mock_stream_chat(messages, **kwargs):
            captured_messages.extend(messages)
            yield "OK", None
            yield "", {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6}

        with patch(
            "app.api.v1.chat._load_flavor_with_relations",
            new_callable=AsyncMock,
            return_value=flavor,
        ), patch(
            "app.api.v1.chat.OpenAIAdapter",
        ) as MockAdapter, patch(
            "app.api.v1.chat.provider_service",
        ) as mock_ps:
            MockAdapter.return_value.stream_chat = mock_stream_chat
            mock_ps.get_decrypted_api_key = AsyncMock(return_value="sk-key")

            await client.post(
                "/api/v1/chat/completions",
                json={
                    "flavor_id": str(flavor.id),
                    "messages": [{"role": "user", "content": "Summarize"}],
                    "context": {
                        "transcript": "Alice: Hello everyone",
                        "summary": "Meeting about Q1 results",
                    },
                },
            )

        # Verify the system prompt was resolved correctly
        assert len(captured_messages) >= 2
        system_msg = captured_messages[0]
        assert system_msg["role"] == "system"
        assert "Alice: Hello everyone" in system_msg["content"]
        assert "Meeting about Q1 results" in system_msg["content"]

    @pytest.mark.asyncio
    async def test_missing_context_returns_422(self, client):
        """Request without context field returns 422."""
        resp = await client.post(
            "/api/v1/chat/completions",
            json={
                "flavor_id": str(uuid4()),
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_transcript_in_context_returns_422(self, client):
        """Context without transcript returns 422."""
        resp = await client.post(
            "/api/v1/chat/completions",
            json={
                "flavor_id": str(uuid4()),
                "messages": [{"role": "user", "content": "Hello"}],
                "context": {"summary": "no transcript"},
            },
        )
        assert resp.status_code == 422
