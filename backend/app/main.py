import logging
import os
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import label, registry, reports, sgr
from app.config import settings
from app.database import create_tables

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await create_tables()
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Failed to create tables: {e}")
    yield


app = FastAPI(
    lifespan=lifespan,
    title="LabelCheck API",
    description="Сервис проверки этикеток БАД на соответствие законодательству РФ/ЕАЭС",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    logging.error("Unhandled: %s\n%s", exc, "".join(tb))
    return JSONResponse(status_code=500, content={"detail": str(exc), "trace": "".join(tb[-3:])})

app.include_router(sgr.router, prefix="/api/v1")
app.include_router(label.router, prefix="/api/v1")
app.include_router(registry.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")

# Serve uploaded files (labels, SGR documents) as static files
os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.get("/")
async def root():
    return {
        "service": "LabelCheck",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug/db")
async def debug_db():
    """Test DB connection with raw asyncpg to diagnose SSL issues."""
    import asyncpg
    import ssl as ssl_mod
    from app.config import settings

    results = {}
    db_url = settings.database_url
    # Convert SQLAlchemy URL to plain postgres URL
    raw_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    if "?" in raw_url:
        raw_url = raw_url.split("?")[0]

    results["url_host"] = raw_url.split("@")[1].split("/")[0] if "@" in raw_url else "unknown"

    # Test 1: no SSL
    try:
        conn = await asyncpg.connect(raw_url, timeout=10)
        count = await conn.fetchval("SELECT count(*) FROM verification_reports")
        await conn.close()
        results["no_ssl"] = f"OK, count={count}"
    except Exception as e:
        results["no_ssl"] = str(e)

    # Test 2: ssl=True
    try:
        conn = await asyncpg.connect(raw_url, ssl=True, timeout=10)
        count = await conn.fetchval("SELECT count(*) FROM verification_reports")
        await conn.close()
        results["ssl_true"] = f"OK, count={count}"
    except Exception as e:
        results["ssl_true"] = str(e)

    # Test 3: custom SSLContext CERT_NONE
    try:
        ctx = ssl_mod.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl_mod.CERT_NONE
        conn = await asyncpg.connect(raw_url, ssl=ctx, timeout=10)
        count = await conn.fetchval("SELECT count(*) FROM verification_reports")
        await conn.close()
        results["ssl_ctx_none"] = f"OK, count={count}"
    except Exception as e:
        results["ssl_ctx_none"] = str(e)

    # Test 4: SSLContext PROTOCOL_TLS
    try:
        ctx2 = ssl_mod.SSLContext(ssl_mod.PROTOCOL_TLS_CLIENT)
        ctx2.check_hostname = False
        ctx2.verify_mode = ssl_mod.CERT_NONE
        conn = await asyncpg.connect(raw_url, ssl=ctx2, timeout=10)
        count = await conn.fetchval("SELECT count(*) FROM verification_reports")
        await conn.close()
        results["ssl_tls_client"] = f"OK, count={count}"
    except Exception as e:
        results["ssl_tls_client"] = str(e)

    # Test 5: direct_tls
    try:
        ctx3 = ssl_mod.create_default_context()
        ctx3.check_hostname = False
        ctx3.verify_mode = ssl_mod.CERT_NONE
        conn = await asyncpg.connect(raw_url, ssl=ctx3, direct_tls=True, timeout=10)
        count = await conn.fetchval("SELECT count(*) FROM verification_reports")
        await conn.close()
        results["direct_tls"] = f"OK, count={count}"
    except Exception as e:
        results["direct_tls"] = str(e)

    return results
