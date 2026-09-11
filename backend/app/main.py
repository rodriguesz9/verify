from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
import os

load_dotenv()

from app.api import check_text, check_url, upload, auth, history, whatsapp, verificacao
from app.core.database import init_db

# ── Rate limiter (IP-based via slowapi) ───────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Verify API",
    description="Sistema Inteligente de Checagem de Fatos, Proteção contra Golpes e Auditoria Digital",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app" if origins == ["*"] or any("localhost" in o for o in origins) else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Security headers ─────────────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"]    = "nosniff"
    response.headers["X-Frame-Options"]           = "DENY"
    response.headers["X-XSS-Protection"]          = "1; mode=block"
    response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
    return response

# ── Startup: create DB tables ─────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await init_db()

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,        prefix="/api",     tags=["Auth"])
app.include_router(check_text.router,  prefix="/api",     tags=["Analysis"])
app.include_router(check_url.router,   prefix="/api",     tags=["Analysis"])
app.include_router(upload.router,      prefix="/api",     tags=["Analysis"])
app.include_router(history.router,     prefix="/api",     tags=["History"])
app.include_router(whatsapp.router,    prefix="/api",     tags=["WhatsApp"])
app.include_router(verificacao.router, prefix="/api",     tags=["Verificacao & Banca"])
app.include_router(verificacao.router,                    tags=["Verificacao & Banca"])

# ── Login rate-limit endpoint (5 attempts per 15 min per IP) ─────────────────
@app.post("/api/auth/login-rl")
@limiter.limit("5/15minutes")
async def login_rate_limited(request: Request):
    """Thin wrapper — actual logic is in auth router. This endpoint is rate-limited."""
    return JSONResponse({"detail": "Use POST /api/auth/login"})

@app.get("/", tags=["Health"])
def root():
    return {"status": "online", "service": "Verify v1.0", "app": "Verify"}

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "Verify"}
