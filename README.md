<div align="center">

# AlgoLog

**Self-rate competitive-programming submissions, revisit what didn't stick.**

Log every LeetCode / Codeforces / CodeChef / AtCoder / GFG problem you attempt with a 1–5
difficulty score and an honest "did I actually solve this myself?" flag. AlgoLog finds
problems similar to ones you struggled with, tracks how much you solve unaided, resurfaces
weak problems on a spaced-repetition schedule, and emails you a weekly digest — all running
locally, with no LLM and no API keys.

[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue?style=flat-square&logo=react)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=flat-square&logo=vite)](https://vitejs.dev)
[![Postgres](https://img.shields.io/badge/PostgreSQL-16%20+%20pgvector-336791?style=flat-square&logo=postgresql)](https://github.com/pgvector/pgvector)
[![MCP](https://img.shields.io/badge/MCP-server-purple?style=flat-square)](https://modelcontextprotocol.io)
[![backend-tests](https://github.com/trimoyee-g/AlgoLog/actions/workflows/backend-tests.yml/badge.svg)](https://github.com/trimoyee-g/AlgoLog/actions/workflows/backend-tests.yml)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [MCP Server](#mcp-server)
- [Environment Variables](#environment-variables)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Key Design Decisions](#key-design-decisions)
- [Contributing](#contributing)

---

## Overview

AlgoLog is a personal practice tracker with three ways in and one brain behind them:

- **Browser extension** — click the toolbar icon on any problem page to rate the submission
  you just made (1–5 difficulty, solved-yourself yes/no, tags, notes). The platform is
  inferred from the tab URL.
- **React dashboard** — add and edit problems, filter your history, find similar problems,
  work the spaced-repetition review queue, and trigger the weekly digest on demand.
- **MCP server** — ask Claude Desktop or Claude Code *"what should I revisit next?"* and let
  it call your own tracker as tools, including a recommender that reasons over your data
  rather than just fetching it.

Everything runs locally: embeddings are computed in-process via `sentence-transformers`, and
the review scheduler, weak-topic detection, and weekly digest are deterministic rules — no
LLM anywhere in the loop. Auth is delegated to **Supabase** (JWT), so data is per-user and
the backend never stores a password.

---

## Architecture

```
   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
   │  Browser     │   │ React Dash   │   │  Claude Desktop  │
   │  extension   │   │ (Vite · TS · │   │   (MCP client)   │
   │ (popup rate) │   │  Tailwind)   │   └────────┬─────────┘
   └──────┬───────┘   └──────┬───────┘            │
          │ Bearer JWT       │ Bearer JWT         │ stdio
          │                  │            ┌───────▼────────┐
          │                  │            │   MCP server   │
          │                  │            │ (proxies REST) │
          │                  │            └───────┬────────┘
          ▼                  ▼                    ▼
   ┌───────────────────────────────────────────────────────┐
   │                FastAPI backend  :8000                 │
   │         attempts · similarity · stats · review        │
   │  SM-2 scheduler · weak-topic + recommend (rule-based) │
   │   Supabase-JWT auth · APScheduler weekly digest       │
   └───────────┬───────────────────────────┬───────────────┘
               │                           │
        ┌──────▼──────┐            ┌───────▼────────┐
        │ PostgreSQL  │            │ sentence-      │
        │ + pgvector  │            │ transformers   │
        │   :5432     │            │ (in-process)   │
        └─────────────┘            └────────────────┘
       ▲
┌──────┴───────┐
│   Supabase   │  issues JWTs the backend verifies via JWKS (ES256/RS256)
│    (auth)    │  the extension gets its session from the web app via a bridge
└──────────────┘
```

---

## Features

| Feature | How it works |
|---|---|
| **Self-rating** | Every attempt logs a 1–5 difficulty score, a `solved_self` flag, tags, and notes. Repeat attempts on the same problem are kept as history, not overwritten. |
| **Similarity search** | A problem's comma-separated tags are embedded with `all-MiniLM-L6-v2` and stored in pgvector. "Find similar" returns the closest matches from *your own* history. |
| **Spaced repetition** | An SM-2 variant reschedules each problem from its attempt history — a fail or struggle resets the interval to 1 day, clean recalls stretch it out (1 → 6 → ×ease). No scheduler state is stored; the schedule is *derived* by folding SM-2 over the immutable attempt log. |
| **Weak-topic detection** | Per tag, the recent (90-day) solved-unaided rate. A tag is "weak" below 50% *and* with ≥3 attempts, so one bad problem never brands a topic weak forever. |
| **Recommend next** | Merges due-for-review and weak topics into one ranked suggestion — `high` priority means overdue **and** a weak topic — each carrying a plain-English `reason` string. |
| **Weekly digest** | An APScheduler job emails a Sunday summary over SMTP: week stats with a week-over-week trend, the top-5 due-for-review problems, and a templated coach note built from simple conditionals. Also triggerable on demand from the dashboard. |
| **MCP tools** | Query the tracker from any MCP client — weak problems, overall stats, and the reasoned "recommend next problem". |

---

## Tech Stack

### Backend

| Concern | Technology |
|---|---|
| Language | Python 3.11 |
| Framework | FastAPI 0.115 + Uvicorn |
| ORM | SQLAlchemy 2.0 · psycopg2 |
| Database | PostgreSQL 16 + [pgvector](https://github.com/pgvector/pgvector) |
| Auth | Supabase-issued JWT (ES256/RS256), verified against the project JWKS via PyJWT |
| Embeddings | `sentence-transformers` — `all-MiniLM-L6-v2` (384-dim, local) |
| Recall scheduling | SM-2 variant derived from the attempt log; weak-topic and recommend are plain deterministic Python |
| Scheduler | APScheduler (weekly email digest) |
| MCP | `mcp` 1.2 (`FastMCP`) — stdio server proxying the REST API |

### Frontend

| Concern | Technology |
|---|---|
| Framework | React 18 + TypeScript |
| Build tool | Vite 5 |
| Styling | Tailwind CSS + shadcn/ui (Radix primitives) |
| Routing | React Router v6 |
| Server state | TanStack Query |
| Auth | `@supabase/supabase-js` (session + JWT interceptor) |
| Motion / toasts | Framer Motion · Sonner |

### Extension

A manifest-v3 extension (Chrome / Edge / Firefox / Safari — it uses a shared
`browser ?? chrome` handle). There is **no page scraping**: you click the toolbar icon on a
problem page and a popup asks for your rating.

It authenticates by reusing your dashboard session. A `bridge.js` content script on the web
app copies the Supabase session into extension storage whenever it changes; `auth.js` just
reads whatever was last synced and treats an expired or missing session as logged-out. The
extension never bundles the Supabase SDK or calls Supabase itself — see
[Key Design Decisions](#key-design-decisions) for why. If the session is stale, the popup
shows a login prompt that opens the dashboard; logging in there syncs back automatically.

---

## Getting Started

### Prerequisites

- Docker Desktop
- Node 18+ (for the dashboard)
- A free [Supabase](https://supabase.com) project (for auth)

### 1. Start the backend

```bash
# from the repo root
cp backend/.env.example backend/.env
# edit backend/.env: set SUPABASE_PROJECT_URL, and SMTP_* if you want the weekly email

docker compose up -d --build
```

Verify: `http://localhost:8000/health` → `{"status":"ok"}`

### 2. Run the dashboard

```bash
cd frontend
cp .env.example .env   # set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
npm install
npm run dev            # http://localhost:5173
```

Log in, then add and edit problems, filter by difficulty / solved-self / platform / tag, find
similar problems, work the **Review** tab, and trigger the weekly digest.

### 3. Load the extension

1. Go to `chrome://extensions` → enable **Developer mode**.
2. **Load unpacked** → select the `extension/` folder.
3. Log in on the dashboard (step 2) — the extension picks that session up automatically via
   the bridge content script.
4. On a supported problem page, click the AlgoLog toolbar icon and rate the problem.

### 4. (Optional) MCP server

See [MCP Server](#mcp-server) below.

---

## API Reference

All endpoints require `Authorization: Bearer <supabase-jwt>`. Base URL `http://localhost:8000`.

### Attempts & problems — `/api`

| Method | Path | Description |
|---|---|---|
| POST | `/attempts` | Log an attempt (upserts the problem by user + URL, appends a new attempt row) |
| GET | `/problems` | List your problems and attempts; filter by `min_rating`, `solved_self`, `platform`, `tag` |
| PATCH | `/problems/{id}` | Update a problem; `rating` / `solved_self` update (or create) the latest attempt |
| DELETE | `/problems/{id}` | Delete a problem (attempts cascade) |
| GET | `/problems/{id}/similar` | Embedding-similar problems from your history |

### Spaced repetition — `/api/review`

| Method | Path | Description |
|---|---|---|
| GET | `/review?due_only=true` | SM-2 review queue, soonest-due first; `due_only=false` returns the whole schedule |

### Stats — `/api/stats`

| Method | Path | Description |
|---|---|---|
| GET | `/overview` | Totals: problems, attempts, solved-unaided, hard-rated (≥ 4) |
| GET | `/weekly` | Last-7-days breakdown by platform and tag |
| GET | `/weak-topics` | Tags whose recent solved-unaided rate is below threshold, with enough samples |
| GET | `/recommend?count=1` | Ranked "what to do next" — due reviews + weak topics, each with a `reason` and `priority` |
| POST | `/digest/send-now` | Send your weekly email digest immediately |

Health check: `GET /health` · Interactive docs: `http://localhost:8000/docs`

---

## MCP Server

A `FastMCP` stdio server exposing three tools to any MCP client:

| Tool | What it does |
|---|---|
| `get_weak_problems` | Problems you rated hard (≥ threshold) or couldn't solve unaided |
| `get_stats_overview` | Overall practice stats |
| `get_recommended_problem` | Reasoned "what to work on next" — SM-2 due dates plus weak topics, ranked with `reason` and `priority` |

The server acts as **you**: it holds its own Supabase refresh token and mints short-lived
access tokens from it. It logs in *independently* rather than copying the dashboard's
session, because Supabase rotates a refresh token on every redemption and invalidates the
previous one — two clients sharing one token would keep silently logging each other out.

**One-time setup:**

1. In your Supabase dashboard, under **Authentication → URL Configuration → Redirect URLs**,
   add `http://localhost:8765/` (the login script listens there briefly to catch the redirect).
2. From `backend/`, run:
   ```bash
   python -m app.mcp_login
   ```
   This opens a browser to sign in via GitHub and saves the resulting refresh token to
   `~/.algolog/mcp_refresh_token`. The server persists each rotated token back to that file,
   so it survives restarts without re-seeding.

Then add it to Claude Desktop's config (`%APPDATA%\Claude\claude_desktop_config.json` on
Windows, `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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

Restart Claude Desktop and ask: *"Using algolog, what should I revisit next?"* The
recommender answers with something like *"Due for review (last solved 12 days ago, interval
14d) AND tagged 'dp', where you solve only 35% unaided."*

---

## Environment Variables

Backend — `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://dsa:dsa@localhost:5432/algolog` | Postgres + pgvector connection (docker-compose overrides the host to `postgres`) |
| `SUPABASE_PROJECT_URL` | — | Your Supabase project URL; its `/auth/v1/.well-known/jwks.json` endpoint verifies tokens |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS origin for the dashboard |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers model |
| `EMBEDDING_DIM` | `384` | Embedding dimension (must match the model) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | Gmail host/port, empty creds | Weekly digest email; use a Gmail App Password. Empty credentials disable email. |
| `DIGEST_TO_EMAIL` | _(empty)_ | Fallback recipient; the scheduled job otherwise emails each user's own address |

Frontend — `frontend/.env`: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, and optional
`VITE_BACKEND_URL`.

The extension's backend and dashboard URLs live in `extension/config.js`. It never talks to
Supabase directly, so it needs no Supabase URL or key.

---

## Testing

The backend has a pyramid-shaped `pytest` suite in `backend/tests/`:

| Layer | What it covers | Needs a DB? |
|---|---|---|
| **Unit** | Embeddings wrapper, SM-2 scheduler, recommend ranking, weak-topic and digest logic, JWT verification, Pydantic schemas, SMTP — mocked or pure functions | No |
| **Integration** | Every router (attempts, similarity, stats, review) via FastAPI `TestClient` against real Postgres + pgvector, each test rolled back | Yes |
| **E2E** | One full journey: log → filter → stats → similar → digest → edit → delete | Yes |

Embeddings are stubbed and there is no LLM to mock, so tests are fast and offline.
Integration and E2E tests auto-skip when no test DB is reachable, so unit tests run anywhere:

```bash
cd backend
pip install -r requirements-dev.txt

# unit only (no DB needed)
pytest tests/unit

# full pyramid — point at a Postgres + pgvector instance
docker run -d --name algolog-testdb -e POSTGRES_USER=dsa -e POSTGRES_PASSWORD=dsa \
  -e POSTGRES_DB=algolog_test -p 5432:5432 pgvector/pgvector:pg16
TEST_DATABASE_URL=postgresql+psycopg2://dsa:dsa@localhost:5432/algolog_test \
  pytest --cov=app
```

CI (`.github/workflows/backend-tests.yml`) spins up a `pgvector/pgvector` service and runs
the whole suite with coverage on every push and PR.

---

## Project Structure

```
.
├── docker-compose.yml          # Postgres (pgvector) + backend
│
├── backend/                    # FastAPI + pgvector + MCP  (port 8000)
│   └── app/
│       ├── main.py             # App wiring, CORS, pgvector index, APScheduler digest job
│       ├── config.py           # Settings (env-driven)
│       ├── deps.py             # Supabase JWT verification (JWKS)
│       ├── database.py         # Engine / session / Base
│       ├── models.py           # SQLAlchemy models (per-user)
│       ├── schemas.py          # Pydantic DTOs
│       ├── mcp_server.py       # FastMCP stdio server
│       ├── mcp_login.py        # One-time OAuth login to seed the MCP refresh token
│       ├── routers/            # attempts · similarity · stats_router · review
│       └── services/           # embeddings · scheduler (SM-2) · recommend · digest
│
├── extension/                  # MV3 browser extension (popup rating + session bridge)
│   ├── manifest.json
│   ├── config.js               # Backend / dashboard URLs + cross-browser `api` handle
│   ├── auth.js                 # Reads the bridged session
│   ├── background.js           # Service worker; opens onboarding on install
│   ├── popup.{html,js}         # The rating UI
│   ├── onboarding.{html,js}    # First-run tab
│   └── content_scripts/
│       └── bridge.js           # Copies the web-app Supabase session into the extension
│
└── frontend/                   # React + Vite + TS dashboard  (port 5173)
    └── src/
        ├── pages/              # Landing · Login · Dashboard · Review
        ├── components/         # Cards, dialogs, filters, charts, ui/ (shadcn)
        └── lib/                # api.ts (JWT interceptor) · supabase.ts · types
```

---

## Key Design Decisions

**A deterministic coach, not an LLM.** The review scheduler, weak-topic detection, and the
digest coach note are plain rules. Every suggestion is reproducible and debuggable — you can
always answer *"why is this due?"* or *"why is dp flagged weak?"* — which is the right trade
for a feature you rely on to guide practice. Embeddings run in-process via
`sentence-transformers`, so there are no API keys, no per-call cost, and no data leaving the
machine.

**The SM-2 schedule stores no state.** Interval, ease, and repetitions are derived by folding
SM-2 over a problem's immutable attempt log, so a review is just another logged attempt and
the schedule is a pure function of history. Weak-topic detection reads only a 90-day window,
so "weak" reflects current skill rather than old history.

**Tags are the embedding signal.** A problem's comma-separated tags are what get embedded,
not full problem text — which is why the extension requires at least one tag. Tags are a
compact, high-signal summary that keeps "find similar" cheap and consistent.

**Supabase for auth, nothing else.** Supabase issues the JWTs; the backend only verifies them
against the project JWKS and upserts a thin user row so the digest knows your email. No
passwords stored, no session server to run. Crucially, the dashboard's `supabase-js` client
is the *only* thing that ever refreshes a token — the extension just re-reads the bridged
copy, and the MCP server logs in on its own lineage. Since Supabase rotates and invalidates
refresh tokens on every use, two independent refreshers sharing a token would race and
silently log each other out.

**pgvector over a separate vector DB.** Embeddings live in the same Postgres as everything
else, so similarity search is one SQL query (cosine distance, IVFFlat index) and there is one
database to back up.

**MCP proxies the REST API.** The MCP server calls the same HTTP endpoints the dashboard
does, keeping one source of truth for business logic. It could talk to the DB directly if
latency ever mattered.

---

## Contributing

Contributions are welcome. Open an issue first for anything large or design-changing so we
can align before you build.
