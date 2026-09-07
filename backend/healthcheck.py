"""Deep health probe for the personal-site LLM pipeline.

Runs on a systemd timer. Hits /api/chat end-to-end to confirm the retrieval +
LLM chain is actually producing answers, then pushes a WeChat notification via
Server酱 or PushPlus when the state flips (ok -> fail after N consecutive
failures, or fail -> ok recovery).

State lives in HEALTHCHECK_STATE_FILE so the timer-run process can remember
consecutive failures and the last notification time across invocations.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / "backend" / ".env"
load_dotenv(ENV_PATH)

DEFAULT_STATE_FILE = ROOT_DIR / "backend" / ".healthcheck_state.json"
DEFAULT_TARGET_URL = "http://127.0.0.1:8000/api/chat"
DEFAULT_QUESTION = "healthcheck ping"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("healthcheck")
# httpx logs full request URLs at INFO level. Notification providers place
# credentials in the URL path, so keep those URLs out of the system journal.
logging.getLogger("httpx").setLevel(logging.WARNING)


@dataclass
class State:
    """Persisted state across timer invocations."""

    consecutive_failures: int = 0
    status: str = "unknown"            # ok | fail | unknown
    last_ok_at: Optional[float] = None
    last_fail_at: Optional[float] = None
    last_notified_at: Optional[float] = None
    last_error: Optional[str] = None
    last_latency_ms: Optional[int] = None
    last_checked_at: Optional[float] = None
    outage_started_at: Optional[float] = None
    history: list[dict] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "State":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            log.warning("state file unreadable, starting fresh: %s", exc)
            return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)


@dataclass
class ProbeResult:
    ok: bool
    latency_ms: int
    error: Optional[str] = None
    answer_preview: Optional[str] = None


def probe_chat(url: str, question: str, timeout: float) -> ProbeResult:
    started = time.perf_counter()
    try:
        response = httpx.post(
            url,
            json={"question": question, "history": []},
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        return ProbeResult(ok=False, latency_ms=elapsed, error=f"HTTPError: {exc}")

    elapsed = int((time.perf_counter() - started) * 1000)

    if response.status_code >= 400:
        detail = ""
        try:
            detail = response.json().get("detail", "")
        except ValueError:
            detail = response.text[:300]
        return ProbeResult(
            ok=False,
            latency_ms=elapsed,
            error=f"HTTP {response.status_code}: {detail}",
        )

    try:
        data = response.json()
    except ValueError:
        return ProbeResult(ok=False, latency_ms=elapsed, error="response not JSON")

    answer = (data.get("answer") or "").strip()
    if not answer:
        return ProbeResult(ok=False, latency_ms=elapsed, error="empty answer")

    return ProbeResult(ok=True, latency_ms=elapsed, answer_preview=answer[:120])


def push_serverchan(send_key: str, title: str, desp: str) -> bool:
    url = f"https://sctapi.ftqq.com/{send_key}.send"
    try:
        response = httpx.post(url, data={"title": title, "desp": desp}, timeout=15)
        payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        ok = response.status_code == 200 and payload.get("code", 0) == 0
        if not ok:
            log.error("Server酱 push failed: status=%s body=%s", response.status_code, response.text[:200])
        return ok
    except httpx.HTTPError as exc:
        log.error("Server酱 push error: %s", exc)
        return False


def push_pushplus(token: str, title: str, content: str) -> bool:
    url = "http://www.pushplus.plus/send"
    try:
        response = httpx.post(
            url,
            json={"token": token, "title": title, "content": content, "template": "markdown"},
            timeout=15,
        )
        payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        ok = response.status_code == 200 and payload.get("code", 0) == 200
        if not ok:
            log.error("PushPlus push failed: status=%s body=%s", response.status_code, response.text[:200])
        return ok
    except httpx.HTTPError as exc:
        log.error("PushPlus push error: %s", exc)
        return False


def send_notification(title: str, body_md: str) -> bool:
    """Try all configured providers; return True if any one succeeds."""
    sent_any = False

    sct_key = os.getenv("HEALTHCHECK_SERVERCHAN_KEY", "").strip()
    if sct_key:
        if push_serverchan(sct_key, title, body_md):
            log.info("Server酱 notification sent")
            sent_any = True

    pp_token = os.getenv("HEALTHCHECK_PUSHPLUS_TOKEN", "").strip()
    if pp_token:
        if push_pushplus(pp_token, title, body_md):
            log.info("PushPlus notification sent")
            sent_any = True

    if not sct_key and not pp_token:
        log.warning("No push provider configured; skipping notification")

    return sent_any


def fmt_ts(ts: Optional[float]) -> str:
    if not ts:
        return "-"
    return time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(ts))


def build_outage_message(state: State, result: ProbeResult, host: str) -> tuple[str, str]:
    title = "🚨 LLM 服务异常"
    outage_started = fmt_ts(state.outage_started_at)
    last_ok = fmt_ts(state.last_ok_at)
    body = (
        f"**主机**: `{host}`\n\n"
        f"**连续失败次数**: {state.consecutive_failures}\n\n"
        f"**故障开始**: {outage_started}\n\n"
        f"**最近一次成功**: {last_ok}\n\n"
        f"**本次延迟**: {result.latency_ms} ms\n\n"
        f"**错误**:\n\n```\n{(result.error or '')[:800]}\n```\n"
    )
    return title, body


def build_recovery_message(state: State, result: ProbeResult, host: str, downtime_seconds: float) -> tuple[str, str]:
    title = "✅ LLM 服务已恢复"
    minutes = downtime_seconds / 60
    body = (
        f"**主机**: `{host}`\n\n"
        f"**故障持续**: {minutes:.1f} 分钟\n\n"
        f"**本次延迟**: {result.latency_ms} ms\n\n"
        f"**预览回答**: {result.answer_preview or '-'}\n"
    )
    return title, body


def main() -> int:
    state_path = Path(os.getenv("HEALTHCHECK_STATE_FILE", str(DEFAULT_STATE_FILE)))
    target_url = os.getenv("HEALTHCHECK_URL", DEFAULT_TARGET_URL).strip() or DEFAULT_TARGET_URL
    question = os.getenv("HEALTHCHECK_QUESTION", DEFAULT_QUESTION).strip() or DEFAULT_QUESTION
    timeout = float(os.getenv("HEALTHCHECK_TIMEOUT", "45"))
    failure_threshold = int(os.getenv("HEALTHCHECK_FAILURE_THRESHOLD", "2"))
    cooldown_minutes = float(os.getenv("HEALTHCHECK_COOLDOWN_MINUTES", "30"))
    host = socket.gethostname()

    state = State.load(state_path)
    result = probe_chat(target_url, question, timeout)
    now = time.time()

    state.last_checked_at = now
    state.last_latency_ms = result.latency_ms

    if result.ok:
        prev_status = state.status
        state.last_ok_at = now
        state.consecutive_failures = 0
        state.last_error = None
        state.status = "ok"

        log.info("probe ok (%sms) preview=%r", result.latency_ms, result.answer_preview)

        # Fire recovery notification if we were alerting before.
        if prev_status == "fail" and state.outage_started_at:
            downtime = now - state.outage_started_at
            title, body = build_recovery_message(state, result, host, downtime)
            send_notification(title, body)
            state.last_notified_at = now
            state.outage_started_at = None
    else:
        state.consecutive_failures += 1
        state.last_fail_at = now
        state.last_error = result.error
        log.warning(
            "probe failed (%sms) consecutive=%d error=%s",
            result.latency_ms,
            state.consecutive_failures,
            result.error,
        )

        if state.consecutive_failures >= failure_threshold:
            if state.status != "fail":
                state.status = "fail"
                state.outage_started_at = state.outage_started_at or state.last_fail_at

            cooldown_ok = (
                state.last_notified_at is None
                or (now - state.last_notified_at) >= cooldown_minutes * 60
            )
            if cooldown_ok:
                title, body = build_outage_message(state, result, host)
                if send_notification(title, body):
                    state.last_notified_at = now
            else:
                remaining = cooldown_minutes * 60 - (now - state.last_notified_at)
                log.info("in cooldown (%.0fs left), suppressing duplicate notification", remaining)

    # Keep a short rolling window of recent checks for debugging.
    state.history.append({
        "at": now,
        "ok": result.ok,
        "latency_ms": result.latency_ms,
        "error": result.error,
    })
    state.history = state.history[-20:]

    state.save(state_path)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
