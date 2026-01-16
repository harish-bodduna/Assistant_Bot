"""QA business logic service."""
import asyncio
import json
from typing import AsyncGenerator
from src.retrieval.multimodal_service import hybrid_search, get_1440_response
from services.streaming_service import stream_markdown_chunks


async def process_question_stream(question: str) -> AsyncGenerator[str, None]:
    """
    Orchestrates search + LLM + streaming.
    
    Flow:
    1. Search Qdrant for relevant documents
    2. Call LLM with retrieved context
    3. Stream markdown response as SSE chunks
    
    Args:
        question: User's question
        
    Yields:
        SSE-formatted strings with markdown chunks
    """
    try:
        # 1. Search Qdrant (run in thread pool since it's synchronous)
        loop = asyncio.get_event_loop()
        retrieval_data = await loop.run_in_executor(None, hybrid_search, question)
        
        if not retrieval_data.get("text"):
            error_msg = retrieval_data.get("error") or "No relevant documents found"
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
            return
        
        # 2. Call LLM (run in thread pool since it's synchronous)
        answer_markdown = await loop.run_in_executor(
            None, 
            get_1440_response, 
            question, 
            retrieval_data
        )
        
        if not answer_markdown:
            yield f"data: {json.dumps({'error': 'Failed to generate response'})}\n\n"
            return
        
        # 3. Stream markdown chunks immediately
        # Start streaming as soon as we have the answer
        async for chunk in stream_markdown_chunks(answer_markdown):
            yield chunk
            # Small delay to ensure chunks are sent (optional, helps with buffering)
            await asyncio.sleep(0.01)
            
    except Exception as e:
        # Stream error as SSE
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
