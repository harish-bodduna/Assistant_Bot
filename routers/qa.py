"""QA router for question answering endpoint."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from schemas.qa import QuestionRequest
# from services.qa_service import process_question_stream  # Commented out - using demo QA only
from services.demo_qa_service import process_demo_question_stream

router = APIRouter()


@router.post("/answer")
async def answer_question(request: QuestionRequest):
    """
    Streaming SSE endpoint for Q&A - Demo QA only.
    
    Loads markdown from local file and sends to OpenAI for echo.
    
    Accepts a question and streams the answer as Server-Sent Events (SSE).
    The response is markdown that streams in real-time as chunks.
    """
    try:
        # Always use demo QA service (loads markdown from local file)
        return StreamingResponse(
            process_demo_question_stream(request.question),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
        
        # Commented out - regular QA service (searches Qdrant 6333)
        # if needed in future, uncomment:
        # return StreamingResponse(
        #     process_question_stream(request.question),
        #     media_type="text/event-stream",
        #     headers={
        #         "Cache-Control": "no-cache, no-transform",
        #         "Connection": "keep-alive",
        #         "X-Accel-Buffering": "no",
        #     }
        # )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
