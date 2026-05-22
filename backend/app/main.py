from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
import os

load_dotenv()

from app.api import check_text, check_url, upload, auth, history
from app.core.database import init_db

# ── Rate limiter (IP-based via slowapi) ───────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="VerifAI API",
    description="Sistema de Auditoria Digital e Combate à Desinformação",
    version="0.2.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    response.headers["Permissions-Policy"]        = "geolocation=(), microphone=(), camera=()"
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

# ── Login rate-limit endpoint (5 attempts per 15 min per IP) ─────────────────
@app.post("/api/auth/login-rl")
@limiter.limit("5/15minutes")
async def login_rate_limited(request: Request):
    """Thin wrapper — actual logic is in auth router. This endpoint is rate-limited."""
    return JSONResponse({"detail": "Use POST /api/auth/login"})

@app.get("/", tags=["Health"])
def root():
    return {"status": "online", "service": "VerifAI v0.2"}

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
