# API Reference

All endpoints require `Authorization: Bearer <supabase-jwt>`. Base URL `http://localhost:8000`.
Interactive docs are also served at `/docs` (Swagger) once the backend is running.

| Method | Path                            | Description                                                                              |
| ------ | ------------------------------- | ----------------------------------------------------------------------------------------- |
| POST   | `/api/attempts`                 | Log an attempt (upserts the problem by user + URL, appends an attempt row)               |
| GET    | `/api/problems`                 | List problems and attempts; filter by `min_rating`, `solved_self`, `platform`, `tag`     |
| PATCH  | `/api/problems/{id}`            | Update a problem; `rating` / `solved_self` update (or create) the latest attempt         |
| DELETE | `/api/problems/{id}`            | Delete a problem (attempts cascade)                                                       |
| GET    | `/api/problems/{id}/similar`    | Embedding-similar problems from your history                                             |
| GET    | `/api/review?due_only=true`     | SM-2 review queue, soonest-due first; `due_only=false` returns the whole schedule         |
| GET    | `/api/stats/overview`           | Totals: problems, attempts, solved-unaided, hard-rated (≥4)                              |
| GET    | `/api/stats/weekly`             | Last-7-days breakdown by platform and tag                                                |
| GET    | `/api/stats/weak-topics`        | Tags whose recent solved-unaided rate is below threshold, with enough samples            |
| GET    | `/api/stats/recommend?count=1`  | Ranked "what to do next" — due reviews + weak topics, each with `reason` and `priority`  |
| POST   | `/api/stats/digest/send-now`    | Send your weekly digest immediately                                                      |
| POST   | `/api/documents`                | Upload a study PDF (multipart `file`); text is extracted, chunked and embedded           |
| GET    | `/api/documents`                | List uploaded study material with page and chunk counts                                  |
| DELETE | `/api/documents/{id}`           | Delete a document (chunks cascade)                                                        |
| POST   | `/api/documents/ask`            | Ask a question against your material — runs the corrective-RAG loop                       |

`POST /api/documents/ask` takes `{"question": "..."}` and returns
`{question, answer, passages, web, trace}`. `passages` are the graded extracts, each with a
`relevance` score and its source document; `trace` records what the loop did (retrieve, rewrite,
web fallback). `answer` is `null` unless `OLLAMA_MODEL` is set — without a local model the
endpoint returns retrieval only and the caller writes the answer. See
[Design Decisions](design-decisions.md) for why grading uses a cross-encoder rather than the LLM.

See [Architecture — Data model](architecture.md#data-model) for the tables these endpoints
read and write, and [MCP Server](mcp-server.md) for the equivalent tool-based interface.
