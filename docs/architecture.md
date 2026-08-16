# Architecture

## Data model

| Table          | Key columns                                                              | Notes                                                                 |
| -------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------------- |
| `users`        | `id` (Supabase UUID), `email`                                            | Upserted on first verified token; no password ever stored             |
| `problems`     | `id`, `user_id`, `url`, `platform`, `title`, `tags`, `embedding`         | One row per (user, URL); `embedding` is a pgvector column over `tags` |
| `attempts`     | `id`, `problem_id`, `rating` (1–5), `solved_self`, `notes`, `created_at` | Append-only — repeat attempts add rows, never overwrite history       |
| `digest_sends` | `user_id`, `week_start`, `sent_at`                                       | At-most-once claim table so the weekly job can't double-send          |
| `documents`    | `id`, `user_id`, `filename`, `pages`                                     | One uploaded study PDF; the file itself isn't kept, only its text     |
| `chunks`       | `id`, `document_id`, `user_id`, `ordinal`, `text`, `embedding`           | Retrievable passages; `user_id` denormalised so search needs no join  |

The SM-2 schedule (interval, ease, repetitions) and the weak-topic rate are not stored —
both are derived by folding over `attempts` at read time, so the schedule is always a pure
function of history. See [Design Decisions](design-decisions.md) for why.

## Sequence: ask your study material (corrective RAG)

```mermaid
flowchart LR
    Q[Question] --> R[retrieve<br/>bi-encoder + pgvector, k=20]
    R --> G{grade<br/>cross-encoder}
    G -- enough --> GEN[generate]
    G -- thin, budget left --> RW[rewrite query<br/>chat LLM] --> R
    G -- empty, budget spent --> W[web fallback<br/>ddgs] --> GEN
    GEN --> C{grounded?}
    C -- yes --> OUT[passages + answer]
    C -- no, once --> GEN
```

Grading is a cross-encoder rather than the chat model: it scores question and passage
_jointly_, which the retrieval bi-encoder structurally cannot, in one batched CPU call
instead of twenty generations. The chat model only routes, rewrites, and writes. Without
`OLLAMA_MODEL` the graph is retrieve+grade and the caller (Claude, via MCP) writes the answer.

## Sequence: rate an attempt

```mermaid
sequenceDiagram
    participant U as User (extension/dashboard)
    participant API as FastAPI /api/v1/attempts
    participant Auth as deps.py
    participant Svc as Service layer
    participant DB as Postgres + pgvector

    U->>API: POST /api/v1/attempts (Bearer JWT, url, rating, solved_self, tags)
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
    participant API as /api/v1/stats/recommend or MCP tool
    participant Svc as Service layer
    participant DB as Postgres

    C->>API: GET /api/v1/stats/recommend?count=1
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
