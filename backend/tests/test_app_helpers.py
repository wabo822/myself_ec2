from __future__ import annotations

import pytest

from backend import app as app_module


class TestCleanAnswerContent:
    def test_strips_think_tags(self) -> None:
        cleaned = app_module._clean_answer_content("<think>reasoning</think>Hello")
        assert cleaned == "Hello"

    def test_strips_multiline_think(self) -> None:
        cleaned = app_module._clean_answer_content(
            "<think>line1\nline2\nline3</think>\n  final answer"
        )
        assert cleaned == "final answer"

    def test_passthrough_without_think(self) -> None:
        assert app_module._clean_answer_content("plain answer") == "plain answer"

    def test_falls_back_to_original_when_only_think(self) -> None:
        assert app_module._clean_answer_content("<think>only</think>") == "<think>only</think>"


class TestLLMProvider:
    @pytest.mark.parametrize(
        ("env_value", "expected"),
        [
            ("openai", "openai_compatible"),
            ("openai-compatible", "openai_compatible"),
            ("compatible", "openai_compatible"),
            ("claude", "anthropic"),
            ("anthropic", "anthropic"),
            ("", "openai_compatible"),
            ("OpenAI", "openai_compatible"),
        ],
    )
    def test_alias_resolution(self, monkeypatch, env_value, expected) -> None:
        monkeypatch.setenv("LLM_PROVIDER", env_value)
        assert app_module._llm_provider() == expected


class TestBuildChatUrl:
    def test_uses_full_url_when_set(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_CHAT_COMPLETIONS_URL", "https://api.example/v1/chat")
        monkeypatch.setenv("LLM_API_BASE_URL", "")
        assert app_module._build_chat_url() == "https://api.example/v1/chat"

    def test_builds_from_base_for_openai(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.delenv("LLM_CHAT_COMPLETIONS_URL", raising=False)
        monkeypatch.setenv("LLM_API_BASE_URL", "https://api.example/v1/")
        monkeypatch.delenv("LLM_API_PATH", raising=False)
        assert app_module._build_chat_url() == "https://api.example/v1/chat/completions"

    def test_builds_from_base_for_anthropic(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.delenv("LLM_MESSAGES_URL", raising=False)
        monkeypatch.setenv("LLM_API_BASE_URL", "https://api.anthropic.com/v1")
        monkeypatch.delenv("LLM_API_PATH", raising=False)
        assert app_module._build_chat_url() == "https://api.anthropic.com/v1/messages"

    def test_returns_empty_when_unconfigured(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.delenv("LLM_CHAT_COMPLETIONS_URL", raising=False)
        monkeypatch.setenv("LLM_API_BASE_URL", "")
        assert app_module._build_chat_url() == ""


class TestLLMIsConfigured:
    def test_true_when_all_set(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_API_KEY", "k")
        monkeypatch.setenv("LLM_MODEL", "m")
        monkeypatch.setenv("LLM_API_BASE_URL", "https://api.example/v1")
        assert app_module.llm_is_configured() is True

    def test_false_without_key(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_API_KEY", "")
        monkeypatch.setenv("LLM_MODEL", "m")
        monkeypatch.setenv("LLM_API_BASE_URL", "https://api.example/v1")
        assert app_module.llm_is_configured() is False

    def test_false_for_unsupported_provider(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "made-up-provider")
        monkeypatch.setenv("LLM_API_KEY", "k")
        monkeypatch.setenv("LLM_MODEL", "m")
        monkeypatch.setenv("LLM_API_BASE_URL", "https://api.example/v1")
        assert app_module.llm_is_configured() is False


class TestBuildHeaders:
    def test_anthropic_uses_x_api_key(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("LLM_API_KEY", "secret")
        headers = app_module._build_headers()
        assert headers["x-api-key"] == "secret"
        assert "anthropic-version" in headers
        assert "Authorization" not in headers

    def test_openai_uses_bearer(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setenv("LLM_API_KEY", "secret")
        monkeypatch.delenv("LLM_API_KEY_HEADER", raising=False)
        monkeypatch.delenv("LLM_API_KEY_PREFIX", raising=False)
        headers = app_module._build_headers()
        assert headers["Authorization"] == "Bearer secret"


class TestHealthcheckState:
    def test_returns_unknown_when_missing(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("HEALTHCHECK_STATE_FILE", str(tmp_path / "missing.json"))
        state = app_module._read_healthcheck_state()
        assert state == {"status": "unknown"}

    def test_reads_state_file(self, monkeypatch, tmp_path) -> None:
        state_file = tmp_path / "state.json"
        state_file.write_text(
            '{"status": "ok", "last_checked_at": "2026-01-01T00:00:00Z", '
            '"consecutive_failures": 0}',
            encoding="utf-8",
        )
        monkeypatch.setenv("HEALTHCHECK_STATE_FILE", str(state_file))
        state = app_module._read_healthcheck_state()
        assert state["status"] == "ok"
        assert state["last_checked_at"] == "2026-01-01T00:00:00Z"
        assert state["consecutive_failures"] == 0

    def test_returns_unknown_for_invalid_json(self, monkeypatch, tmp_path) -> None:
        state_file = tmp_path / "broken.json"
        state_file.write_text("not json{{{", encoding="utf-8")
        monkeypatch.setenv("HEALTHCHECK_STATE_FILE", str(state_file))
        state = app_module._read_healthcheck_state()
        assert state == {"status": "unknown"}
