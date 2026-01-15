"""SSE streaming utilities."""
import json
from typing import AsyncGenerator
from schemas.qa import StreamingChunk


async def stream_markdown_chunks(markdown: str, chunk_size: int = 50) -> AsyncGenerator[str, None]:
    """
    Split markdown into chunks and stream as SSE.
    
    Args:
        markdown: Complete markdown string to stream
        chunk_size: Number of characters per chunk
        
    Yields:
        SSE-formatted strings: "data: {...}\n\n"
    """
    for i in range(0, len(markdown), chunk_size):
        chunk = markdown[i:i + chunk_size]
        chunk_data = StreamingChunk(chunk=chunk)
        yield f"data: {chunk_data.model_dump_json()}\n\n"
    
    # Send completion signal
    yield "data: [DONE]\n\n"
