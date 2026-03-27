# Napkin Runbook

## Curation Rules
- Re-prioritize on every read.
- Keep recurring, high-value notes only.
- Max 10 items per category.
- Each item includes date + "Do instead".

## Execution & Validation (Highest Priority)
1. **[2026-03-27] Backend local default is `8010`, not `8000`**
   Do instead: use `uvicorn main:app --host 0.0.0.0 --port 8010 --reload` and point local clients to `http://localhost:8010`.
2. **[2026-03-27] FastAPI startup seeds and initializes SQLite automatically**
   Do instead: let the app create `data/imoveis.db` on startup instead of preparing a separate local database service.

## Shell & Command Reliability
1. **[2026-03-27] Frontend dev server expects backend through Vite proxy**
   Do instead: run `npm run dev` on `8080` and keep `VITE_BACKEND_URL` aligned with the backend port so `/webhook`, `/health`, and `/imoveis` proxy correctly.
2. **[2026-03-27] `scripts/frontend_cli.py` defaults to backend `8000`**
   Do instead: export `BACKEND_URL=http://localhost:8010` in the shell or pass `backend_url` explicitly before using the CLI against local dev.

## Domain Behavior Guardrails
1. **[2026-03-27] WhatsApp integration is safe by default in local dev**
   Do instead: keep `DISABLE_WHATSAPP_SEND=true` unless you intentionally configure real WhatsApp credentials.

## User Directives
