<div align="center">

# AlgoLog

**Self-rate your CP submissions, revisit what didn't stick.**

Log every LeetCode / Codeforces / CodeChef / AtCoder / GFG problem you attempt with a 1–5
difficulty score and an honest "did I actually solve this myself?" flag. AlgoLog finds
problems similar to ones you struggled with, resurfaces weak ones on a spaced-repetition
schedule, and emails a weekly digest — no cloud API keys, no data leaving your machine.

[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue?style=flat-square&logo=react)](https://react.dev)
[![Postgres](https://img.shields.io/badge/PostgreSQL-16%20+%20pgvector-336791?style=flat-square&logo=postgresql)](https://github.com/pgvector/pgvector)
[![MCP](https://img.shields.io/badge/MCP-server-purple?style=flat-square)](https://modelcontextprotocol.io)
[![backend-tests](https://github.com/trimoyee-g/AlgoLog/actions/workflows/backend-tests.yml/badge.svg)](https://github.com/trimoyee-g/AlgoLog/actions/workflows/backend-tests.yml)

[Architecture](docs/architecture.md) ·
[API Reference](docs/api-reference.md) ·
[MCP Server](docs/mcp-server.md) ·
[Environment Variables](docs/environment-variables.md) ·
[Testing](docs/testing.md) ·
[Design Decisions](docs/design-decisions.md)

</div>

---

## Overview

Three ways in, one brain behind them:

- **Browser extension** — click the toolbar icon on a problem page and rate the submission
  you just made. The platform is inferred from the tab URL.
- **React dashboard** — add, edit, and filter problems, find similar ones, work the review
  queue, and see what to revisit next with the reason it was picked.
- **MCP server** — ask Claude _"what should I revisit next?"_ and let it call your tracker
  as tools.

Everything that guides your practice is deterministic: embeddings run in-process via
`sentence-transformers`, and the SM-2 scheduler, weak-topic detection, and recommender are
plain rules — so every suggestion is reproducible. Auth is delegated to Supabase (JWT); the
backend verifies tokens against the project JWKS and never stores a password.

An **optional local LLM** (Ollama) enriches the weekly digest with a personalized paragraph,
study tips, and web-searched practice problems. It only ever _appends_ to an already-complete
email and falls back cleanly when unset or unreachable.

Full system diagram, data model, and sequence diagrams: [docs/architecture.md](docs/architecture.md).

## Features

| Feature                  | How it works                                                                                                                                                  |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Self-rating**          | Each attempt logs a 1–5 score, a `solved_self` flag, tags, and notes. Repeat attempts are kept as history, never overwritten.                                  |
| **Similarity search**    | Tags are embedded with `all-MiniLM-L6-v2` into pgvector; "find similar" returns the closest matches from _your own_ history.                                   |
| **Spaced repetition**    | An SM-2 variant folded over the immutable attempt log — a struggle resets the interval to 1 day, clean recalls stretch it (1 → 6 → ×ease). No scheduler state. |
| **Weak-topic detection** | Per tag, the 90-day solved-unaided rate. Weak = below 50% _and_ ≥3 attempts, so one bad problem never brands a topic.                                          |
| **Recommend next**       | Merges due reviews and weak topics into one ranked list; `high` priority means overdue **and** weak. Each carries a plain-English `reason`.                    |
| **Weekly digest**        | An APScheduler job emails a Sunday summary over SMTP: week stats with trend, top-5 due problems, and a coach note. Also triggerable from the dashboard.        |
| **Digest enrichment**    | _Optional._ With `OLLAMA_MODEL` set, a local LLM appends tips and web-searched problems (keyless `ddgs`). Any failure sends the plain digest.                  |
| **MCP tools**            | Query the tracker from any MCP client: weak problems, overall stats, and the reasoned "recommend next".                                                        |

## Getting Started

**Prerequisites:** Docker Desktop · Node 18+ · a free [Supabase](https://supabase.com) project.

### 1. Backend

```bash
cp .env.example .env                  # Postgres user/password/db — no defaults, compose won't start without them
cp backend/.env.example backend/.env  # set SUPABASE_PROJECT_URL (required); SMTP_* for the weekly email

docker compose up -d --build          # runs `alembic upgrade head`, then serves
```

Verify: `http://localhost:8000/health` → `{"status":"ok"}` · Docs: `/docs`

Compose also starts an **Ollama** service for digest enrichment and sets `OLLAMA_MODEL=llama3.1`.
Pull the model once — `docker compose exec ollama ollama pull llama3.1` (~4.7GB) — or set
`OLLAMA_MODEL: ""` in `docker-compose.yml` to leave enrichment off. Everything else works either way.

The schema is owned by Alembic, not the app. The container migrates on boot; by hand:
`docker compose exec backend alembic upgrade head`. Upgrading a deployment that predates
migrations: `alembic stamp 0001` once, then `upgrade head`.

### 2. Dashboard

```bash
cd frontend
cp .env.example .env   # VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
npm install && npm run dev   # http://localhost:5173
```

### 3. Extension

Go to `chrome://extensions` → **Developer mode** → **Load unpacked** → select `extension/`.
Log in on the dashboard and the extension picks up that session automatically via its bridge
content script. Then click the toolbar icon on any problem page to rate it.

It's manifest-v3 and cross-browser (Chrome / Edge / Firefox / Safari). It never bundles the
Supabase SDK or calls Supabase itself — see [Design Decisions](docs/design-decisions.md).

### 4. MCP server (optional)

Ask Claude what to revisit next without opening the dashboard — hosted (recommended) or
stdio setup, both covered in [docs/mcp-server.md](docs/mcp-server.md).

## Reference

| Topic                    | Doc                                              |
| ------------------------- | ------------------------------------------------- |
| System diagram, data model, sequence flows | [docs/architecture.md](docs/architecture.md) |
| REST endpoints             | [docs/api-reference.md](docs/api-reference.md)     |
| MCP tools & setup           | [docs/mcp-server.md](docs/mcp-server.md)           |
| Config & env vars          | [docs/environment-variables.md](docs/environment-variables.md) |
| Test suite                 | [docs/testing.md](docs/testing.md)                 |
| Why it's built this way    | [docs/design-decisions.md](docs/design-decisions.md) |

## Testing

```bash
cd backend
pip install -r requirements-dev.txt
pytest tests/unit
```

Full suite (unit, integration, E2E) and CI details: [docs/testing.md](docs/testing.md).

## Contributing

Contributions are welcome. Open an issue first for anything large or design-changing.
