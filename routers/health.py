"""Health check router."""
from fastapi import APIRouter
from schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "1440-bot-api"}
