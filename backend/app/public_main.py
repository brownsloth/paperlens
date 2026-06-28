from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from backend.app.cors import cors_origins_from_env
from backend.app.public_routes import router as public_router

ROOT = Path(__file__).resolve().parents[2]
DIST_DIR = ROOT / "frontend" / "dist"

ALLOWED_ORIGINS = cors_origins_from_env()

app = FastAPI(
    title="PaperLens",
    description="Upload a PDF, annotate and highlight, export — ephemeral sessions only",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public_router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "mode": "public", "cors_origins": ALLOWED_ORIGINS}


if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="frontend")
else:

    @app.get("/")
    def missing_frontend() -> PlainTextResponse:
        return PlainTextResponse(
            "Frontend not built. Run: cd frontend && VITE_PUBLIC_MODE=true npm run build",
            status_code=503,
        )


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("backend.app.public_main:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
