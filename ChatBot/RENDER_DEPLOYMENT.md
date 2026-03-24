# Render Deployment

## What This Deploys

This project can be deployed to Render as a Python web service using the existing FastAPI app in [backend/main.py](backend/main.py).

The deployed app will serve:

- `/` for the browser chat page
- `/static` for frontend assets
- `/v1/chat/simple` for lightweight chatbot requests
- `/healthz` for health checks

## Important Limitation

The current browser chatbot path uses in-memory session state in `/v1/chat/simple`.

That means:

- conversations are preserved only while the instance stays alive
- a restart or cold start clears session memory
- this is fine for demos and public sharing
- this is not long-term persistent chat memory

If you want persistent sessions and memory across restarts, move to `/v1/chat` with Redis and Postgres enabled.

## Deploy Steps

1. Push this repository to GitHub.
2. In Render, create a new `Blueprint` deployment from the repository.
3. Render will detect [render.yaml](render.yaml).
4. Deploy the web service.
5. Open the generated Render URL.

## Manual Render Settings

If you do not use Blueprint deployment, create a `Web Service` with these values:

- Build Command: `pip install -r requirements-backend.txt`
- Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/healthz`

Recommended environment variables:

- `ARC_ENV=production`
- `ARC_HOST=0.0.0.0`
- `ARC_PORT=10000`
- `ARC_USE_REDIS_SESSIONS=false`
- `ARC_USE_POSTGRES_MEMORY=false`
- `ARC_ENABLE_TOOL_ROUTER=true`
- `ARC_ENABLE_CRISIS_GUARDRAILS=true`

## Free Tier Behavior

On Render free instances, the service can spin down after inactivity.

That means:

- the first request after idle can be slow
- in-memory chat sessions can reset
- the bot is public, but not truly always hot

If you want the bot to feel always available, use a paid Render instance or add persistent backing services.

## Local Verification

Run locally with:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Then open:

```text
http://localhost:8000/
```

## Next Upgrade Path

For a more production-ready deployment on Render:

1. Add a managed Redis instance for shared session state.
2. Add a managed Postgres instance for durable memory.
3. Restrict CORS in [backend/main.py](backend/main.py).
4. Move browser traffic from `/v1/chat/simple` to `/v1/chat`.