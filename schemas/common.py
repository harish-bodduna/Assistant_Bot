"""Common Pydantic models."""
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response model."""
    success: bool = False
    error: str


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
