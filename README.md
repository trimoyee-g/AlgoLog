<div align="center">

# AlgoLog

**Self-rate competitive-programming submissions, revisit what didn't stick.**

Log every LeetCode / Codeforces / CodeChef / AtCoder / GFG problem you attempt with a
1–5 difficulty score and an honest "did I actually solve this myself?" flag. AlgoLog
then finds problems similar to ones you struggled with, tracks how much you solve
unaided, resurfaces weak problems on a spaced-repetition schedule, and emails you a
weekly digest — all running locally, no API keys at all.

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
- [API Reference](#api-reference)
- [MCP Server](#mcp-server)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [Key Design Decisions](#key-design-decisions)
- [Contributing](#contributing)

---

## Overview

AlgoLog is a personal, single-user tracker with three ways in and one brain behind them:

- **Browser extension** — click the toolbar icon on any problem page to rate the
  submission you just made (1–5 difficulty, solved-yourself yes/no, tags, notes). The
  platform is guessed from the tab URL.
- **React dashboard** — add and edit problems, filter your history, find similar
  problems, work the spaced-repetition review queue, and trigger the weekly digest on demand.
- **MCP server** — ask Claude Desktop / Claude Code "what should I revisit next?" and let
  it call your own tracker as tools — including a recommender that reasons over your data,
  not just fetches it.

Everything runs **locally and free**, with **no LLM in the loop**: embeddings run locally
via `sentence-transformers`, and the review scheduler, weak-topic detection, and weekly
digest are all deterministic rules — reproducible and debuggable. Auth is handled by
**Supabase** (JWT), so the data is per-user and the backend never stores a password.

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
   │                 FastAPI backend  :8000                 │
   │      attempts · similarity · stats · review           │
   │  SM-2 scheduler · weak-topic + recommend (deterministic)│
   │  Supabase-JWT auth · APScheduler weekly digest         │
   └───────────┬───────────────────────────┬───────────────┘
               │                           │
        ┌──────▼──────┐            ┌────────▼───────┐
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
| **Self-rating** | Every attempt logs a 1–5 difficulty score + a `solved_self` flag + tags and notes. Repeat attempts on the same problem are kept as history, not overwritten. |
| **Similarity search** | A problem's comma-separated tags are embedded with `all-MiniLM-L6-v2` and stored in pgvector. "Find similar" returns the closest matches from *your own* history. |
| **Spaced repetition** | An SM-2 variant reschedules each problem from its attempt history — fail/struggle resets the interval to 1 day, clean recalls stretch it out (1 → 6 → ×ease). No scheduler state is stored; the schedule is *derived* by folding SM-2 over the immutable attempt log. The dashboard **Review** tab and `/review` page surface what's due. |
| **Weak-topic detection** | For each tag, the recent (90-day) solved-unaided rate; a tag is "weak" below 50% *with* ≥3 attempts, so one bad problem never brands a topic weak forever. |
| **Recommend next** | Combines due-for-review + weak topics into one ranked, *reasoned* suggestion — `high` = overdue **and** a weak topic — each with a plain-English `reason` string so a coach (or Claude) can say *why*. |
| **Weekly digest** | An APScheduler job emails a Sunday summary (SMTP): week stats + week-over-week trend, the top-5 due-for-review problems, and a templated "coach note" from simple conditionals — deterministic, no LLM. Trigger it on demand from the dashboard. |
| **MCP tools** | Query your tracker from Claude Desktop / Claude Code — weak problems, similar problems, stats, and the reasoned "recommend next problem". |

---

## Tech Stack

### Backend

| Concern | Technology |
|---|---|
| Language | Python 3.11 |
| Framework | FastAPI 0.115 + Uvicorn |
| ORM | SQLAlchemy 2.0 · psycopg2 |
| Database | PostgreSQL 16 + [pgvector](https://github.com/pgvector/pgvector) (`ankane/pgvector`) |
| Auth | Supabase-issued JWT (ES256/RS256), verified against the project JWKS via PyJWT |
| Embeddings | `sentence-transformers` — `all-MiniLM-L6-v2` (384-dim, local) |
| Recall scheduling | SM-2 variant, derived from the attempt log (no stored state); weak-topic + recommend are plain deterministic Python |
| Scheduler | APScheduler (weekly email digest) |
| MCP | `mcp` 1.1 (`FastMCP`) — stdio server proxying the REST API |

### Frontend

| Concern | Technology |
|---|---|
| Framework | React 18 + TypeScript |
| Build tool | Vite 5 |
| Styling | Tailwind CSS + shadcn/ui (Radix primitives) |
| Routing | React Router v6 |
| Server state | TanStack Query |
| Auth | `@supabase/supabase-js` (session + JWT interceptor) |
| Motion | Framer Motion |
| Toasts | Sonner |

### Extension

A manifest-v3 extension (Chrome / Edge / Firefox / Safari — it uses the shared
`browser ?? chrome` handle). There is **no page scraping**: you click the toolbar icon on
a problem page and a popup asks for your rating. It authenticates by reusing your
dashboard session — a `bridge.js` content script on the web app copies the Supabase
session into the extension's storage, and `auth.js` mints fresh access tokens from the
refresh token so requests go out as `Bearer <jwt>`. First install opens an onboarding tab.

---

## API Reference

All endpoints require `Authorization: Bearer <supabase-jwt>`. Base URL `http://localhost:8000`.

### Attempts & Problems — `/api`

| Method | Path | Description |
|---|---|---|
| POST | `/attempts` | Log an attempt (upserts the problem by user+URL, appends a new attempt row) |
| GET | `/problems` | List your problems + attempts; filter by `min_rating`, `solved_self`, `platform`, `tag` |
| PATCH | `/problems/{id}` | Update a problem; `rating`/`solved_self` update (or create) the latest attempt |
| DELETE | `/problems/{id}` | Delete a problem (attempts cascade) |

### Similarity — `/api`

| Method | Path | Description |
|---|---|---|
| GET | `/problems/{id}/similar` | Embedding-similar problems from your history |

### Spaced repetition — `/api/review`

| Method | Path | Description |
|---|---|---|
| GET | `/review?due_only=true` | SM-2 review queue, soonest-due first; `due_only=false` returns the whole schedule (due + upcoming) |

### Stats — `/api/stats`

| Method | Path | Description |
|---|---|---|
| GET | `/overview` | Totals: problems, attempts, solved-unaided, hard-rated (≥ 4) |
| GET | `/weekly` | Last-7-days breakdown by platform and tag |
| GET | `/weak-topics` | Tags where your recent solved-unaided rate is below threshold (with enough samples) |
| GET | `/recommend?count=1` | Ranked, reasoned "what to do next" — due reviews + weak topics combined, each with a `reason` and `priority` |
| POST | `/digest/send-now` | Send *your* weekly email digest immediately |

Health check: `GET /health` → `{"status":"ok"}` · Interactive docs: `http://localhost:8000/docs`

---

## MCP Server

Uses `FastMCP` and exposes three tools to any MCP client (e.g. Claude Desktop / Claude Code):

| Tool | What it does |
|---|---|
| `get_weak_problems` | Problems you rated hard (≥ threshold) or couldn't solve unaided |
| `get_stats_overview` | Overall practice stats |
| `get_recommended_problem` | Reasoned "what to work on next" — SM-2 due dates + weak topics combined into a ranked list with `reason`/`priority`, so Claude can coach you unprompted |

The MCP server acts as **you**: it authenticates with your Supabase **refresh token** and
mints short-lived access tokens, exactly like the web app and extension do. Grab the
refresh token once from the web app's `localStorage` after logging in, and set it via
`SUPABASE_REFRESH_TOKEN`. Supabase rotates the refresh token on each use, so the server
persists the latest one to `~/.algolog/mcp_refresh_token` — it survives restarts without
re-seeding.

Add to Claude Desktop's config (`%APPDATA%\Claude\claude_desktop_config.json` on Windows,
`~/Library/Application Support/Claude/claude_desktop_config.json` on Mac):

```json
{
  "mcpServers": {
    "algolog": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/absolute/path/to/repo/backend",
      "env": {
        "BACKEND_URL": "http://localhost:8000",
        "SUPABASE_URL": "https://<ref>.supabase.co",
        "SUPABASE_ANON_KEY": "<your-anon-key>",
        "SUPABASE_REFRESH_TOKEN": "<one-time-seed-from-localStorage>"
      }
    }
  }
}
```

Restart Claude Desktop, then ask: *"Using algolog, what should I revisit next?"* — the
recommender returns something like *"Due for review (last solved 12 days ago, interval 14d)
AND tagged 'dp' where you solve only 35% unaided"*.

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

Log in, then add/edit problems, filter by difficulty / solved-self / platform / tag, find
similar problems, work the **Review** tab (spaced-repetition queue), and trigger the weekly digest.

### 3. Load the extension

1. Go to `chrome://extensions` → enable **Developer mode**
2. **Load unpacked** → select the `extension/` folder
3. Log in on the dashboard (step 2) — the extension picks up that session automatically
   via the bridge content script.
4. On a supported problem page (LeetCode / Codeforces / CodeChef / AtCoder / GFG), click
   the AlgoLog toolbar icon and rate the problem. Logged out → the popup shows a login prompt.

### 4. (Optional) MCP server

See [MCP Server](#mcp-server) above.

---

## Testing

The backend has a pyramid-shaped `pytest` suite (`backend/tests/`):

| Layer | Location | What it covers | Needs a DB? |
|---|---|---|---|
| **Unit** | `tests/unit/` | Embeddings wrapper, SM-2 scheduler, recommend ranking core, weak-topic + digest note logic, JWT verification/upsert, Pydantic schemas, SMTP — all with mocks or pure functions | No |
| **Integration** | `tests/integration/` | Every router (attempts, similarity, stats, review) via FastAPI `TestClient` against real Postgres+pgvector, with each test rolled back | Yes |
| **E2E** | `tests/e2e/` | One full journey: log → filter → stats → similar → digest → edit → delete | Yes |

Embeddings are stubbed and there's no LLM to mock, so tests are fast and offline. Integration/E2E
tests **auto-skip** if no test DB is reachable, so unit tests run anywhere:

```bash
cd backend
pip install -r requirements-dev.txt

# unit only (no DB needed)
pytest tests/unit

# full pyramid — point at a Postgres+pgvector instance
docker run -d --name algolog-testdb -e POSTGRES_USER=dsa -e POSTGRES_PASSWORD=dsa \
  -e POSTGRES_DB=algolog_test -p 5432:5432 pgvector/pgvector:pg16
TEST_DATABASE_URL=postgresql+psycopg2://dsa:dsa@localhost:5432/algolog_test \
  pytest --cov=app
```

CI (`.github/workflows/backend-tests.yml`) spins up a `pgvector/pgvector` service
and runs the whole suite with coverage on every push/PR.

---

## Environment Variables

Backend — `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://dsa:dsa@localhost:5432/algolog` | Postgres + pgvector connection (docker-compose overrides the host to `postgres`) |
| `SUPABASE_PROJECT_URL` | `https://<ref>.supabase.co/` | Your Supabase project URL; its `/auth/v1/.well-known/jwks.json` endpoint verifies tokens |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS origin for the dashboard |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers model |
| `EMBEDDING_DIM` | `384` | Embedding dimension (must match the model) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | Gmail defaults | Weekly digest email (use a Gmail App Password) |
| `DIGEST_TO_EMAIL` | _(empty)_ | Fallback recipient; the scheduled job otherwise emails each user's own address |

Frontend — `frontend/.env`: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (and optional `VITE_BACKEND_URL`).

The extension's Supabase URL, anon key, and backend URL live in `extension/config.js`.

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
│       ├── routers/            # attempts · similarity · stats_router · review
│       └── services/           # embeddings · scheduler (SM-2) · recommend · digest
│
├── extension/                  # MV3 browser extension (popup rating + session bridge)
│   ├── manifest.json
│   ├── config.js               # Supabase / backend URLs + cross-browser `api` handle
│   ├── auth.js                 # session storage + token refresh helpers
│   ├── background.js           # service worker; opens onboarding on install
│   ├── popup.{html,js}         # the rating UI
│   ├── onboarding.{html,js}    # first-run tab
│   └── content_scripts/
│       └── bridge.js           # copies the web-app Supabase session into the extension
│
└── frontend/                   # React + Vite + TS dashboard  (port 5173)
    └── src/
        ├── pages/              # Landing · Login · Dashboard · Review
        ├── components/         # cards, dialogs, filters, charts, ui/ (shadcn)
        └── lib/                # api.ts (JWT interceptor) · supabase.ts · types
```

---

## Key Design Decisions

**Everything runs locally and free** — `sentence-transformers` for embeddings runs
in-process, and there's no LLM at all: no API keys, no per-call cost, no data leaving the machine.

**A deterministic coach over an LLM** — the review scheduler, weak-topic detection, and the
digest "coach note" are plain rules, not model output. That makes every suggestion
reproducible and debuggable ("why is this due? why is dp flagged weak?") — the right
trade for a feature you rely on to guide practice.

**The SM-2 schedule stores no state** — interval, ease, and repetitions are *derived* by
folding SM-2 over a problem's immutable attempt log, so a review is just another logged
attempt and the schedule is a pure function of history. Weak-topic detection uses only a
recent (90-day) window, so "weak" reflects current skill, not old history.

**Tags are the embedding signal** — a problem's comma-separated tags are what get embedded
(not full problem text), which is why the extension requires at least one tag. Tags are a
compact, high-signal summary and keep "find similar" cheap and consistent.

**Supabase for auth, nothing else** — Supabase issues the JWTs; the backend only *verifies*
them (against the project's JWKS) and upserts a thin user row so the digest knows your
email. No passwords stored, no session server to run. The extension never bundles the
Supabase SDK — it reuses the web app's session via a bridge and refreshes tokens with a
single POST.

**pgvector over a separate vector DB** — embeddings live in the same Postgres as everything
else, so similarity search is one SQL query (cosine distance, IVFFlat index) and there's
one database to back up.

**MCP proxies the REST API** — the MCP server calls the same HTTP endpoints the dashboard
does, so there's one source of truth for business logic. It could talk to the DB directly
for lower latency if that ever matters.

---

## Contributing

Contributions are welcome. Open an issue first for anything large or design-changing so we can align before you build.

---

