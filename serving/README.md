# PaperLens Public — Railway deploy

Public app: upload a PDF → highlight / annotate → export. Sessions are **ephemeral** (disk on the container, not a library).

Unlike **quote-search** and **Hindi Jinnie**, this ships **UI + API in one Railway service** (no separate Netlify step required). You can still embed or link it from [projects.tarun-ssharma.com](https://projects.tarun-ssharma.com) if you want.

```
Browser  ──▶  Railway (FastAPI + static Vite build)
              /api/upload, /api/papers/…, /api/health
              /          → PaperLens React UI
```

---

## Compare to your other Railway projects

| Project | Repo layout | Railway Dockerfile | UI host |
|---------|-------------|-------------------|---------|
| Quote Memory | `serving/Dockerfile` | API only | Netlify (Gatsby static) |
| Hindi Jinnie | `serving/Dockerfile` | API + HF model pull | Netlify (Gatsby static) |
| **PaperLens Public** | `Dockerfile.public` (repo root) | **API + UI together** | Same Railway URL |

---

## 1. Push to GitHub

This repo needs to be on GitHub (new repo is fine). From the repo root:

```bash
git remote add origin git@github.com:YOUR_USER/paperlens.git   # if not set
git add Dockerfile.public railway.toml requirements-public.txt serving/ backend/ paperlens/ ...
git commit -m "Add public PaperLens Railway deploy"
git push -u origin master
```

Do **not** commit `.env`, `data/`, or large PDFs.

---

## 2. Railway

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub** → select this repo.
2. Railway reads `railway.toml` at the repo root:
   - Builder: **Dockerfile**
   - Dockerfile path: `Dockerfile.public`
   - Health check: `GET /api/health`
3. **Variables** (Settings → Variables):

| Variable | Required | Example |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes (for “Annotate” + follow-up chat) | `sk-…` |
| `OPENAI_MODEL` | No | `gpt-4o-mini` |
| `OPENAI_BASE_URL` | No | OpenAI-compatible proxy URL |
| `CORS_ORIGINS` | No | Comma-separated browser origins (see below) |
| `PORT` | Auto-set by Railway | — |

**CORS** (required when UI is on Netlify at `projects.tarun-ssharma.com` and API on Railway):

```text
CORS_ORIGINS=https://projects.tarun-ssharma.com,http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173,http://127.0.0.1:5173
```

Defaults are baked in if unset. Check active origins: `curl https://YOUR-RAILWAY-URL/api/health` → `cors_origins`.

Highlights and manual notes work without the API key; AI annotate / selection Q&A need `OPENAI_API_KEY`.

4. **Networking → Generate domain** → e.g. `https://paperlens.up.railway.app`
5. Open the URL — you should see the upload screen.

### Smoke test

```bash
curl https://YOUR-RAILWAY-URL/api/health
# → {"status":"ok","mode":"public"}

curl -F "file=@/path/to/paper.pdf" https://YOUR-RAILWAY-URL/api/upload -o doc.json
```

---

## 3. Local Docker (optional)

```bash
docker build -f Dockerfile.public -t paperlens-public .
docker run -p 8080:8080 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  paperlens-public
# → http://localhost:8080
```

Or without Docker:

```bash
./scripts/start-public.sh          # API on :8080
cd frontend && npm run dev:public  # Vite dev UI on :5173
```

---

## 4. Portfolio (Netlify) + Railway API

Same split as Quote Memory and Hindi Jinnie:

| Host | URL |
|------|-----|
| UI | `https://projects.tarun-ssharma.com/paperlens/` |
| API | `https://YOUR-RAILWAY-URL` |

### Sync UI into Gatsby static

```bash
# Terminal 1 — API
./scripts/start-public.sh

# Terminal 2 — build & copy UI (uses ../../myblogs/projects by default)
chmod +x scripts/sync-portfolio-paperlens.sh
./scripts/sync-portfolio-paperlens.sh
```

Edit `serving/portfolio/config.js` with your Railway URL before syncing (or edit `static/paperlens/config.js` in the portfolio repo after copy).

**Local portfolio test:** copy `serving/portfolio/config.local.js.example` → portfolio `static/paperlens/config.js`, run Gatsby on :8000, API on :8080.

Commit & push the **portfolio** repo → Netlify rebuilds.

### Link only (no portfolio static)

You can also use the Railway URL directly (UI + API same origin, no CORS config needed).

---

## 5. Link from your portfolio (included)

The portfolio repo has:

- `static/paperlens/` — built UI (after `sync-portfolio-paperlens.sh`)
- Project write-up: `content/projects/paperlens/`
- Live demos strip + approach page links

---

## Ops notes

| Topic | Detail |
|-------|--------|
| Build time | ~2–4 min (npm + slim Python; **no** docling / HF weights) |
| Memory | 512MB–1GB recommended (PDF parse + page PNG render) |
| Persistence | Uploads live under `/app/data/public_sessions/` on the container disk — **lost on redeploy** unless you add a Railway volume |
| Full PaperLens library | Local only (`backend.app.main` + categories); not this image |

---

## File layout

```
Dockerfile.public          ← Railway image (UI + API)
railway.toml               ← builder + healthcheck
requirements-public.txt    ← slim deps (no docling)
scripts/start-public.sh    ← local dev
backend/app/public_main.py ← FastAPI + static files
backend/app/public_routes.py
frontend/                  ← PublicApp (VITE_PUBLIC_MODE)
serving/README.md          ← this file
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails on `npm ci` | Ensure `frontend/package-lock.json` is committed |
| `Frontend not built` 503 | Dockerfile frontend stage failed; check Railway build logs |
| Annotate returns 500 | Set `OPENAI_API_KEY` on Railway |
| Health check failing | Confirm service listens on `$PORT`; path is `/api/health` |
| Upload works then 404 after redeploy | Expected without a volume — sessions are ephemeral |
