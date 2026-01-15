"""QA request/response models."""
from pydantic import BaseModel


class QuestionRequest(BaseModel):
    """Request model for Q&A endpoint."""
    question: str


class QAResponse(BaseModel):
    """Response model for Q&A endpoint (non-streaming)."""
    success: bool
    answer_markdown: str | None
    source_file: str | None
    confidence_score: float
    error: str | None = None


class StreamingChunk(BaseModel):
    """Model for streaming SSE chunks."""
    chunk: str
