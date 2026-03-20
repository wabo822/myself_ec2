from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


@dataclass
class RetrievedChunk:
    source: str
    text: str
    snippet: str
    score: float


@dataclass
class _Chunk:
    source: str
    text: str


class KnowledgeBase:
    def __init__(self, knowledge_dir: Path, embedding_model_name: str, embedding_threads: int = 1) -> None:
        self.knowledge_dir = knowledge_dir
        self.embedding_model_name = embedding_model_name
        self.embedding_threads = embedding_threads
        self._model = None
        self._chunks: list[_Chunk] = []
        self._matrix: np.ndarray | None = None
        self.document_count = 0
        self.chunk_count = 0

    def load(self) -> None:
        documents = list(self._load_documents())
        self.document_count = len(documents)

        chunks: list[_Chunk] = []
        for source, text in documents:
            chunks.extend(self._chunk_text(source, text))

        self._chunks = chunks
        self.chunk_count = len(chunks)
        if not chunks:
            self._matrix = None
            return

        model = self._get_model()
        vectors = np.asarray(list(model.embed([chunk.text for chunk in chunks])), dtype=np.float32)
        self._matrix = self._normalize_rows(vectors)

    def search(self, query: str, top_k: int = 4) -> list[RetrievedChunk]:
        if not self._chunks or self._matrix is None:
            return []

        model = self._get_model()
        query_vector = np.asarray(list(model.embed([query]))[0], dtype=np.float32)
        query_vector = self._normalize_vector(query_vector)
        scores = self._matrix @ query_vector
        top_indices = np.argsort(scores)[::-1][:top_k]

        results: list[RetrievedChunk] = []
        for index in top_indices:
            chunk = self._chunks[int(index)]
            score = float(scores[int(index)])
            snippet = chunk.text.strip().replace("\n", " ")
            if len(snippet) > 220:
                snippet = f"{snippet[:217]}..."
            results.append(
                RetrievedChunk(
                    source=chunk.source,
                    text=chunk.text,
                    snippet=snippet,
                    score=score,
                )
            )
        return results

    def _get_model(self):
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(
                model_name=self.embedding_model_name,
                threads=self.embedding_threads,
                lazy_load=False,
            )
        return self._model

    def _normalize_rows(self, matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms

    def _normalize_vector(self, vector: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm

    def _load_documents(self) -> Iterable[tuple[str, str]]:
        for path in sorted(self.knowledge_dir.rglob("*")):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix not in {".md", ".txt", ".pdf"}:
                continue
            text = self._read_file(path, suffix).strip()
            if text:
                yield str(path.relative_to(self.knowledge_dir)), text

    def _read_file(self, path: Path, suffix: str) -> str:
        if suffix in {".md", ".txt"}:
            return path.read_text(encoding="utf-8")

        if suffix == ".pdf":
            try:
                from pypdf import PdfReader

                reader = PdfReader(str(path))
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception:
                return ""

        return ""

    def _chunk_text(self, source: str, text: str) -> list[_Chunk]:
        paragraphs = [item.strip() for item in text.split("\n") if item.strip()]
        if not paragraphs:
            return []

        max_chars = 850
        overlap_chars = 120
        current = ""
        chunks: list[_Chunk] = []

        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
            if len(candidate) <= max_chars:
                current = candidate
                continue

            if current:
                chunks.append(_Chunk(source=source, text=current))
                current = current[-overlap_chars:].strip()

            if len(paragraph) <= max_chars:
                current = f"{current}\n\n{paragraph}".strip() if current else paragraph
                continue

            start = 0
            while start < len(paragraph):
                end = min(start + max_chars, len(paragraph))
                piece = paragraph[start:end].strip()
                if piece:
                    chunks.append(_Chunk(source=source, text=piece))
                start = end if end >= len(paragraph) else max(end - overlap_chars, start + 1)

        if current:
            chunks.append(_Chunk(source=source, text=current))

        return chunks
