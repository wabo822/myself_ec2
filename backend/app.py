from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.rag import KnowledgeBase

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / "backend" / ".env"
load_dotenv(ENV_PATH)


def _build_chat_url() -> str:
    full_url = os.getenv("LLM_CHAT_COMPLETIONS_URL", "").strip()
    if full_url:
        return full_url

    base = os.getenv("LLM_API_BASE_URL", "").strip().rstrip("/")
    path = os.getenv("LLM_API_PATH", "/chat/completions").strip()
    if not base:
      return ""
    if not path.startswith("/"):
      path = f"/{path}"
    return f"{base}{path}"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=800)
    history: list[ChatMessage] = Field(default_factory=list)


class SourceItem(BaseModel):
    source: str
    snippet: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


app = FastAPI(title="Jiahan Wang Portfolio RAG")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

knowledge_base = KnowledgeBase(
    knowledge_dir=ROOT_DIR / "backend" / "knowledge",
    embedding_model_name=os.getenv(
        "EMBEDDING_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ),
    embedding_threads=int(os.getenv("EMBEDDING_THREADS", "1")),
)


@app.on_event("startup")
async def startup_event() -> None:
    knowledge_base.load()


def llm_is_configured() -> bool:
    return bool(_build_chat_url() and os.getenv("LLM_MODEL", "").strip())


def _build_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("LLM_API_KEY", "").strip()
    key_header = os.getenv("LLM_API_KEY_HEADER", "Authorization").strip()
    key_prefix = os.getenv("LLM_API_KEY_PREFIX", "Bearer ")
    if key_prefix and not key_prefix.endswith(" "):
        key_prefix = f"{key_prefix} "
    if api_key and key_header:
        headers[key_header] = f"{key_prefix}{api_key}" if key_prefix else api_key
    return headers


async def generate_answer(question: str, history: list[ChatMessage], context: str) -> str:
    chat_url = _build_chat_url()
    if not chat_url:
        raise HTTPException(status_code=503, detail="LLM API 未配置：缺少聊天接口地址。")

    model = os.getenv("LLM_MODEL", "").strip()
    if not model:
        raise HTTPException(status_code=503, detail="LLM API 未配置：缺少模型名。")

    system_prompt = (
        "You are the portfolio AI assistant for Jiahan Wang. "
        "Answer only from the provided context about Jiahan's profile, skills, projects, education, "
        "experience, availability, and contact. "
        "If the answer is not supported by the context, say so clearly and do not invent anything. "
        "Reply in the same language as the user's question unless the user asks otherwise. "
        "Keep the answer concise, professional, and factual."
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    messages.extend(
        {"role": item.role, "content": item.content}
        for item in history[-6:]
    )
    messages.append(
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\n"
                f"Retrieved context:\n{context}\n\n"
                "Answer based only on the retrieved context."
            ),
        }
    )

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }

    timeout = float(os.getenv("LLM_REQUEST_TIMEOUT", "60"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(chat_url, headers=_build_headers(), json=payload)

    if response.status_code >= 400:
        detail = response.text[:400] or "LLM API 请求失败。"
        raise HTTPException(status_code=502, detail=f"LLM API 请求失败：{detail}")

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise HTTPException(status_code=502, detail="LLM API 返回内容为空。")

    answer = choices[0].get("message", {}).get("content", "").strip()
    if not answer:
        raise HTTPException(status_code=502, detail="LLM API 返回了空答案。")

    return answer


@app.get("/api/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "llm_configured": llm_is_configured(),
        "document_count": knowledge_base.document_count,
        "chunk_count": knowledge_base.chunk_count,
        "embedding_model": knowledge_base.embedding_model_name,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空。")

    top_k = int(os.getenv("RAG_TOP_K", "4"))
    retrieved = knowledge_base.search(question, top_k=top_k)
    if not retrieved:
        raise HTTPException(status_code=500, detail="知识库为空，无法执行检索。")

    context = "\n\n".join(
        f"[Source: {item.source} | Score: {item.score:.3f}]\n{item.text}"
        for item in retrieved
    )
    answer = await generate_answer(question, payload.history, context)
    sources = [
        SourceItem(source=item.source, snippet=item.snippet, score=item.score)
        for item in retrieved
    ]
    return ChatResponse(answer=answer, sources=sources)


@app.get("/", include_in_schema=False)
async def homepage() -> FileResponse:
    return FileResponse(ROOT_DIR / "index.html")


@app.get("/cv_mars2026.pdf", include_in_schema=False)
async def resume_pdf() -> FileResponse:
    return FileResponse(ROOT_DIR / "cv_mars2026.pdf")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(ROOT_DIR / "assets" / "icons" / "favicon.svg")


@app.get("/assets/{path:path}", include_in_schema=False)
async def assets(path: str) -> FileResponse:
    assets_dir = ROOT_DIR / "assets"
    candidate = (assets_dir / path).resolve()
    if assets_dir not in candidate.parents and candidate != assets_dir:
        raise HTTPException(status_code=404)
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(candidate)
