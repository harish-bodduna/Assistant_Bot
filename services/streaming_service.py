"""SSE streaming utilities."""
import json
from typing import AsyncGenerator
from schemas.qa import StreamingChunk


async def stream_markdown_chunks(markdown: str, chunk_size: int = 200) -> AsyncGenerator[str, None]:
    """
    Split markdown into chunks and stream as SSE.
    
    Args:
        markdown: Complete markdown string to stream
        chunk_size: Number of characters per chunk
        
    Yields:
        SSE-formatted strings: "data: {...}\n\n"
    """
    if not markdown:
        yield "data: [DONE]\n\n"
        return
    
    # Stream in larger chunks for better performance
    for i in range(0, len(markdown), chunk_size):
        chunk = markdown[i:i + chunk_size]
        chunk_data = StreamingChunk(chunk=chunk)
        # Ensure proper SSE format with double newline
        # Use model_dump_json() to get properly escaped JSON
        json_str = chunk_data.model_dump_json()
        yield f"data: {json_str}\n\n"
    
    # Send completion signal
    yield "data: [DONE]\n\n"
