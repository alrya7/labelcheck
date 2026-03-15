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
    from sqlalchemy import text
    from app.database import async_session
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT count(*) FROM verification_reports"))
            count = result.scalar()
            cols = await session.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='verification_reports' ORDER BY ordinal_position"
            ))
            return {"count": count, "columns": [r[0] for r in cols.fetchall()]}
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()[-500:]}
