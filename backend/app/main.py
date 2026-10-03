from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import os

load_dotenv()

from app.api import check_text, check_url, upload, auth, history, whatsapp, verificacao
from app.core.database import init_db, engine
from app.core.rate_limit import limiter
from app.core.request_budget import RequestBudgetMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(
    title="Verify API",
    description="Sistema Inteligente de Checagem de Fatos, Proteção contra Golpes e Auditoria Digital",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
configured_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
).split(",")
origins = [origin.strip() for origin in configured_origins if origin.strip() and origin.strip() != "*"]
origin_regex = os.getenv("CORS_ORIGIN_REGEX") or None

# Never turn a legacy wildcard into permission for EVERY Vercel customer.
# Configure exact owned domains (or an explicit, narrowly scoped regex).
app.add_middleware(RequestBudgetMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=origin_regex,
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

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,        prefix="/api",     tags=["Auth"])
app.include_router(check_text.router,  prefix="/api",     tags=["Analysis"])
app.include_router(check_url.router,   prefix="/api",     tags=["Analysis"])
app.include_router(upload.router,      prefix="/api",     tags=["Analysis"])
app.include_router(history.router,     prefix="/api",     tags=["History"])
app.include_router(whatsapp.router,    prefix="/api",     tags=["WhatsApp"])
app.include_router(verificacao.router, prefix="/api",     tags=["Verificação forense"])

@app.get("/", tags=["Health"])
def root():
    return {"status": "online", "service": "Verify v1.0", "app": "Verify"}

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "Verify"}


@app.get("/api/capabilities", tags=["Health"])
def capabilities():
    from app.services.capabilities import capability_report
    return capability_report()
