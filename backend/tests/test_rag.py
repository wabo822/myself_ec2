from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from backend.rag import KnowledgeBase


@pytest.fixture()
def kb(tmp_path: Path) -> KnowledgeBase:
    return KnowledgeBase(knowledge_dir=tmp_path, embedding_model_name="dummy")


class TestChunkText:
    def test_returns_empty_for_blank_text(self, kb: KnowledgeBase) -> None:
        assert kb._chunk_text("source.md", "   \n\n  ") == []

    def test_short_text_becomes_single_chunk(self, kb: KnowledgeBase) -> None:
        chunks = kb._chunk_text("source.md", "first paragraph\nsecond paragraph")
        assert len(chunks) == 1
        assert chunks[0].source == "source.md"
        assert "first paragraph" in chunks[0].text
        assert "second paragraph" in chunks[0].text

    def test_long_paragraph_is_split_with_overlap(self, kb: KnowledgeBase) -> None:
        long_paragraph = "x" * 2000
        chunks = kb._chunk_text("big.md", long_paragraph)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk.text) <= 850

    def test_paragraphs_packed_until_max(self, kb: KnowledgeBase) -> None:
        text = "\n".join(["a" * 400, "b" * 400, "c" * 400])
        chunks = kb._chunk_text("packed.md", text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk.text) <= 850


class TestNormalize:
    def test_normalize_vector_unit_length(self, kb: KnowledgeBase) -> None:
        vector = np.array([3.0, 4.0], dtype=np.float32)
        normalized = kb._normalize_vector(vector)
        assert np.isclose(np.linalg.norm(normalized), 1.0)

    def test_normalize_vector_zero_unchanged(self, kb: KnowledgeBase) -> None:
        vector = np.zeros(4, dtype=np.float32)
        normalized = kb._normalize_vector(vector)
        np.testing.assert_array_equal(normalized, vector)

    def test_normalize_rows_handles_zero_row(self, kb: KnowledgeBase) -> None:
        matrix = np.array([[0.0, 0.0, 0.0], [3.0, 0.0, 4.0]], dtype=np.float32)
        normalized = kb._normalize_rows(matrix)
        np.testing.assert_array_equal(normalized[0], np.array([0.0, 0.0, 0.0]))
        assert np.isclose(np.linalg.norm(normalized[1]), 1.0)


class TestLoadDocuments:
    def test_skips_unsupported_extensions(self, tmp_path: Path) -> None:
        (tmp_path / "good.md").write_text("hello", encoding="utf-8")
        (tmp_path / "ignore.png").write_bytes(b"\x89PNG")
        (tmp_path / "ignore.json").write_text("{}", encoding="utf-8")

        kb = KnowledgeBase(knowledge_dir=tmp_path, embedding_model_name="dummy")
        docs = list(kb._load_documents())
        sources = {source for source, _ in docs}
        assert sources == {"good.md"}

    def test_skips_empty_files(self, tmp_path: Path) -> None:
        (tmp_path / "empty.md").write_text("   \n  ", encoding="utf-8")
        (tmp_path / "real.md").write_text("real content", encoding="utf-8")

        kb = KnowledgeBase(knowledge_dir=tmp_path, embedding_model_name="dummy")
        sources = {source for source, _ in kb._load_documents()}
        assert sources == {"real.md"}


class TestSearch:
    def test_returns_empty_when_not_loaded(self, kb: KnowledgeBase) -> None:
        assert kb.search("anything") == []
