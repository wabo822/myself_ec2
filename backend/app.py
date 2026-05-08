from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import time
from pathlib import Path
from typing import Literal, Optional

import httpx
from dotenv import load_dotenv
from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.rag import KnowledgeBase

import json

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / "backend" / ".env"
FRONTEND_DIST_DIR = ROOT_DIR / "frontend" / "dist"
HEALTHCHECK_STATE_FILE = ROOT_DIR / "backend" / ".healthcheck_state.json"
AUTH_FILE = ROOT_DIR / "backend" / "auth.json"
MEMORY_DIR = ROOT_DIR / "backend" / "data" / "sessions"
SESSION_COOKIE_NAME = "math_session"
load_dotenv(ENV_PATH)
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

FRONTEND_META = {
    False: {
        "lang": "fr",
        "title": "Jiahan Wang | AI & Embedded Systems Builder",
        "description": (
            "Portfolio personnel de Jiahan Wang, étudiant ingénieur à Paris, entre "
            "intelligence artificielle, RAG, vision embarquée et systèmes connectés."
        ),
        "robots": "index,follow",
    },
    True: {
        "lang": "zh-CN",
        "title": "王稼瀚 | 中文问答入口",
        "description": (
            "王稼瀚的中文问答入口，可以直接用中文提问他的项目经历、RAG、嵌入式系统、技能和求职方向。"
        ),
        "robots": "noindex, nofollow",
    },
}


SUPPORTED_LLM_PROVIDERS = {"openai_compatible", "anthropic"}


def _llm_provider() -> str:
    raw_provider = os.getenv("LLM_PROVIDER", "openai_compatible").strip().lower()
    aliases = {
        "openai": "openai_compatible",
        "openai-compatible": "openai_compatible",
        "compatible": "openai_compatible",
        "claude": "anthropic",
    }
    return aliases.get(raw_provider, raw_provider or "openai_compatible")


def _build_chat_url() -> str:
    provider = _llm_provider()
    full_url_env = "LLM_MESSAGES_URL" if provider == "anthropic" else "LLM_CHAT_COMPLETIONS_URL"
    default_path = "/messages" if provider == "anthropic" else "/chat/completions"

    full_url = os.getenv(full_url_env, "").strip()
    if full_url:
        return full_url

    base = os.getenv("LLM_API_BASE_URL", "").strip().rstrip("/")
    path = os.getenv("LLM_API_PATH", default_path).strip()
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


class MathImage(BaseModel):
    media_type: Literal["image/jpeg", "image/png", "image/gif", "image/webp"]
    # base64 string; 20M chars ≈ 15MB raw image — plenty for phone photos
    data: str = Field(min_length=1, max_length=20_000_000)


class MathChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(default="", max_length=8000)
    images: list[MathImage] = Field(default_factory=list)


class MathChatRequest(BaseModel):
    question: str = Field(default="", max_length=4000)
    images: list[MathImage] = Field(default_factory=list)
    history: list[MathChatMessage] = Field(default_factory=list)


class MathChatResponse(BaseModel):
    answer: str


app = FastAPI(title="Jiahan Wang Portfolio RAG")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount(
    "/app",
    StaticFiles(directory=FRONTEND_DIST_DIR / "app", check_dir=False),
    name="frontend-app",
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
    return (
        _llm_provider() in SUPPORTED_LLM_PROVIDERS
        and bool(_build_chat_url() and os.getenv("LLM_MODEL", "").strip() and os.getenv("LLM_API_KEY", "").strip())
    )


def _build_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("LLM_API_KEY", "").strip()

    if _llm_provider() == "anthropic":
        if api_key:
            headers["x-api-key"] = api_key
        headers["anthropic-version"] = os.getenv("LLM_ANTHROPIC_VERSION", "2023-06-01").strip() or "2023-06-01"
        anthropic_beta = os.getenv("LLM_ANTHROPIC_BETA", "").strip()
        if anthropic_beta:
            headers["anthropic-beta"] = anthropic_beta
        return headers

    key_header = os.getenv("LLM_API_KEY_HEADER", "Authorization").strip()
    key_prefix = os.getenv("LLM_API_KEY_PREFIX", "Bearer ")
    if key_prefix and not key_prefix.endswith(" "):
        key_prefix = f"{key_prefix} "
    if api_key and key_header:
        headers[key_header] = f"{key_prefix}{api_key}" if key_prefix else api_key
    return headers


def _clean_answer_content(content: str) -> str:
    # MiniMax OpenAI-compatible responses may include reasoning inside <think> tags.
    cleaned = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL).strip()
    return cleaned or content.strip()


def _llm_auth_error_detail() -> str:
    if _llm_provider() == "anthropic":
        return (
            "Claude API 鉴权失败：请检查 Anthropic API key 是否有效，并确认接口地址为 "
            "https://api.anthropic.com/v1/messages。"
        )

    return (
        "LLM API 鉴权失败：请检查 API key 是否有效，以及 key 是否有对应模型分组的权限"
        "（当前网关：https://api.pptv.help/v1/chat/completions）。"
    )


def _build_user_prompt(question: str, context: str) -> str:
    return (
        f"Question:\n{question}\n\n"
        f"Retrieved context:\n{context}\n\n"
        "Answer based only on the retrieved context."
    )


def _apply_thinking_flag(payload: dict[str, object]) -> None:
    """DeepSeek v4-pro defaults to thinking mode, which silently consumes max_tokens.

    When LLM_THINKING_DISABLED is true (the default for our DeepSeek setup), pass
    `thinking: {type: "disabled"}` so the visible answer comes back in `content`.
    """
    if os.getenv("LLM_THINKING_DISABLED", "false").strip().lower() in {"1", "true", "yes"}:
        payload["thinking"] = {"type": "disabled"}


def _build_openai_payload(system_prompt: str, question: str, history: list[ChatMessage], context: str) -> dict[str, object]:
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    messages.extend(
        {"role": item.role, "content": item.content}
        for item in history[-6:]
    )
    messages.append({"role": "user", "content": _build_user_prompt(question, context)})

    payload: dict[str, object] = {
        "model": os.getenv("LLM_MODEL", "").strip(),
        "messages": messages,
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "1024")),
    }
    if os.getenv("LLM_REASONING_SPLIT", "false").strip().lower() in {"1", "true", "yes"}:
        payload["reasoning_split"] = True
    _apply_thinking_flag(payload)
    return payload


def _build_anthropic_payload(system_prompt: str, question: str, history: list[ChatMessage], context: str) -> dict[str, object]:
    messages = [
        {"role": item.role, "content": item.content}
        for item in history[-6:]
    ]
    messages.append({"role": "user", "content": _build_user_prompt(question, context)})

    return {
        "model": os.getenv("LLM_MODEL", "").strip(),
        "system": system_prompt,
        "messages": messages,
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "1024")),
    }


def _response_json(response: httpx.Response) -> dict[str, object] | None:
    try:
        data = response.json()
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _llm_error_payload(data: dict[str, object] | None) -> dict[str, object] | None:
    if not isinstance(data, dict) or data.get("type") != "error":
        return None
    error = data.get("error")
    return error if isinstance(error, dict) else {}


def _is_auth_error(response: httpx.Response, data: dict[str, object] | None) -> bool:
    if response.status_code in {401, 403}:
        return True

    error = _llm_error_payload(data)
    if not error:
        return False

    error_type = str(error.get("type", "")).strip().lower()
    return error_type in {"authorized_error", "authentication_error", "permission_error", "invalid_api_key"}


def _extract_openai_answer(data: dict[str, object]) -> str:
    choices = data.get("choices", [])
    if not isinstance(choices, list) or not choices:
        raise HTTPException(status_code=502, detail="LLM API 返回内容为空。")

    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = message.get("content", "") if isinstance(message, dict) else ""
    if isinstance(content, list):
        content = "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        )

    answer = _clean_answer_content(str(content or ""))
    if not answer:
        raise HTTPException(status_code=502, detail="LLM API 返回了空答案。")
    return answer


def _extract_anthropic_answer(data: dict[str, object]) -> str:
    content = data.get("content", [])
    if not isinstance(content, list) or not content:
        raise HTTPException(status_code=502, detail="Claude API 返回内容为空。")

    answer = _clean_answer_content(
        "\n".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        )
    )
    if not answer:
        raise HTTPException(status_code=502, detail="Claude API 返回了空答案。")
    return answer


async def generate_answer(question: str, history: list[ChatMessage], context: str) -> str:
    provider = _llm_provider()
    if provider not in SUPPORTED_LLM_PROVIDERS:
        raise HTTPException(status_code=503, detail=f"LLM_PROVIDER 不支持：{provider}")

    if not os.getenv("LLM_API_KEY", "").strip():
        raise HTTPException(status_code=503, detail="LLM API 未配置：缺少 API key。")

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

    payload = (
        _build_anthropic_payload(system_prompt, question, history, context)
        if provider == "anthropic"
        else _build_openai_payload(system_prompt, question, history, context)
    )

    timeout = float(os.getenv("LLM_REQUEST_TIMEOUT", "60"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(chat_url, headers=_build_headers(), json=payload)

    data = _response_json(response)

    if _is_auth_error(response, data):
        raise HTTPException(status_code=502, detail=_llm_auth_error_detail())

    error = _llm_error_payload(data)
    if error is not None:
        detail = error.get("message") or response.text[:400] or "LLM API 请求失败。"
        raise HTTPException(status_code=502, detail=f"LLM API 请求失败：{detail}")

    if response.status_code >= 400:
        detail = response.text[:400] or "LLM API 请求失败。"
        raise HTTPException(status_code=502, detail=f"LLM API 请求失败：{detail}")

    if data is None:
        raise HTTPException(status_code=502, detail="LLM API 返回格式无法解析。")

    return _extract_anthropic_answer(data) if provider == "anthropic" else _extract_openai_answer(data)


def _frontend_entrypoint(is_chinese: bool = False) -> Path:
    dist_index = FRONTEND_DIST_DIR / "index.html"
    if dist_index.exists():
        return dist_index

    fallback = ROOT_DIR / "zh" / "index.html" if is_chinese else ROOT_DIR / "index.html"
    return fallback


def _render_frontend_html(is_chinese: bool = False) -> HTMLResponse | FileResponse:
    entrypoint = _frontend_entrypoint(is_chinese=is_chinese)
    if entrypoint.parent != FRONTEND_DIST_DIR:
        return FileResponse(entrypoint)

    html = entrypoint.read_text(encoding="utf-8")
    meta = FRONTEND_META[is_chinese]

    html = re.sub(r'<html lang="[^"]+">', f'<html lang="{meta["lang"]}">', html, count=1)
    html = re.sub(r"<title>.*?</title>", f"<title>{meta['title']}</title>", html, count=1, flags=re.DOTALL)
    html = re.sub(
        r'(<meta\s+name="description"\s+content=")([^"]*)(")',
        lambda match: f'{match.group(1)}{meta["description"]}{match.group(3)}',
        html,
        count=1,
    )
    html = re.sub(
        r'(<meta\s+name="robots"\s+content=")([^"]*)(")',
        lambda match: f'{match.group(1)}{meta["robots"]}{match.group(3)}',
        html,
        count=1,
    )
    return HTMLResponse(content=html)


def _read_healthcheck_state() -> dict[str, object]:
    """Read the last deep-probe result written by backend.healthcheck.

    The probe runs on a systemd timer and persists status + timestamps here.
    Exposed through /api/health so external monitors (UptimeRobot, etc.)
    can watch one endpoint and catch LLM-chain failures.
    """
    state_file_env = os.getenv("HEALTHCHECK_STATE_FILE", "").strip()
    state_path = Path(state_file_env) if state_file_env else HEALTHCHECK_STATE_FILE
    if not state_path.exists():
        return {"status": "unknown"}
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {"status": "unknown"}
    return {
        "status": raw.get("status", "unknown"),
        "last_checked_at": raw.get("last_checked_at"),
        "last_ok_at": raw.get("last_ok_at"),
        "last_fail_at": raw.get("last_fail_at"),
        "last_latency_ms": raw.get("last_latency_ms"),
        "consecutive_failures": raw.get("consecutive_failures", 0),
        "last_error": raw.get("last_error"),
    }


@app.get("/api/health")
async def health() -> dict[str, object]:
    probe = _read_healthcheck_state()
    return {
        "status": "ok" if probe.get("status") != "fail" else "degraded",
        "llm_configured": llm_is_configured(),
        "document_count": knowledge_base.document_count,
        "chunk_count": knowledge_base.chunk_count,
        "embedding_model": knowledge_base.embedding_model_name,
        "llm_probe": probe,
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


# ----------------------------------------------------------------------
# Auth: pbkdf2 password hashing + HMAC-signed session cookie (no deps)
# ----------------------------------------------------------------------

def _load_users() -> dict[str, str]:
    """Read backend/auth.json -> {username: pbkdf2_sha256$iters$salt_b64$hash_b64}."""
    if not AUTH_FILE.exists():
        return {}
    try:
        raw = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    users = raw.get("users") if isinstance(raw, dict) else None
    return users if isinstance(users, dict) else {}


def _verify_password(plain: str, stored: str) -> bool:
    """Verify password against pbkdf2_sha256$iters$salt_b64$hash_b64 format."""
    try:
        scheme, iters_s, salt_b64, hash_b64 = stored.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except (ValueError, TypeError):
        return False

    digest = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, iters)
    return hmac.compare_digest(digest, expected)


def _session_secret() -> bytes:
    secret = os.getenv("MATH_SESSION_SECRET", "").strip()
    if not secret:
        # Fail closed: refuse to mint cookies without a configured secret.
        raise HTTPException(status_code=503, detail="MATH_SESSION_SECRET 未配置。")
    return secret.encode("utf-8")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _sign_session(username: str) -> str:
    ttl = int(os.getenv("MATH_SESSION_TTL_SECONDS", "604800"))
    payload = {"u": username, "iat": int(time.time()), "exp": int(time.time()) + ttl}
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(_session_secret(), payload_bytes, hashlib.sha256).hexdigest()
    return f"{_b64url_encode(payload_bytes)}.{sig}"


def _verify_session(token: Optional[str]) -> Optional[str]:
    if not token or "." not in token:
        return None
    payload_b64, sig = token.rsplit(".", 1)
    try:
        payload_bytes = _b64url_decode(payload_b64)
    except (ValueError, TypeError):
        return None
    expected = hmac.new(_session_secret(), payload_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    user = payload.get("u")
    return user if isinstance(user, str) and user else None


def current_user(math_session: Optional[str] = Cookie(default=None)) -> str:
    user = _verify_session(math_session)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或会话已过期。")
    if user not in _load_users():
        # User was removed from auth.json after they got a cookie.
        raise HTTPException(status_code=401, detail="用户不存在。")
    return user


# ----------------------------------------------------------------------
# Per-user math chat memory (last N turns persisted to disk)
# ----------------------------------------------------------------------

def _memory_path(username: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", username)
    return MEMORY_DIR / f"{safe}.json"


def _memory_max_messages() -> int:
    """Cap = N turns × 2 (each turn = user + assistant). Default 3 turns -> 6 msgs."""
    return max(2, int(os.getenv("MATH_MEMORY_TURNS", "3")) * 2)


def _load_memory(username: str) -> list[dict[str, str]]:
    path = _memory_path(username)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
    msgs = raw.get("messages") if isinstance(raw, dict) else None
    if not isinstance(msgs, list):
        return []
    out: list[dict[str, str]] = []
    for m in msgs[-_memory_max_messages():]:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = m.get("content", "")
        if role in {"user", "assistant"} and isinstance(content, str):
            out.append({"role": role, "content": content})
    return out


def _save_memory(username: str, messages: list[dict[str, str]]) -> None:
    pruned = messages[-_memory_max_messages():]
    payload = {"messages": pruned, "updated_at": int(time.time())}
    path = _memory_path(username)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=0), encoding="utf-8")
    os.replace(tmp, path)


def _append_memory(username: str, user_text: str, assistant_text: str, had_image: bool) -> None:
    msgs = _load_memory(username)
    user_record = user_text or ("[图片]" if had_image else "")
    if had_image and user_text:
        user_record = f"{user_text}\n[已上传 1 张图片]"
    msgs.append({"role": "user", "content": user_record})
    msgs.append({"role": "assistant", "content": assistant_text})
    _save_memory(username, msgs)


def _clear_memory(username: str) -> None:
    path = _memory_path(username)
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


MATH_SYSTEM_PROMPT = (
    "你是一个耐心、严谨的数学解题助手，面向中学到大学的学生。\n"
    "原则：\n"
    "1. 看到题目（文字或图片）后，先简短复述题意，再分步骤推导，最后给出明确答案。\n"
    "2. 推导每一步都要写清楚用到的定义、公式或定理，不要跳步；让学生看得懂为什么这样做。\n"
    "3. 数学公式一律使用 LaTeX：行内用 $...$，独立公式用 $$...$$，不要用 \\( \\) 或 \\[ \\]。\n"
    "4. 如果图片里题目模糊或缺信息，先指出哪里看不清并请用户补充，不要瞎猜数字。\n"
    "5. 题目有歧义就先列出可能的解读，再让用户确认；不要假装确定。\n"
    "6. 只回答数学/逻辑/相关学科问题；与做题无关的请求礼貌拒绝并把话题拉回做题。\n"
    "7. 回答语言跟随用户提问的语言（中文 / English / Français 等）。\n"
    "8. 末尾用一行写「答案：...」，便于学生快速对答案。"
)


def _math_user_blocks(text: str, images: list[MathImage]) -> list[dict[str, object]]:
    """Build OpenAI-compatible multimodal content blocks for one user turn."""
    blocks: list[dict[str, object]] = []
    for img in images:
        blocks.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{img.media_type};base64,{img.data}"},
            }
        )
    if text:
        blocks.append({"type": "text", "text": text})
    if not blocks:
        blocks.append({"type": "text", "text": "（学生没有输入文字也没有上传图片，请提示其上传题目。）"})
    return blocks


def _math_assistant_blocks(text: str) -> list[dict[str, object]]:
    return [{"type": "text", "text": text or ""}]


def _build_math_payload(
    question: str,
    images: list[MathImage],
    history: list[MathChatMessage],
) -> dict[str, object]:
    """Build a multimodal Chat Completions payload for the PPTV / OpenAI-compatible gateway."""
    messages: list[dict[str, object]] = [{"role": "system", "content": MATH_SYSTEM_PROMPT}]
    for item in history[-10:]:
        if item.role == "user":
            content = _math_user_blocks(item.content.strip(), item.images)
        else:
            content = _math_assistant_blocks(item.content.strip())
        messages.append({"role": item.role, "content": content})

    messages.append({"role": "user", "content": _math_user_blocks(question.strip(), images)})

    payload: dict[str, object] = {
        "model": os.getenv("LLM_MODEL", "").strip(),
        "messages": messages,
        "temperature": float(os.getenv("MATH_LLM_TEMPERATURE", "0.2")),
        "max_tokens": int(os.getenv("MATH_LLM_MAX_TOKENS", "2048")),
    }
    if os.getenv("LLM_REASONING_SPLIT", "false").strip().lower() in {"1", "true", "yes"}:
        payload["reasoning_split"] = True
    _apply_thinking_flag(payload)
    return payload


def _llm_supports_vision() -> bool:
    return os.getenv("LLM_SUPPORTS_VISION", "false").strip().lower() in {"1", "true", "yes"}


def _vision_proxy_configured() -> bool:
    return bool(
        os.getenv("VISION_LLM_API_KEY", "").strip()
        and os.getenv("VISION_LLM_MODEL", "").strip()
        and (
            os.getenv("VISION_LLM_API_BASE_URL", "").strip()
            or os.getenv("VISION_LLM_CHAT_COMPLETIONS_URL", "").strip()
        )
    )


def _math_can_accept_images() -> bool:
    return _llm_supports_vision() or _vision_proxy_configured()


def _vision_chat_url() -> str:
    full = os.getenv("VISION_LLM_CHAT_COMPLETIONS_URL", "").strip()
    if full:
        return full
    base = os.getenv("VISION_LLM_API_BASE_URL", "").strip().rstrip("/")
    path = os.getenv("VISION_LLM_API_PATH", "/chat/completions").strip()
    if not base:
        return ""
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


VISION_OCR_PROMPT = (
    "你是一个严格的题目识别助手。看着图片把上面的题目原样转录出来。\n"
    "规则：\n"
    "1. 只转录，不要解题，不要给提示。\n"
    "2. 公式/数学符号一律用 LaTeX：行内 $...$，独立公式 $$...$$。\n"
    "3. 保留原始语言（中文 / English / Français 等），不要翻译。\n"
    "4. 多道题就分别编号并全部转录。\n"
    "5. 如果某处看不清，原位置写 [图像不清: 我推测是 X] 而不要乱猜。\n"
    "6. 直接输出转录结果，不要加任何前后说明。"
)


async def transcribe_images(images: list[MathImage]) -> str:
    """Call the vision proxy (Gemini OpenAI-compat) to OCR math problem images into text + LaTeX."""
    url = _vision_chat_url()
    api_key = os.getenv("VISION_LLM_API_KEY", "").strip()
    model = os.getenv("VISION_LLM_MODEL", "").strip()

    if not (url and api_key and model):
        raise HTTPException(status_code=503, detail="视觉模型未配置完整。")

    content_blocks: list[dict[str, object]] = []
    for img in images:
        content_blocks.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{img.media_type};base64,{img.data}"},
            }
        )
    content_blocks.append({"type": "text", "text": "请按上面的规则转录这些图片里的题目。"})

    payload = {
        "model": model,
        "max_tokens": int(os.getenv("VISION_LLM_MAX_TOKENS", "1500")),
        "messages": [
            {"role": "system", "content": VISION_OCR_PROMPT},
            {"role": "user", "content": content_blocks},
        ],
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    timeout = float(os.getenv("VISION_LLM_REQUEST_TIMEOUT", "60"))

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.status_code in {401, 403}:
        raise HTTPException(status_code=502, detail="视觉模型鉴权失败，请检查 VISION_LLM_API_KEY。")

    if response.status_code >= 400:
        detail = response.text[:400] or "视觉模型请求失败。"
        raise HTTPException(status_code=502, detail=f"视觉模型请求失败：{detail}")

    data = _response_json(response) or {}
    transcription = _extract_openai_answer(data).strip()
    if not transcription:
        raise HTTPException(status_code=502, detail="视觉模型返回空转录。")
    return transcription


async def generate_math_answer(
    question: str,
    images: list[MathImage],
    history: list[MathChatMessage],
) -> str:
    provider = _llm_provider()
    if provider != "openai_compatible":
        raise HTTPException(
            status_code=503,
            detail=f"/api/math-chat 当前只支持 openai_compatible 网关，当前 provider={provider}",
        )

    if images and not _math_can_accept_images():
        raise HTTPException(
            status_code=400,
            detail=(
                "当前后端 LLM（"
                f"{os.getenv('LLM_MODEL', 'unknown').strip()}"
                "）不支持图片识别，且未配置视觉模型代理。请用文字描述题目。"
            ),
        )

    # If main LLM can't see images but a vision proxy is configured, OCR them first
    # and replace images with their transcribed text. DeepSeek will only see text.
    if images and not _llm_supports_vision() and _vision_proxy_configured():
        transcription = await transcribe_images(images)
        ocr_block = f"[图片转录的题目]\n{transcription}"
        question = f"{question}\n\n{ocr_block}" if question else ocr_block
        images = []

    # Strip any historical images — at this point we're sending text-only to the
    # chat LLM (DeepSeek). Historical images were already consumed last turn.
    history_text = [
        MathChatMessage(role=m.role, content=m.content, images=[])
        for m in history
    ]

    if not os.getenv("LLM_API_KEY", "").strip():
        raise HTTPException(status_code=503, detail="LLM API 未配置：缺少 API key。")

    chat_url = _build_chat_url()
    if not chat_url:
        raise HTTPException(status_code=503, detail="LLM API 未配置：缺少聊天接口地址。")

    if not os.getenv("LLM_MODEL", "").strip():
        raise HTTPException(status_code=503, detail="LLM API 未配置：缺少模型名。")

    payload = _build_math_payload(question, images, history_text)
    timeout = float(os.getenv("LLM_REQUEST_TIMEOUT", "60"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(chat_url, headers=_build_headers(), json=payload)

    data = _response_json(response)

    if _is_auth_error(response, data):
        raise HTTPException(status_code=502, detail=_llm_auth_error_detail())

    error = _llm_error_payload(data)
    if error is not None:
        detail = error.get("message") or response.text[:400] or "LLM API 请求失败。"
        raise HTTPException(status_code=502, detail=f"LLM API 请求失败：{detail}")

    if response.status_code >= 400:
        detail = response.text[:400] or "LLM API 请求失败。"
        raise HTTPException(status_code=502, detail=f"LLM API 请求失败：{detail}")

    if data is None:
        raise HTTPException(status_code=502, detail="LLM API 返回格式无法解析。")

    return _extract_openai_answer(data)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=200)


@app.post("/api/auth/login")
async def auth_login(payload: LoginRequest, response: Response) -> dict[str, str]:
    users = _load_users()
    stored = users.get(payload.username)
    # Run pbkdf2 even on missing user to avoid timing leak of valid usernames.
    ok = _verify_password(payload.password, stored or "pbkdf2_sha256$200000$AAAAAAAAAAAAAAAAAAAAAA==$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
    if not stored or not ok:
        raise HTTPException(status_code=401, detail="账号或密码错误。")

    token = _sign_session(payload.username)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=int(os.getenv("MATH_SESSION_TTL_SECONDS", "604800")),
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return {"username": payload.username}


@app.post("/api/auth/logout")
async def auth_logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
async def auth_me(user: str = Depends(current_user)) -> dict[str, str]:
    return {"username": user}


@app.post("/api/math-chat", response_model=MathChatResponse)
async def math_chat(payload: MathChatRequest, user: str = Depends(current_user)) -> MathChatResponse:
    question = payload.question.strip()
    if not question and not payload.images:
        raise HTTPException(status_code=400, detail="请输入题目文字或上传题目图片。")

    # Server-side memory replaces whatever the client sent as history.
    stored = _load_memory(user)
    history = [MathChatMessage(role=m["role"], content=m["content"]) for m in stored]

    answer = await generate_math_answer(question, payload.images, history)
    _append_memory(user, question, answer, had_image=bool(payload.images))
    return MathChatResponse(answer=answer)


@app.get("/api/math-chat/memory")
async def math_chat_memory(user: str = Depends(current_user)) -> dict[str, object]:
    return {"messages": _load_memory(user), "max_turns": int(os.getenv("MATH_MEMORY_TURNS", "3"))}


@app.delete("/api/math-chat/memory")
async def math_chat_memory_clear(user: str = Depends(current_user)) -> dict[str, bool]:
    _clear_memory(user)
    return {"ok": True}


@app.get("/api/math-chat/config")
async def math_chat_config() -> dict[str, object]:
    return {
        "model": os.getenv("LLM_MODEL", "").strip(),
        "vision": _math_can_accept_images(),
        "vision_via_proxy": (not _llm_supports_vision()) and _vision_proxy_configured(),
        "vision_model": (
            os.getenv("VISION_LLM_MODEL", "").strip()
            if _vision_proxy_configured()
            else ""
        ),
        "memory_turns": int(os.getenv("MATH_MEMORY_TURNS", "3")),
    }


@app.get("/math", include_in_schema=False)
@app.get("/math/", include_in_schema=False)
async def math_page() -> FileResponse:
    page = ROOT_DIR / "frontend" / "math.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail="math 页面未构建。")
    # 别让浏览器（尤其 iOS Safari）缓存这个页面，否则前端 bug 修了用户还卡在旧版
    return FileResponse(
        page,
        media_type="text/html; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/", include_in_schema=False)
async def homepage():
    return _render_frontend_html()


@app.get("/zh", include_in_schema=False)
@app.get("/zh/", include_in_schema=False)
@app.get("/zh/index.html", include_in_schema=False)
@app.get("/zh.com", include_in_schema=False)
@app.get("/zh.com/", include_in_schema=False)
async def homepage_zh():
    return _render_frontend_html(is_chinese=True)


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
