from __future__ import annotations

import os

DEFAULT_CORS_ORIGINS = ",".join(
    [
        "https://projects.tarun-ssharma.com",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
)


def cors_origins_from_env(*, extra: str | None = None) -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    if extra:
        raw = f"{raw},{extra}"
    return [o.strip() for o in raw.split(",") if o.strip()]
