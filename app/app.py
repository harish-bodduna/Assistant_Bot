"""FastAPI application setup."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import qa, ingestion, health
# from routers.demo_qa import router as demo_qa_router  # Commented out - using main QA endpoint for demo

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
# app.include_router(demo_qa_router, prefix="/api/demo/qa", tags=["Demo QA"])  # Commented out - using main QA endpoint for demo