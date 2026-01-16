"""FastAPI application setup."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import qa, ingestion, health

app = FastAPI(
    title="1440 Bot API",
    description="API for document ingestion and QA retrieval",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(qa.router, prefix="/api/qa", tags=["QA"])
app.include_router(ingestion.router, prefix="/api/ingest", tags=["Ingestion"])
app.include_router(health.router, tags=["Health"])
