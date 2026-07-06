<div align="center">

# AlgoLog

**Self-rate every competitive-programming submission — so you stop copy-pasting solutions and forgetting you never really understood them.**

Log every LeetCode / Codeforces / CodeChef / AtCoder / GFG problem you attempt with a
1–5 difficulty score and an honest "did I actually solve this myself?" flag. AlgoLog
then finds problems similar to ones you struggled with, predicts how hard a new problem
will feel *to you*, grades your understanding with a local LLM, and emails you a weekly
digest — all running locally, no paid API keys.

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
- [Known Limitations](#known-limitations)

---

## Overview

AlgoLog is a personal, single-user tracker with three ways in and one brain behind them:

- **Chrome extension** — auto-detects a verdict on a problem page and pops up an overlay asking you to rate it. Manual popup rating always works as a fallback.
- **React dashboard** — filter your history, find similar problems, train the calibration model, trigger the weekly digest.
- **MCP server** — ask Claude Desktop "what DP problems have I failed this month?" and let it call your own tracker as tools.

Everything runs **locally and free**. LLM calls go to Ollama in Docker; embeddings run locally via `sentence-transformers`. Auth is handled by **Supabase** (JWT), so the data is per-user and the backend never stores a password.

---

## Architecture

```
   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
   │ Chrome Ext.  │   │ React Dash   │   │  Claude Desktop  │
   │ (MV3 overlay │   │ (Vite · TS · │   │   (MCP client)   │
   │  per platform)   │  Tailwind)   │   └────────┬─────────┘
   └──────┬───────┘   └──────┬───────┘            │
          │ Bearer JWT       │ Bearer JWT         │ stdio
          │                  │            ┌───────▼────────┐
          │                  │            │   MCP server   │
          │                  │            │ (proxies REST) │
          │                  │            └───────┬────────┘
          ▼                  ▼                    ▼
   ┌───────────────────────────────────────────────────────┐
   │                 FastAPI backend  :8000                 │
   │  attempts · similarity · calibration · grading · stats │
   │  Supabase-JWT auth · APScheduler weekly digest         │
   └───┬────────────────┬───────────────────┬───────────────┘
       │                │                   │
┌──────▼──────┐  ┌──────▼───────┐   ┌───────▼────────┐
│ PostgreSQL  │  │   Ollama     │   │ sentence-      │
│ + pgvector  │  │  (local LLM, │   │ transformers   │
│   :5432     │  │   :11434)    │   │ (in-process)   │
└─────────────┘  └──────────────┘   └────────────────┘
       ▲
┌──────┴───────┐
│   Supabase   │  issues JWTs the backend verifies (HS256)
│    (auth)    │
└──────────────┘
```

---

## Features

| Feature | How it works |
|---|---|
| **Self-rating** | Every attempt logs a 1–5 difficulty score + a `solved_self` flag + optional time, tags, and notes. |
| **Similarity search** | Problem text is embedded with `all-MiniLM-L6-v2` and stored in pgvector. "Find similar" returns the closest matches from *your own* history. |
| **Calibration model** | A scikit-learn model trained on your logged attempts predicts how hard a *new* problem will feel to you. Falls back to your running average until you have 10+ attempts. |
| **Self-grading agent** | A multi-turn LLM (Ollama) asks follow-up questions about a problem to check whether you actually understood your solution. |
| **Weekly digest** | An APScheduler job emails you a Sunday summary (SMTP). Trigger it on demand from the dashboard. |
| **MCP tools** | Query your tracker from Claude Desktop — weak problems, similar problems, stats, difficulty prediction. |

---

## Tech Stack

### Backend

| Concern | Technology |
|---|---|
| Language | Python 3.11 |
| Framework | FastAPI 0.115 + Uvicorn |
| ORM | SQLAlchemy 2.0 · psycopg2 |
| Database | PostgreSQL 16 + [pgvector](https://github.com/pgvector/pgvector) (`ankane/pgvector`) |
| Auth | Supabase-issued JWT (HS256), verified via PyJWT |
| Embeddings | `sentence-transformers` — `all-MiniLM-L6-v2` (384-dim, local) |
| LLM | Ollama (local) — default model `phi3` |
| ML | scikit-learn · pandas · joblib |
| Scheduler | APScheduler (weekly email digest) |
| MCP | `mcp` 1.1 — stdio server proxying the REST API |

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

Chrome MV3 — a shared `common.js` overlay plus one content script per platform
(`leetcode.js`, `codeforces.js`, `codechef.js`, `atcoder.js`, `gfg.js`) that detects a
submission verdict and shows the rating overlay.

---

## API Reference

All protected endpoints require `Authorization: Bearer <supabase-jwt>`. Base URL `http://localhost:8000`.

### Attempts & Problems — `/api`

| Method | Path | Description |
|---|---|---|
| POST | `/attempts` | Log an attempt (creates the problem if new) |
| GET | `/problems` | List your problems + their attempts |
| PATCH | `/problems/{id}` | Update a problem / add a rating |
| DELETE | `/problems/{id}` | Delete a problem |

### Similarity — `/api`

| Method | Path | Description |
|---|---|---|
| GET | `/problems/{id}/similar` | Embedding-similar problems from your history |
| GET | `/problems/search-similar-text?...` | Free-text similarity search |

### Calibration — `/api/calibration`

| Method | Path | Description |
|---|---|---|
| POST | `/train` | Train the personal difficulty model (needs 10+ attempts) |
| POST | `/predict` | Predict how hard a new problem will feel to you |

### Grading — `/api/grading`

| Method | Path | Description |
|---|---|---|
| POST | `/start` | Start a self-grading session for a problem |
| POST | `/answer` | Answer the agent's follow-up question |

### Stats — `/api/stats`

| Method | Path | Description |
|---|---|---|
| GET | `/overview` | Totals: problems, attempts, solved-unaided, hard-rated |
| GET | `/weekly` | Weekly breakdown |
| POST | `/digest/send-now` | Send the weekly email digest immediately |

Health check: `GET /health` → `{"status":"ok"}` · Interactive docs: `http://localhost:8000/docs`

---

## MCP Server

Exposes four tools to any MCP client (e.g. Claude Desktop):

| Tool | What it does |
|---|---|
| `get_weak_problems` | Problems you rated hard (≥ threshold) or couldn't solve unaided |
| `get_similar_problems` | Free-text similarity search over your history |
| `get_stats_overview` | Overall practice stats |
| `predict_difficulty` | Predict how hard a new problem will feel to you |

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
        "SUPABASE_JWT_SECRET": "the-same-secret-from-.env"
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
# edit backend/.env: paste your SUPABASE_JWT_SECRET, and SMTP_* if you want the weekly email

docker compose up -d --build
```

First run only, pull an LLM model into the Ollama container (`phi3` is small and fast;
swap for `llama3.1` if you have the RAM):

```bash
docker exec -it algolog-ollama ollama pull phi3
```

Verify: `http://localhost:8000/health` → `{"status":"ok"}`

### 2. Load the extension

1. Go to `chrome://extensions` → enable **Developer mode**
2. **Load unpacked** → select the `extension/` folder
3. Solve a problem on a supported platform — an overlay pops up when a verdict appears. If the site's DOM changed and it doesn't, click the extension icon and rate manually.

### 3. Run the dashboard

```bash
cd frontend
cp .env.example .env   # set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
npm install
npm run dev            # http://localhost:5173
```

From the dashboard you can filter by difficulty / solved-self / platform / tag, find
similar problems, train the calibration model, and trigger the weekly digest.

### 4. (Optional) MCP server

See [MCP Server](#mcp-server) above.

---

## Environment Variables

Backend — `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://dsa:dsa@postgres:5432/algolog` | Postgres + pgvector connection |
| `SUPABASE_JWT_SECRET` | `change-me` | From Supabase → Project Settings → API → JWT Secret (HS256) |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS origin for the dashboard |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `phi3` | LLM model for the grading agent |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers model |
| `EMBEDDING_DIM` | `384` | Embedding dimension (must match the model) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | Gmail defaults | Weekly digest email (use a Gmail App Password) |
| `DIGEST_TO_EMAIL` | _(empty)_ | Where the digest is sent |

Frontend — `frontend/.env`: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.

---

## Project Structure

```
.
├── docker-compose.yml          # Postgres (pgvector) + Ollama + backend
│
├── backend/                    # FastAPI + pgvector + Ollama + MCP  (port 8000)
│   └── app/
│       ├── main.py             # App wiring, CORS, APScheduler digest job
│       ├── config.py           # Settings (env-driven)
│       ├── deps.py             # Supabase JWT verification
│       ├── models.py           # SQLAlchemy models (per-user)
│       ├── schemas.py          # Pydantic DTOs
│       ├── mcp_server.py       # stdio MCP server (4 tools)
│       ├── routers/            # attempts · similarity · calibration · grading · stats
│       └── services/           # embeddings · calibration · grading_agent · llm_client · digest
│
├── extension/                  # Chrome MV3 extension
│   ├── manifest.json
│   ├── background.js · popup.{html,js}
│   └── content_scripts/        # common + one per platform (leetcode/codeforces/…)
│
└── frontend/                   # React + Vite + TS dashboard  (port 5173)
    └── src/
        ├── pages/              # Landing · Login · Dashboard
        ├── components/         # cards, dialogs, filters, charts, ui/ (shadcn)
        └── lib/                # api.ts (JWT interceptor) · supabase.ts · types
```

---

## Key Design Decisions

**Everything runs locally and free** — Ollama for LLM inference and `sentence-transformers`
for embeddings mean no API keys, no per-call cost, and no data leaving the machine.

**Supabase for auth, nothing else** — Supabase issues the JWTs; the backend only *verifies*
them (HS256, `SUPABASE_JWT_SECRET`) and upserts a thin user row so the digest knows your
email. No passwords stored, no session server to run.

**pgvector over a separate vector DB** — embeddings live in the same Postgres as everything
else, so similarity search is one SQL query and there's one database to back up.

**Calibration falls back gracefully** — the personal-difficulty model needs ~10 attempts to
be meaningful, so below that it returns your running average instead of a cold-start guess.

**MCP proxies the REST API** — the MCP server calls the same HTTP endpoints the dashboard
does, so there's one source of truth for business logic. It could talk to the DB directly
for lower latency if that ever matters.

---

## Known Limitations

- **DOM-based submission detection is inherently fragile.** LeetCode/Codeforces/CodeChef/AtCoder/GFG redesign their pages periodically; the selectors in `extension/content_scripts/*.js` are a reasonable starting point, not guaranteed-forever. The manual popup rating always works as a fallback.
- **The extension's auth predates the Supabase switch.** `popup.js` still sends an `X-API-Key` header, while the backend now verifies a Supabase `Bearer` JWT. Until the extension is updated to send a Supabase token, use the dashboard for the write path.
- **The calibration model needs ~10+ logged attempts** before it trains; before that it returns your running average.
- **Self-grading quality depends on the Ollama model.** `phi3` is fast but sometimes shallow; `llama3.1` or `mistral` ask sharper follow-ups if you have the RAM.
- **Single-user by design** — one Supabase project, running on localhost. Not hardened for public multi-tenant exposure as-is.
</content>
</invoke>
