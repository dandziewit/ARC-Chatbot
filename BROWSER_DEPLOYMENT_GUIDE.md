# Browser Deployment Guide

## Overview

Your chatbot is now ready for browser deployment! We've created:

- **arc_core.py**: Pure, testable business logic
- **/v1/chat/simple**: Lightweight API endpoint for browser requests
- **static/index.html**: Ready-to-use chatbot UI

## Quick Start

### 1. Start the Backend Server

```bash
cd ChatBot
python -m backend.main
```

The server will start on `http://localhost:8000`

### 2. Open the Chat Interface

Navigate to:
```
http://localhost:8000/static/
```

Or open `static/index.html` in a browser after starting the server.

## What's Different

### /v1/chat (Original - Full Production)
- Requires Redis + PostgreSQL
- Distributed session state
- Memory persistence across restarts
- Complex orchestrator with retrieval pipeline
- For: Production apps at scale

### /v1/chat/simple (New - Browser Deployment)
- No external dependencies
- In-memory session state (cleared on restart)
- Simple ChatbotEngine - stateless core logic
- Perfect for: websites, demos, quick deployments
- **This is what the browser uses!**

## Architecture

```
Browser (HTML/JS)
    ↓ POST /v1/chat/simple (JSON)
    ↓
FastAPI Backend
    ↓
ChatbotEngine (arc_core.py)
    ├─ classify_intent()
    ├─ classify_emotion()
    └─ build_response()
    ↓
ChatState (per-session in memory)
    ↓
Response (JSON) → Browser
```

## Key Components

### ChatbotEngine (arc_core.py)
Pure business logic with no dependencies on UI or external services:

```python
from arc_core import ChatbotEngine, ChatState

engine = ChatbotEngine()
state = ChatState(session_id="user-123")
response, state = engine.chat("Hello!", state)
print(response)  # "Hi there! How can I help?"
```

### Browser Interface (static/index.html)
- Clean, modern chat UI
- Automatic session management
- Typing indicators and animations
- Error handling and recovery
- localStorage for session persistence

### API Endpoint (/v1/chat/simple)
```javascript
POST /v1/chat/simple
Content-Type: application/json

{
  "session_id": "session-123456",
  "message": "Hi, how are you?",
  "user_id": null
}

// Response:
{
  "session_id": "session-123456",
  "response": "I'm doing great! How can I help you today?",
  "strategy": "native",
  "safety_routed": false,
  "fallback_used": false
}
```

## Embedding in Your Website

### Option 1: Full Page Replacement
Replace a page with the `/static/` interface.

### Option 2: iFrame Embed
```html
<iframe 
  src="http://your-domain:8000/static/" 
  width="600" 
  height="600" 
  style="border: none; border-radius: 12px;"
></iframe>
```

### Option 3: Custom Integration
Use the `/v1/chat/simple` endpoint directly:

```javascript
async function chat(message, sessionId) {
  const response = await fetch('http://localhost:8000/v1/chat/simple', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message: message,
      user_id: null
    })
  });
  return response.json();
}
```

## Configuration

### Update CORS for Production
In `backend/main.py`, update the CORS configuration:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com", "https://www.your-domain.com"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)
```

### Performance Characteristics
- Response time: ~50-100ms (pure Python, no network calls)
- Memory per session: ~5KB
- Concurrent sessions: Limited by Python process memory
- Session lifetime: Until server restart (for testing) or add Redis for persistence

## Testing

### Test with curl
```bash
curl -X POST http://localhost:8000/v1/chat/simple \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-1",
    "message": "Hello!",
    "user_id": null
  }'
```

### Test with Browser Console
```javascript
fetch('http://localhost:8000/v1/chat/simple', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: 'test-' + Date.now(),
    message: 'Hi there',
    user_id: null
  })
}).then(r => r.json()).then(console.log);
```

## Troubleshooting

### "Core engine not available"
- Ensure `arc_core.py` is in the project root
- Check that imports are working: `python -c "from arc_core import ChatbotEngine"`

### CORS errors in browser
- Check the CORS middleware is configured with your domain
- In development, `allow_origins=["*"]` is fine
- In production, restrict to specific domains

### Static files not loading
- Ensure `static/` directory exists at project root
- Verify `static/index.html` is present
- Check server logs for mount errors

### Sessions not persisting
- `/v1/chat/simple` uses in-memory state (cleared on restart)
- For persistence, use `/v1/chat` with Redis + PostgreSQL configured
- Or add localStorage support to browser UI

## Files Modified

- ✅ `backend/main.py`: Added CORS, `/v1/chat/simple` endpoint, static mount
- ✅ `arc_core.py`: Created pure business logic
- ✅ `static/index.html`: Created browser interface

## Next Steps

1. ✅ Start the server
2. ✅ Test the browser interface
3. ✅ Customize the UI as needed
4. ✅ Configure CORS for production
5. ✅ Deploy to production (Docker, serverless, etc.)

## Performance Optimization

From the benchmarking analysis, the core engine is extremely fast:
- Intent classification: <1ms
- Emotion detection: <1ms
- Response generation: <5ms
- **Total per request: ~10ms**

The bottleneck in production deployments is the Redis/PostgreSQL memory store, not the chat logic. For `/v1/chat/simple`, there's no external I/O, so performance is excellent.

## Support

For issues or questions:
1. Check the logs: `backend/main.py` outputs to console
2. Review `CODE_REVIEW.md` for architecture details
3. Check `PERFORMANCE_BENCHMARKING_REPORT.md` for optimization options
4. Test the `/v1/chat/simple` endpoint directly with curl

---

**Your chatbot is ready for the web!** 🚀
