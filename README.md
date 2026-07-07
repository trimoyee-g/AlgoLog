<div align="center">

# AlgoLog

**Self-rate competitive-programming submissions, revisit what didn't stick.**

Log every LeetCode / Codeforces / CodeChef / AtCoder / GFG problem you attempt with a
1–5 difficulty score and an honest "did I actually solve this myself?" flag. AlgoLog
then finds problems similar to ones you struggled with, tracks how much you solve
unaided, and emails you a weekly digest with a short LLM-written summary — all running
locally, no paid API keys.

[![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue?style=flat-square&logo=react)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=flat-square&logo=vite)](https://vitejs.dev)
[![Postgres](https://img.shields.io/badge/PostgreSQL-16%20+%20pgvector-336791?style=flat-square&logo=postgresql)](https://github.com/pgvector/pgvector)
[![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-black?style=flat-square&logo=ollama)](https://ollama.com)
[![MCP](https://img.shields.io/badge/MCP-server-purple?style=flat-square)](https://modelcontextprotocol.io)

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
  problems, and trigger the weekly digest on demand.
- **MCP server** — ask Claude Desktop / Claude Code "what DP problems have I failed this
  month?" and let it call your own tracker as tools.

Everything runs **locally and free**. The weekly-digest summary is written by Ollama in
Docker; embeddings run locally via `sentence-transformers`. Auth is handled by
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
   │            attempts · similarity · stats               │
   │  Supabase-JWT auth · APScheduler weekly digest         │
   └───┬────────────────┬───────────────────┬───────────────┘
       │                │                   │
┌──────▼──────┐  ┌──────▼───────┐   ┌───────▼────────┐
│ PostgreSQL  │  │   Ollama     │   │ sentence-      │
│ + pgvector  │  │ (digest      │   │ transformers   │
│   :5432     │  │  narrative)  │   │ (in-process)   │
└─────────────┘  │   :11434     │   └────────────────┘
       ▲         └──────────────┘
┌──────┴───────┐
│   Supabase   │  issues JWTs the backend verifies via JWKS (ES256/RS256)
│    (auth)    │  the extension gets its session from the web app via a bridge
└──────────────┘
```

---

## Features

| Feature | How it works |
|---|---|
| **Self-rating** | Every attempt logs a 1–5 difficulty score + a `solved_self` flag + optional time, tags, and notes. Repeat attempts on the same problem are kept as history, not overwritten. |
| **Similarity search** | A problem's comma-separated tags are embedded with `all-MiniLM-L6-v2` and stored in pgvector. "Find similar" returns the closest matches from *your own* history. |
| **Free-text similarity** | Search history by describing a problem in plain text — useful to check "have I seen something like this before?" before you start. |
| **Weekly digest** | An APScheduler job emails a Sunday summary (SMTP) with a short, Ollama-written coach note plus raw stats. Trigger it on demand from the dashboard. |
| **MCP tools** | Query your tracker from Claude Desktop / Claude Code — weak problems, similar problems, stats. |

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
| LLM | Ollama (local) — default model `phi3`, used for the weekly-digest narrative |
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
| GET | `/problems/search-similar-text?text=...` | Free-text similarity search |

### Stats — `/api/stats`

| Method | Path | Description |
|---|---|---|
| GET | `/overview` | Totals: problems, attempts, solved-unaided, hard-rated (≥ 4) |
| GET | `/weekly` | Last-7-days breakdown by platform and tag |
| POST | `/digest/send-now` | Send *your* weekly email digest immediately |

Health check: `GET /health` → `{"status":"ok"}` · Interactive docs: `http://localhost:8000/docs`

---

## MCP Server

Uses `FastMCP` and exposes three tools to any MCP client (e.g. Claude Desktop / Claude Code):

| Tool | What it does |
|---|---|
| `get_weak_problems` | Problems you rated hard (≥ threshold) or couldn't solve unaided |
| `get_similar_problems` | Free-text similarity search over your history |
| `get_stats_overview` | Overall practice stats |

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

Restart Claude Desktop, then ask: *"Using algolog, what problems have I rated 4 or 5?"*

---

## Getting Started

### Prerequisites

- Docker Desktop (≥ 6 GB RAM recommended for the LLM)
- Node 18+ (for the dashboard)
- A free [Supabase](https://supabase.com) project (for auth)

### 1. Start the backend

```bash
# from the repo root
cp backend/.env.example backend/.env
# edit backend/.env: set SUPABASE_PROJECT_URL, and SMTP_* if you want the weekly email

docker compose up -d --build
```

First run only, pull an LLM model into the Ollama container (`phi3` is small and fast;
swap for `llama3.1` if you have the RAM):

```bash
docker exec -it algolog-ollama ollama pull phi3
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
similar problems, and trigger the weekly digest.

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

## Environment Variables

Backend — `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://dsa:dsa@localhost:5432/algolog` | Postgres + pgvector connection (docker-compose overrides the host to `postgres`) |
| `SUPABASE_PROJECT_URL` | `https://<ref>.supabase.co/` | Your Supabase project URL; its `/auth/v1/.well-known/jwks.json` endpoint verifies tokens |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS origin for the dashboard |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint (docker-compose sets `http://ollama:11434`) |
| `OLLAMA_MODEL` | `phi3` | LLM model for the digest narrative |
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
├── docker-compose.yml          # Postgres (pgvector) + Ollama + backend
│
├── backend/                    # FastAPI + pgvector + Ollama + MCP  (port 8000)
│   └── app/
│       ├── main.py             # App wiring, CORS, pgvector index, APScheduler digest job
│       ├── config.py           # Settings (env-driven)
│       ├── deps.py             # Supabase JWT verification (JWKS)
│       ├── database.py         # Engine / session / Base
│       ├── models.py           # SQLAlchemy models (per-user)
│       ├── schemas.py          # Pydantic DTOs
│       ├── mcp_server.py       # FastMCP stdio server
│       ├── routers/            # attempts · similarity · stats_router
│       └── services/           # embeddings · llm_client · digest
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
        ├── pages/              # Landing · Login · Dashboard
        ├── components/         # cards, dialogs, filters, charts, ui/ (shadcn)
        └── lib/                # api.ts (JWT interceptor) · supabase.ts · types
```

---

## Key Design Decisions

**Everything runs locally and free** — Ollama for the digest narrative and
`sentence-transformers` for embeddings mean no API keys, no per-call cost, and no data
leaving the machine.

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

