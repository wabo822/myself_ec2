from __future__ import annotations

from unittest.mock import patch

from backend.rag import RetrievedChunk


class TestHealthEndpoint:
    def test_returns_ok(self, client) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["llm_configured"] is True
        assert body["chunk_count"] == 3
        assert "llm_probe" in body

    def test_degraded_when_probe_failed(self, client, monkeypatch, tmp_path) -> None:
        state_file = tmp_path / "state.json"
        state_file.write_text('{"status": "fail"}', encoding="utf-8")
        monkeypatch.setenv("HEALTHCHECK_STATE_FILE", str(state_file))
        response = client.get("/api/health")
        assert response.json()["status"] == "degraded"


class TestChatEndpoint:
    def test_rejects_empty_question(self, client) -> None:
        response = client.post("/api/chat", json={"question": "", "history": []})
        assert response.status_code == 422

    def test_rejects_question_over_limit(self, client) -> None:
        response = client.post(
            "/api/chat",
            json={"question": "x" * 801, "history": []},
        )
        assert response.status_code == 422

    def test_returns_500_when_knowledge_base_empty(self, client) -> None:
        with patch("backend.app.knowledge_base.search", return_value=[]):
            response = client.post("/api/chat", json={"question": "hi", "history": []})
        assert response.status_code == 500
        assert "知识库" in response.json()["detail"]

    def test_returns_answer_when_llm_responds(self, client) -> None:
        retrieved = [
            RetrievedChunk(source="profile.md", text="bio text", snippet="bio", score=0.9),
        ]

        async def fake_generate(question, history, context):
            return "mocked answer"

        with patch("backend.app.knowledge_base.search", return_value=retrieved), patch(
            "backend.app.generate_answer", side_effect=fake_generate
        ):
            response = client.post(
                "/api/chat",
                json={"question": "Who is Jiahan?", "history": []},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "mocked answer"
        assert body["sources"][0]["source"] == "profile.md"
        assert body["sources"][0]["score"] == 0.9


class TestStaticRoutes:
    def test_homepage_serves_html(self, client) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_chinese_homepage_serves_html(self, client) -> None:
        response = client.get("/zh")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_assets_path_traversal_blocked(self, client) -> None:
        response = client.get("/assets/../backend/app.py")
        assert response.status_code == 404
