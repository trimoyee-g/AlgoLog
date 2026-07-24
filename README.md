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

## Architecture

```mermaid
flowchart TB
    subgraph clients["Clients"]
        EXT["Browser extension<br/>(MV3 · popup rate)"]
        WEB["React dashboard<br/>(Vite · TS · Tailwind)"]
        MCPC["Claude Desktop / Code<br/>(MCP client)"]
        STDIO["mcp_server.py<br/>(stdio, single-user)"]
    end

    SB[("Supabase auth<br/>issues JWTs · JWKS")]

    subgraph api["FastAPI backend :8000"]
        REST["REST routers<br/>attempts · review · similarity · stats"]
        MCPH["Hosted MCP<br/>POST /mcp (Streamable HTTP)"]
        AUTH["deps.py — verify JWT vs JWKS<br/>ES256/RS256 · upsert user"]
        SVC["Service layer<br/>problems · similarity · stats · recommend<br/>SM-2 scheduler · weak topics · embeddings"]
        JOB["APScheduler<br/>Sun 18:00 weekly digest"]
    end

    ST["sentence-transformers<br/>all-MiniLM-L6-v2 (in-process, cached)"]
    PG[("PostgreSQL 16 + pgvector<br/>users · problems · attempts · digest_sends")]
    OLL["Ollama (optional)<br/>digest enrichment"]
    DDG["ddgs web search<br/>(keyless)"]
    SMTP["SMTP → weekly email"]

    EXT -- "session via bridge<br/>content script" --> WEB
    WEB -- "OAuth" --> SB
    STDIO -- "own refresh token<br/>(mcp_login.py)" --> SB

    EXT -- "Bearer JWT" --> REST
    WEB -- "Bearer JWT" --> REST
    STDIO -- "Bearer JWT · HTTP" --> REST
    MCPC -- "Bearer JWT" --> MCPH

    REST --> AUTH
    MCPH --> AUTH
    AUTH -. "fetch public keys" .-> SB
    AUTH --> SVC
    JOB --> SVC

    SVC --> ST
    SVC --> PG
    JOB -- "at-most-once claim<br/>(digest_sends)" --> PG
    JOB --> SMTP
    JOB -. "optional" .-> OLL
    OLL -. "curates real URLs from" .-> DDG
```

Data model, plus sequence diagrams for the rate-an-attempt, weekly-digest, and
recommend-next flows: [docs/architecture.md](docs/architecture.md).

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
Supabase SDK or calls Supabase itself — see [Design Decisions](#design-decisions).

## API Reference

All endpoints require `Authorization: Bearer <supabase-jwt>`. Base URL `http://localhost:8000`.

| Method | Path                          | Description                                                                             |
| ------ | ----------------------------- | --------------------------------------------------------------------------------------- |
| POST   | `/api/attempts`               | Log an attempt (upserts the problem by user + URL, appends an attempt row)              |
| GET    | `/api/problems`               | List problems and attempts; filter by `min_rating`, `solved_self`, `platform`, `tag`    |
| PATCH  | `/api/problems/{id}`          | Update a problem; `rating` / `solved_self` update (or create) the latest attempt        |
| DELETE | `/api/problems/{id}`          | Delete a problem (attempts cascade)                                                     |
| GET    | `/api/problems/{id}/similar`  | Embedding-similar problems from your history                                            |
| GET    | `/api/review?due_only=true`   | SM-2 review queue, soonest-due first; `due_only=false` returns the whole schedule       |
| GET    | `/api/stats/overview`         | Totals: problems, attempts, solved-unaided, hard-rated (≥4)                             |
| GET    | `/api/stats/weekly`           | Last-7-days breakdown by platform and tag                                               |
| GET    | `/api/stats/weak-topics`      | Tags whose recent solved-unaided rate is below threshold, with enough samples           |
| GET    | `/api/stats/recommend?count=1`| Ranked "what to do next" — due reviews + weak topics, each with `reason` and `priority` |
| POST   | `/api/stats/digest/send-now`  | Send your weekly digest immediately                                                     |

## MCP Server

Three tools — `get_weak_problems`, `get_stats_overview`, and `get_recommended_problem` (the
reasoned "what next", ranked with `reason` and `priority`) — served two ways:

**Hosted (recommended).** `POST /mcp`, Streamable HTTP, mounted into the FastAPI app. The MCP
client owns the OAuth session and sends the user's JWT per request, so one process serves every
user and stores no token. Add the URL as a custom connector in Claude and sign in through
Supabase. In a real deployment, set `MCP_PUBLIC_URL` to the address clients actually reach —
Claude checks the token was issued for that exact URL.

**stdio (`app.mcp_server`).** One process per user, on your machine. It holds its own Supabase
refresh token rather than copying the dashboard's, because Supabase rotates and invalidates a
refresh token on every redemption — two clients sharing one would silently log each other out.

<details>
<summary>stdio setup</summary>

1. In Supabase → **Authentication → URL Configuration → Redirect URLs**, add
   `http://localhost:8765/` (the login script listens there to catch the redirect).
2. From `backend/`, run `python -m app.mcp_login`. It opens a browser to sign in and saves the
   refresh token to `~/.algolog/mcp_refresh_token`, persisting each rotation back to that file.
3. Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "algolog": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/absolute/path/to/repo/backend",
      "env": {
        "BACKEND_URL": "http://localhost:8000",
        "SUPABASE_URL": "https://<your-ref>.supabase.co",
        "SUPABASE_ANON_KEY": "<your-anon-key>"
      }
    }
  }
}
```

</details>

Then ask: _"Using algolog, what should I revisit next?"_ → _"Due for review (last solved 12
days ago, interval 14d) AND tagged 'dp', where you solve only 35% unaided."_

## Environment Variables

Backend — `backend/.env` (see `backend/.env.example` for the annotated list):

| Variable                 | Default                        | Description                                                                                    |
| ------------------------ | ------------------------------ | ---------------------------------------------------------------------------------------------- |
| `SUPABASE_PROJECT_URL`   | **required**                   | Supabase project whose JWKS verifies tokens. No default — the backend refuses to boot without it |
| `DATABASE_URL`           | local Postgres                 | Postgres + pgvector connection (compose overrides the host to `postgres`)                       |
| `FRONTEND_ORIGIN`        | `http://localhost:5173`        | CORS origin for the dashboard                                                                   |
| `MCP_PUBLIC_URL`         | `http://localhost:8000`        | Public URL the hosted MCP server advertises as its resource identifier                          |
| `EMBEDDING_MODEL` / `_DIM` | `all-MiniLM-L6-v2` / `384`   | Must match each other; changing the dim needs a migration to rewrite the column                 |
| `SMTP_HOST/PORT/USER/PASSWORD` | Gmail host/port, empty creds | Weekly digest. Use a Gmail App Password; empty creds disable email. Gmail caps ~500/day     |
| `OLLAMA_MODEL`           | empty (disabled)               | Local model for digest enrichment. Compose sets `llama3.1`; empty leaves enrichment off         |
| `OLLAMA_BASE_URL`        | `http://localhost:11434`       | Compose overrides this to `http://ollama:11434`; set by hand only outside compose               |

Root `.env` (read by compose, **not** the app): `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_DB` — no defaults, so an unset secret fails loudly.

Frontend — `frontend/.env`: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, optional
`VITE_BACKEND_URL`. The extension's URLs live in `extension/config.js`.

## Testing

A pyramid-shaped `pytest` suite in `backend/tests/`: **unit** (scheduler, recommend, weak
topics, digest, JWT, schemas — mocked or pure), **integration** (every router and the MCP
server via `TestClient` against real Postgres + pgvector, each test rolled back), and one
**E2E** journey. Embeddings are stubbed and there's no LLM to mock, so it's fast and offline.

```bash
cd backend
pip install -r requirements-dev.txt
pytest tests/unit          # no DB needed — integration/E2E auto-skip without one

docker run -d --name algolog-testdb -e POSTGRES_USER=dsa -e POSTGRES_PASSWORD=dsa \
  -e POSTGRES_DB=algolog_test -p 5432:5432 pgvector/pgvector:pg16
TEST_DATABASE_URL=postgresql+psycopg2://dsa:dsa@localhost:5432/algolog_test pytest --cov=app
```

CI runs the whole suite with coverage on every push and PR.

## Design Decisions

**A deterministic core; the LLM is a topping.** The scheduler, weak-topic detection, and
recommender are plain rules, so you can always answer _"why is this due?"_ The optional LLM
only appends to an already-complete digest email — and it's a local Ollama container, so no
cloud keys and no data leaving the machine either way.

**The SM-2 schedule stores no state.** Interval, ease, and repetitions are derived by folding
SM-2 over a problem's attempt log, so a review is just another logged attempt and the schedule
is a pure function of history. Weak topics read a 90-day window, reflecting current skill.

**Tags are the embedding signal**, not full problem text — a compact, high-signal summary that
keeps "find similar" cheap and consistent. That's why the extension requires at least one tag.

**Supabase for auth, nothing else.** The dashboard's `supabase-js` client is the _only_ thing
that refreshes a token: the extension re-reads a bridged copy, the hosted MCP server holds none,
and the stdio server has its own lineage. Since Supabase invalidates a refresh token on use, two
independent refreshers sharing one would race and log each other out.

**pgvector over a separate vector DB.** Embeddings live in the same Postgres as everything else
— similarity search is one SQL query (cosine distance, IVFFlat), and one database to back up.

**MCP calls the service layer, not our own REST API.** Same code, same tenancy filters, one less
hop, no token to relay.

## Contributing

Contributions are welcome. Open an issue first for anything large or design-changing.
