"""Demo QA router for question answering with pre-written answers."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from schemas.qa import QuestionRequest
from services.demo_qa_service import process_demo_question_stream

router = APIRouter()


@router.post("/answer")
async def demo_answer_question(request: QuestionRequest):
    """
    Demo streaming SSE endpoint for Q&A using pre-written answers.
    
    Bypasses Qdrant search and uses manually created markdown answers.
    OpenAI is still called but returns the exact same content.
    
    Accepts a question and streams the answer as Server-Sent Events (SSE).
    The response is markdown that streams in real-time as chunks.
    """
    try:
        return StreamingResponse(
            process_demo_question_stream(request.question),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Demo error: {str(e)}")
