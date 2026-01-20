# Streaming Response Debugging

## Issue
Backend processes the request successfully (200 OK), but frontend doesn't receive the streamed response.

## Backend Status
✅ Request received: `POST /api/qa/answer` - 200 OK  
✅ LLM inference completed: 7029 tokens used  
✅ Response generated successfully  

## Possible Issues

### 1. Frontend SSE Parsing
The frontend needs to properly parse Server-Sent Events. Check if your frontend code is:

```javascript
// Example correct SSE handling
const eventSource = new EventSource('/api/qa/answer'); // ❌ Wrong - EventSource only supports GET

// Correct approach for POST with SSE:
const response = await fetch('/api/qa/answer', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: 'your question' })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6); // Remove 'data: '
      if (data === '[DONE]') {
        // Stream complete
        break;
      }
      try {
        const parsed = JSON.parse(data);
        // Handle chunk: parsed.chunk
        console.log('Chunk:', parsed.chunk);
      } catch (e) {
        console.error('Parse error:', e);
      }
    }
  }
}
```

### 2. SSE Format Verification
The backend sends:
```
data: {"chunk":"text here"}\n\n
data: [DONE]\n\n
```

Each chunk is a JSON object with a `chunk` field.

### 3. CORS Issues
CORS is configured in `app/app.py`. If you're still having issues, check:
- Browser console for CORS errors
- Network tab to see if OPTIONS preflight succeeds
- Response headers include `Access-Control-Allow-Origin`

### 4. Testing the Endpoint

Test with curl:
```bash
curl -N -X POST http://localhost:8000/api/qa/answer \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"question":"test question"}' \
  --no-buffer
```

You should see chunks streaming in real-time.

### 5. Check Browser Network Tab
1. Open DevTools → Network tab
2. Make a request from UI
3. Check the `/api/qa/answer` request
4. Look at:
   - Response headers (should include `Content-Type: text/event-stream`)
   - Response preview (should show streaming chunks)
   - Timing (should show streaming, not waiting for full response)

## Backend Changes Made

1. ✅ Increased chunk size from 50 to 200 characters
2. ✅ Added small delay between chunks to prevent buffering
3. ✅ Removed redundant CORS headers (handled by middleware)
4. ✅ Ensured proper SSE format with double newlines

## Next Steps

1. **Check frontend code** - Ensure it's using `fetch` with `ReadableStream`, not `EventSource`
2. **Test with curl** - Verify backend streaming works
3. **Check browser console** - Look for JavaScript errors
4. **Check network tab** - Verify response is streaming, not buffered
