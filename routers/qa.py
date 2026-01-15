"""QA router for question answering endpoint."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from schemas.qa import QuestionRequest
from services.qa_service import process_question_stream

router = APIRouter()


@router.post("/answer")
async def answer_question(request: QuestionRequest):
    """
    Streaming SSE endpoint for Q&A.
    
    Accepts a question and streams the answer as Server-Sent Events (SSE).
    The response is markdown that streams in real-time as chunks.
    """
    try:
        return StreamingResponse(
            process_question_stream(request.question),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
