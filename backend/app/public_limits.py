from __future__ import annotations

import os
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


class PublicLimits:
    """Env-configurable caps for the public demo API."""

    max_pdf_bytes: int = _env_int("PUBLIC_MAX_PDF_BYTES", 15 * 1024 * 1024)
    max_pdf_pages: int = _env_int("PUBLIC_MAX_PDF_PAGES", 40)
    max_uploads_per_ip_hour: int = _env_int("PUBLIC_MAX_UPLOADS_PER_IP_HOUR", 8)
    max_llm_per_session: int = _env_int("PUBLIC_MAX_LLM_PER_SESSION", 30)
    max_llm_per_ip_hour: int = _env_int("PUBLIC_MAX_LLM_PER_IP_HOUR", 80)
    max_chat_per_annotation: int = _env_int("PUBLIC_MAX_CHAT_PER_ANNOTATION", 8)
    max_question_chars: int = _env_int("PUBLIC_MAX_QUESTION_CHARS", 500)
    max_chat_message_chars: int = _env_int("PUBLIC_MAX_CHAT_MESSAGE_CHARS", 800)
    max_public_max_candidates: int = _env_int("PUBLIC_MAX_CANDIDATES", 8)
    disable_bulk_annotate: bool = _env_bool("PUBLIC_DISABLE_BULK_ANNOTATE", True)
    rate_window_seconds: int = _env_int("PUBLIC_RATE_WINDOW_SECONDS", 3600)


limits = PublicLimits()


class _SlidingWindow:
    def __init__(self, window_seconds: int) -> None:
        self._window = window_seconds
        self._events: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> list[float]:
        cutoff = now - self._window
        kept = [t for t in self._events[key] if t > cutoff]
        self._events[key] = kept
        return kept

    def count(self, key: str) -> int:
        now = time.time()
        with self._lock:
            return len(self._prune(key, now))

    def add(self, key: str) -> int:
        now = time.time()
        with self._lock:
            events = self._prune(key, now)
            events.append(now)
            self._events[key] = events
            return len(events)


_ip_uploads = _SlidingWindow(limits.rate_window_seconds)
_ip_llm = _SlidingWindow(limits.rate_window_seconds)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def limits_summary() -> dict:
    return {
        "max_pdf_mb": round(limits.max_pdf_bytes / (1024 * 1024), 1),
        "max_pdf_pages": limits.max_pdf_pages,
        "max_uploads_per_ip_hour": limits.max_uploads_per_ip_hour,
        "max_llm_per_session": limits.max_llm_per_session,
        "max_llm_per_ip_hour": limits.max_llm_per_ip_hour,
        "max_chat_per_annotation": limits.max_chat_per_annotation,
        "bulk_annotate_enabled": not limits.disable_bulk_annotate,
    }


def check_pdf_bytes(pdf_bytes: bytes) -> None:
    if len(pdf_bytes) > limits.max_pdf_bytes:
        mb = limits.max_pdf_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"PDF too large (max {mb:.0f} MB on the public demo).",
        )


def check_pdf_page_count(page_count: int) -> None:
    if page_count > limits.max_pdf_pages:
        raise HTTPException(
            status_code=413,
            detail=f"PDF has too many pages (max {limits.max_pdf_pages} on the public demo).",
        )


def check_upload_rate(ip: str) -> None:
    if limits.max_uploads_per_ip_hour <= 0:
        return
    if _ip_uploads.count(ip) >= limits.max_uploads_per_ip_hour:
        raise HTTPException(
            status_code=429,
            detail="Upload limit reached for this hour. Try again later.",
        )


def record_upload(ip: str) -> None:
    _ip_uploads.add(ip)


def check_bulk_annotate() -> None:
    if limits.disable_bulk_annotate:
        raise HTTPException(
            status_code=403,
            detail="Full-paper AI annotate is disabled on the public demo.",
        )


def check_question_text(text: str) -> None:
    if len(text.strip()) > limits.max_question_chars:
        raise HTTPException(
            status_code=400,
            detail=f"Question too long (max {limits.max_question_chars} characters).",
        )


def check_chat_message(text: str) -> None:
    if len(text.strip()) > limits.max_chat_message_chars:
        raise HTTPException(
            status_code=400,
            detail=f"Message too long (max {limits.max_chat_message_chars} characters).",
        )


def check_llm_allowed(
    ip: str,
    *,
    session_llm_calls: int,
    annotation_chat_calls: int | None = None,
) -> None:
    if limits.max_llm_per_ip_hour > 0 and _ip_llm.count(ip) >= limits.max_llm_per_ip_hour:
        raise HTTPException(
            status_code=429,
            detail="AI usage limit reached for this hour. Try again later.",
        )
    if limits.max_llm_per_session > 0 and session_llm_calls >= limits.max_llm_per_session:
        raise HTTPException(
            status_code=429,
            detail="AI usage limit reached for this document session.",
        )
    if (
        annotation_chat_calls is not None
        and limits.max_chat_per_annotation > 0
        and annotation_chat_calls >= limits.max_chat_per_annotation
    ):
        raise HTTPException(
            status_code=429,
            detail="Follow-up chat limit reached for this annotation.",
        )


def record_llm(ip: str) -> None:
    _ip_llm.add(ip)


def clamp_max_candidates(requested: int) -> int:
    cap = limits.max_public_max_candidates
    if cap <= 0:
        return requested
    return min(requested, cap)
