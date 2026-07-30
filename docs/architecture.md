# Architecture

## System diagram

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

Three clients — the browser extension, the React dashboard, and any MCP client (Claude
Desktop, Claude Code, or the bundled stdio server) — all authenticate against Supabase and
call the same FastAPI backend with a bearer JWT. `deps.py` verifies every token against the
project's JWKS before the service layer runs; the service layer is the single place that
touches Postgres, the embedding model, and the SM-2 scheduler, so REST and MCP requests get
identical behavior.

## Data model

| Table          | Key columns                                                              | Notes                                                                 |
| -------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| `users`        | `id` (Supabase UUID), `email`                                            | Upserted on first verified token; no password ever stored              |
| `problems`     | `id`, `user_id`, `url`, `platform`, `title`, `tags`, `embedding`         | One row per (user, URL); `embedding` is a pgvector column over `tags`  |
| `attempts`     | `id`, `problem_id`, `rating` (1–5), `solved_self`, `notes`, `created_at` | Append-only — repeat attempts add rows, never overwrite history         |
| `digest_sends` | `user_id`, `week_start`, `sent_at`                                       | At-most-once claim table so the weekly job can't double-send            |

The SM-2 schedule (interval, ease, repetitions) and the weak-topic rate are not stored —
both are derived by folding over `attempts` at read time, so the schedule is always a pure
function of history. See [Design Decisions](design-decisions.md) for why.

## Sequence: rate an attempt

```mermaid
sequenceDiagram
    participant U as User (extension/dashboard)
    participant API as FastAPI /api/attempts
    participant Auth as deps.py
    participant Svc as Service layer
    participant DB as Postgres + pgvector

    U->>API: POST /api/attempts (Bearer JWT, url, rating, solved_self, tags)
    API->>Auth: verify JWT against Supabase JWKS
    Auth-->>API: user_id
    API->>Svc: upsert_attempt(user_id, payload)
    Svc->>DB: upsert problem by (user_id, url)
    Svc->>DB: embed tags, upsert vector
    Svc->>DB: insert attempt row
    Svc-->>API: attempt record
    API-->>U: 201 Created
```

## Sequence: recommend next

```mermaid
sequenceDiagram
    participant C as Caller (dashboard or MCP client)
    participant API as /api/stats/recommend or MCP tool
    participant Svc as Service layer
    participant DB as Postgres

    C->>API: GET /api/stats/recommend?count=1
    API->>Svc: recommend_next(user_id, count)
    Svc->>DB: fold SM-2 over attempts -> due reviews
    Svc->>DB: compute 90-day solved-unaided rate per tag -> weak topics
    Svc->>Svc: merge + rank (high = overdue AND weak)
    Svc-->>API: ranked list with reason + priority
    API-->>C: JSON response
```

## Sequence: weekly digest

```mermaid
sequenceDiagram
    participant Job as APScheduler (Sun 18:00)
    participant DB as Postgres (digest_sends)
    participant Svc as Service layer
    participant Ollama as Ollama (optional)
    participant SMTP as SMTP

    Job->>DB: claim week_start for user (at-most-once)
    DB-->>Job: claim acquired
    Job->>Svc: build_digest(user_id)
    Svc-->>Job: week stats, top-5 due, coach note
    opt OLLAMA_MODEL set
        Job->>Ollama: enrich(digest)
        Ollama-->>Job: personalized paragraph + tips + web-searched problems
    end
    Job->>SMTP: send email
```
