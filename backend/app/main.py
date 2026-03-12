import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import label, registry, reports, sgr
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

app.include_router(sgr.router, prefix="/api/v1")
app.include_router(label.router, prefix="/api/v1")
app.include_router(registry.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")


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
