"""FastAPI application setup."""
from fastapi import FastAPI
from routers import qa, ingestion, health

app = FastAPI(
    title="1440 Bot API",
    description="API for document ingestion and QA retrieval",
    version="2.0.0"
)

# Include routers
app.include_router(qa.router, prefix="/api/qa", tags=["QA"])
app.include_router(ingestion.router, prefix="/api/ingest", tags=["Ingestion"])
app.include_router(health.router, tags=["Health"])
