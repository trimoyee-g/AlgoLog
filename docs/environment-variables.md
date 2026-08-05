# Environment Variables

## Backend — `backend/.env`

See `backend/.env.example` for the annotated list.

| Variable                       | Default                      | Description                                                                                       |
| ------------------------------- | ----------------------------- | --------------------------------------------------------------------------------------------------- |
| `SUPABASE_PROJECT_URL`         | **required**                  | Supabase project whose JWKS verifies tokens. No default — the backend refuses to boot without it   |
| `DATABASE_URL`                 | local Postgres                | Postgres + pgvector connection (compose overrides the host to `postgres`)                          |
| `FRONTEND_ORIGIN`               | `http://localhost:5173`       | CORS origin for the dashboard                                                                       |
| `MCP_PUBLIC_URL`                | `http://localhost:8000`       | Public URL the hosted MCP server advertises as its resource identifier                              |
| `EMBEDDING_MODEL` / `_DIM`     | `all-MiniLM-L6-v2` / `384`    | Must match each other; changing the dim needs a migration to rewrite the column                    |
| `RERANK_MODEL`                  | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Grades retrieved passages in the CRAG loop. Baked into the image — changing it needs a rebuild, and re-checking `crag.MIN_SCORE` |
| `MAX_UPLOAD_MB`                 | `20`                          | Study-material upload ceiling. A trust boundary, not a tuning knob                                  |
| `SMTP_HOST/PORT/USER/PASSWORD` | Gmail host/port, empty creds  | Weekly digest. Use a Gmail App Password; empty creds disable email. Gmail caps ~500/day            |
| `GEMINI_API_KEY`                | empty (disabled)              | Hosted chat model for the CRAG answer and digest enrichment. Set it and Gemini wins over Ollama      |
| `GEMINI_MODEL`                  | `gemini-2.5-flash`            | Only read when `GEMINI_API_KEY` is set                                                              |
| `OLLAMA_MODEL`                  | empty (disabled)              | Local fallback, used only when `GEMINI_API_KEY` is empty. Compose sets `llama3.1`                    |
| `OLLAMA_BASE_URL`               | `http://localhost:11434`      | Compose overrides this to `http://ollama:11434`; set by hand only outside compose                   |

## Root — `.env`

Read by compose, **not** the app: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` — no
defaults, so an unset secret fails loudly.

## Frontend — `frontend/.env`

`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, optional `VITE_BACKEND_URL`. The extension's
URLs live in `extension/config.js`.
