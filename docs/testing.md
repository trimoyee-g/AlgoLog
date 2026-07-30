# Testing

A pyramid-shaped `pytest` suite in `backend/tests/`:

- **Unit** — scheduler, recommend, weak topics, digest, JWT, schemas (mocked or pure).
- **Integration** — every router and the MCP server via `TestClient` against real Postgres +
  pgvector, each test rolled back.
- **E2E** — one full journey through the API.

Embeddings are stubbed and there's no LLM to mock, so the suite is fast and offline.

```bash
cd backend
pip install -r requirements-dev.txt
pytest tests/unit          # no DB needed — integration/E2E auto-skip without one

docker run -d --name algolog-testdb -e POSTGRES_USER=dsa -e POSTGRES_PASSWORD=dsa \
  -e POSTGRES_DB=algolog_test -p 5432:5432 pgvector/pgvector:pg16
TEST_DATABASE_URL=postgresql+psycopg2://dsa:dsa@localhost:5432/algolog_test pytest --cov=app
```

CI runs the whole suite with coverage on every push and PR.
