from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from natubot_core.settings import get_settings, PROJECT_ROOT
from natubot_core.gemini_client import GeminiClient
from natubot_core.pinecone_client import PineconeClients
from natubot_core.rag import answer_with_rag
from natubot_core.kiosk_registry import load_kiosk_registry, verify_kiosk, get_kiosk_info
from natubot_core.logging_utils import setup_json_logger, log_event

settings = get_settings()

app = FastAPI(title="NatuBot Backend (Gemini + Pinecone)", version="0.6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Clients (singletons)
gemini = GeminiClient(
    api_key=settings.gemini_api_key,
    chat_model=settings.gemini_chat_model,
    embed_model=settings.gemini_embed_model,
    embed_dim=settings.embed_dim,
)

pinecone = PineconeClients(
    api_key=settings.pinecone_api_key,
    index_name=settings.pinecone_index_name,
    index_host=settings.pinecone_index_host,
)

# Kiosk registry
_registry_path = Path(settings.kiosk_registry_file)
if not _registry_path.is_absolute():
    _registry_path = PROJECT_ROOT / _registry_path
kiosk_registry = load_kiosk_registry(_registry_path)

# Logging
_log_dir = Path(settings.log_dir)
if not _log_dir.is_absolute():
    _log_dir = PROJECT_ROOT / _log_dir
logger = setup_json_logger(_log_dir, level=settings.log_level)

# Rate limiting (in-memory; ok for MVP single instance)
_rate_store = defaultdict(lambda: deque())

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=settings.max_message_chars)
    accepted_terms: bool = Field(False)
    accepted_terms_version: Optional[str] = None
    session_id: Optional[str] = None
    top_k: int = Field(settings.default_top_k, ge=1, le=settings.max_top_k)
    pinecone_filter: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    answer: str
    citations: list
    used_context: bool

def _device_id(request: Request) -> str:
    return (request.headers.get("x-device-id") or "").strip() or "unknown"

def _token(request: Request) -> str:
    tok = (request.headers.get("x-kiosk-token") or "").strip()
    if tok:
        return tok
    auth = (request.headers.get("authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return ""

def _require_kiosk(request: Request) -> Dict[str, Any]:
    did = _device_id(request)

    if not settings.require_kiosk_auth:
        return {"device_id": did, "kiosk": get_kiosk_info(did, kiosk_registry) or {}, "auth_ok": True}

    if did == "unknown":
        raise HTTPException(status_code=401, detail="Missing X-Device-Id.")
    tok = _token(request)
    if not tok:
        raise HTTPException(status_code=401, detail="Missing kiosk token (X-Kiosk-Token or Authorization Bearer).")
    if not verify_kiosk(did, tok, kiosk_registry):
        raise HTTPException(status_code=401, detail="Invalid kiosk credentials.")
    return {"device_id": did, "kiosk": get_kiosk_info(did, kiosk_registry) or {}, "auth_ok": True}

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.time()

    did = _device_id(request)
    client_ip = request.client.host if request.client else "unknown"
    status = 500

    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-Id"] = request_id
        return response
    finally:
        elapsed_ms = int((time.time() - start) * 1000)
        kiosk_info = get_kiosk_info(did, kiosk_registry) or {}
        log_event(logger, {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": status,
            "elapsed_ms": elapsed_ms,
            "client_ip": client_ip,
            "device_id": did,
            "kiosk_location": kiosk_info.get("location"),
            "kiosk_name": kiosk_info.get("name"),
        })

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path != "/chat":
        return await call_next(request)

    did = _device_id(request)
    client_ip = request.client.host if request.client else "unknown"
    key = did if did != "unknown" else client_ip

    now = time.time()
    window = settings.rate_limit_window_sec
    limit = settings.rate_limit_rpm

    dq = _rate_store[key]
    while dq and (now - dq[0]) > window:
        dq.popleft()

    if len(dq) >= limit:
        retry_after = max(1, int(window - (now - dq[0])))
        return JSONResponse(
            status_code=429,
            content={"ok": False, "error": "Rate limit exceeded", "retry_after_sec": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    dq.append(now)
    return await call_next(request)

@app.get("/")
def root():
    return {"ok": True, "message": "NatuBot backend running. See /docs, /terms, /config."}

@app.get("/config")
def get_config(request: Request):
    did = _device_id(request)
    info = get_kiosk_info(did, kiosk_registry) or {}

    payload = {
        "ok": True,
        "bot_name": settings.bot_name,
        "offline_message": settings.offline_message,
        "max_message_chars": settings.max_message_chars,
        "welcome_message": settings.welcome_message,
        "welcome_message_version": settings.welcome_message_version,
        "terms_version": settings.terms_version,
        "rate_limit_rpm": settings.rate_limit_rpm,
        "rate_limit_window_sec": settings.rate_limit_window_sec,
    }
    if info:
        payload["kiosk"] = {"device_id": did, "name": info.get("name"), "location": info.get("location")}
    return payload

@app.get("/terms")
def get_terms():
    try:
        terms_path = Path(settings.terms_file)
        if not terms_path.is_absolute():
            terms_path = PROJECT_ROOT / terms_path
        if not terms_path.exists():
            return JSONResponse(status_code=500, content={"ok": False, "error": f"No se encontró TERMS_FILE: {terms_path}"})
        text = terms_path.read_text(encoding="utf-8")
        return {"ok": True, "version": settings.terms_version, "content_markdown": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})

@app.get("/health")
def health():
    # JSON-safe health check
    try:
        _ = pinecone.stats(namespace=settings.pinecone_namespace)
        return {"ok": True, "pinecone_namespace": settings.pinecone_namespace}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request) -> ChatResponse:
    _ = _require_kiosk(request)

    if not req.accepted_terms:
        raise HTTPException(status_code=412, detail="Debes aceptar términos y condiciones para continuar.")
    if req.accepted_terms_version != settings.terms_version:
        raise HTTPException(status_code=412, detail="Debes aceptar la versión actual de términos y condiciones antes de continuar.")

    try:
        result = answer_with_rag(
            question=req.message,
            gemini=gemini,
            pinecone=pinecone,
            namespace=settings.pinecone_namespace,
            top_k=req.top_k,
            bot_name=settings.bot_name,
            pinecone_filter=req.pinecone_filter,
        )
        return ChatResponse(answer=result["answer"], citations=result["citations"], used_context=result["used_context"])
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"No fue posible responder en este momento: {str(e)}")
