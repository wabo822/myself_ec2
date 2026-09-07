from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")

    with patch("backend.rag.KnowledgeBase.load", return_value=None):
        from backend import app as app_module

        monkeypatch.setattr(app_module, "HEALTHCHECK_STATE_FILE", tmp_path / "healthcheck-state.json")
        app_module.knowledge_base.document_count = 1
        app_module.knowledge_base.chunk_count = 3
        with TestClient(app_module.app) as test_client:
            yield test_client
