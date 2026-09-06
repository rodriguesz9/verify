# VerifAI — Project Structure & Architecture

Digital audit & misinformation-fighting platform ("Antigravity Core").
Stack: **FastAPI + PostgreSQL (async SQLAlchemy) + React (Vite) + Docker Compose**.
External forensic APIs: Gemini, Sightengine, Hugging Face, Serper/SerpApi, GPTZero, Google OAuth.

---

## High-Level Architecture

```
Browser (React)
   │  /api (HTTP-only JWT cookies, axios)
   ▼
FastAPI backend (uvicorn, port 8000)
   │
   ├─ Auth  : JWT (access 60min / refresh 7d), Google OAuth, tier-based daily limits
   ├─ API   : /check-text, /check-url, /upload, /history
   ├─ Core  : analysis pipeline + forensic clients
   └─ DB    : PostgreSQL 16 (asyncpg), tables auto-created on startup
```

Request flow: `api router → verify_limit (quota) → sanitize input → run_pipeline (parallel forensic tasks) → Gemini final report → persist Verification + AnalysisMetrics → return report JSON`.

Media uploads: md5 hash → cache lookup (`cache_registry`, 7-day TTL) → Sightengine + Hugging Face deepfake/AI checks → Gemini report → cache+persist.

---

## Repository Layout

```
verify/
├── AGENTS.md              # Agent behavior rules (read first)
├── README.md              # Project intro, env vars, setup
├── docker-compose.yml     # db + backend + frontend orchestration
├── fix-docker.sh          # Docker fix helper script
├── issues.md              # Known issues / roadmap
├── docs/
│   ├── general.md         # This file
│   └── serper.md          # Serper news-search notes
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env / .env.example
│   ├── init_db.py
│   ├── tests/
│   └── app/
│       ├── main.py        # FastAPI app, middleware, rate limiter, router wiring
│       ├── api/           # Route handlers
│       ├── core/          # Business logic + external client wrappers
│       └── models/        # SQLAlchemy ORM + Pydantic schemas
└── frontend/
    ├── Dockerfile / Dockerfile.dev
    ├── vite.config.js / tailwind.config.js / package.json
    └── src/
        ├── main.jsx / App.jsx      # Entry + routes
        ├── components/             # Navbar, Dropzone, GaugeChart, ProtectedRoute...
        ├── pages/                  # Landing, Dashboard, Report, History, Pricing...
        ├── hooks/useAuth.jsx       # Auth context
        └── services/api.js         # Axios client + endpoint wrappers
```

---

## Backend (`backend/app`)

### `main.py` — App entry
- Creates FastAPI app, mounts slowapi rate limiter (IP-based).
- CORS from `CORS_ORIGINS`, security headers middleware.
- Startup: `init_db()` creates all tables.
- Wires routers under `/api`: auth, check_text, check_url, upload, history.
- `POST /api/auth/login-rl` is rate-limited wrapper (5/15min) — actual logic lives in auth router.

### `api/` — Routers (thin layers: validate → quota → pipeline → persist)
- `auth.py` — register/login/google/refresh/logout/me. Argon2 hashing via `core/security`. Sets access+refresh JWTs as HTTP-only same-site cookies. Email/password validation.
- `check_text.py` — `POST /api/check-text`. Sanitize text → `run_pipeline` → store Verification + AnalysisMetrics.
- `check_url.py` — `POST /api/check-url`. Scrapes page (httpx + BeautifulSoup, strips nav/scripts, grabs `<main>`/`<article>`), then same pipeline.
- `upload.py` — `POST /api/upload`. Allowed MIME types, 15MB cap, md5 cache, image deepfake/AI forensics, persist + cache.
- `history.py` — paginated history, `/history/stats`, single record by id.

### `core/` — Business logic & integrations
- `pipeline.py` — **Central orchestrator ("Antigravity Core")**. Async: Gemini claim extraction → fact-check queries (first 5 claims) + Serper news search (first 3) + GPTZero AI-text detection + domain reputation. Dedupes results, builds context dict, calls `generate_final_report`.
- `gemini_analyzer.py` — Gemini orchestration: `extract_claims_with_ai`, `decontextualize_claims` (standalone searchable claims), `generate_final_report` (JSON verdict: verdict/score/summary/red_flags/semantic_score/sensationalism/domain_score/temporal_issues/positives + evidence arrays). Injects current timestamp as "absolute present" for temporal anchoring.
- `fact_checker.py` — `query_fact_check_api` (Google Fact Check Tools style).
- `domain_checker.py` — `check_domain_reputation` (sync, run via `asyncio.to_thread`).
- `gptzero_client.py` — AI-text detection (perplexity analysis).
- `serper_client.py` — `search_news` (news search via Serper).
- `sightengine_client.py` — `check_deepfake` (deepfake + AI-gen image/video).
- `huggingface_client.py` — `check_ai_image_hf` (community model second check).
- `serpapi_client.py` — Google Reverse Image search wrapper.
- `hive_moderation.py` — Hive moderation API wrapper.
- `auth.py` — `get_current_user` (JWT from HTTP-only access cookie), `verify_limit` (tier-based daily quota: Standard 300 textual/100 media, Premium 10k/5k, Enterprise 9999), Google token verify.
- `security.py` — Argon2 hashing, JWT create/decode, bleach-based XSS sanitize, password/email validation.
- `cache.py` — caching helpers.
- `database.py` — async engine, `get_db` dependency, `init_db`.

### `models/` — ORM & schemas
- `user.py` — `User` (UUID pk, email unique, google_id, hashed_password nullable for OAuth, tier enum, timestamps).
- `history.py` — `Verification` (per-analysis record: content_type, source_url, file_hash_md5, verdict_score 0-100, verdict_label, ai_summary, raw_result JSON), `AnalysisMetrics` (forensic scores per provider), `CacheRegistry` (md5 → cached verdict, expires_at).
- `schemas.py` — Pydantic: `AnalysisRequest`, `UrlRequest`, `FactCheckResult`, `AnalysisResponse`.

### Tests
`backend/tests/` — pytest suite (run against backend container / test DB).

---

## Frontend (`frontend/src`)

- **React 18 + Vite + Tailwind + react-router-dom + axios**.
- `services/api.js` — axios instance, base `/api`, sends same-site cookies, auto-refreshes on 401, calls cookie-clearing logout, then redirects to `/login`. Exports auth/analysis/history wrappers.
- `hooks/useAuth.jsx` — AuthProvider context (user state, login/register/logout).
- `components/` — `Navbar`, `Footer`, `ProtectedRoute`, `Dropzone`, `GaugeChart`, `MetricBar`, `UsageBar`, `LoadingScreen`, `SplashScreen`.
- `pages/` — Public: `LandingPage`, `LoginPage`, `RegisterPage`, `Termos`, `Privacidade`, `LimitacoesIA`. Protected (`ProtectedRoute` + Navbar): `Home`, `Dashboard`, `HistoryPage`, `ReportPage` (incl. `/report/:id`), `PricingPage`, `Missao`, `Sugestoes`.
- `App.jsx` — route table; splash screen shows 2.5s on load.

---

## Data Model (PostgreSQL)

```
users (id UUID, google_id?, email UNIQUE, hashed_password?, name, avatar_url?, tier, is_active, last_login?, created_at, updated_at)
  └── verifications (id, user_id FK, content_type[Text|Image|Audio|Video], source_url?, file_hash_md5?, verdict_score, verdict_label, ai_summary?, raw_result JSON, created_at)
        ├── analysis_metrics (id, verification_id FK, sightengine_ai_score?, sightengine_deepfake_score?, huggingface_model_score?, text_ai_probability?, earliest_known_date?)
        └── cache_registry (file_hash_md5 PK, cached_verdict_id FK, expires_at)
```

Tables auto-created at startup via SQLAlchemy `Base.metadata.create_all`.

---

## Docker Compose

- **db**: postgres:16-alpine, healthcheck via pg_isready.
- **backend**: builds `./backend`, volume-mounts code, runs `uvicorn app.main:app --reload`, `env_file: ./backend/.env`, waits for healthy db.
- **frontend**: `Dockerfile.dev`, Vite dev server on 5173, `VITE_API_PROXY_TARGET=http://backend:8000`, anonymous node_modules volume.

---

## Key Config (.env, backend/)

`GEMINI_API_KEY`, `GEMINI_MODEL_NAME`, `SIGHTENGINE_API_USER/SECRET`, `HUGGINGFACE_API_TOKEN`, `SERPAPI_KEY`, `GPTZERO_API_KEY`, `GOOGLE_CLIENT_ID`, `JWT_SECRET`, `DATABASE_URL`, `CORS_ORIGINS`, `COOKIE_SECURE`.

See `README.md` for the full list and docker-compose for wiring.
