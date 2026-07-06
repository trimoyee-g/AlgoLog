# AlgoLog

Self-rate every LeetCode/Codeforces/CodeChef/AtCoder/GFG submission (difficulty
1-5 + "did I actually solve it myself") so you stop copy-pasting solutions and
forgetting you never really understood them.

## What's inside

```
backend/     FastAPI + Postgres/pgvector + local Ollama LLM + MCP server + ML model
extension/   Chrome extension (MV3) - popup + auto-detecting overlay per platform
frontend/    Plain HTML/JS dashboard with filters, similarity search, digest trigger
docker-compose.yml   Postgres (pgvector) + Ollama + backend, one command to start
```

Everything runs **locally and free** - no paid API keys. LLM calls go to Ollama
running in Docker; embeddings run locally via sentence-transformers.

## 1. Start the backend

```bash
cd algolog
cp backend/.env.example backend/.env
# edit backend/.env: set API_KEY to something random, and SMTP_* if you want the weekly email

docker compose up -d --build
```

First time only, pull an LLM model into the Ollama container (phi3 is small
and fast, good enough for the digest/grading agent; swap for llama3.1 if you
want better quality and have the RAM):

```bash
docker exec -it algolog-ollama ollama pull phi3
```

Check the backend is up: open http://localhost:8000/health -> `{"status":"ok"}`
Interactive API docs: http://localhost:8000/docs

## 2. Load the extension

1. Go to `chrome://extensions`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked" -> select the `extension/` folder
4. Click the extension icon -> "API settings" -> paste the same `API_KEY` you set in `backend/.env`

Now solve a problem on LeetCode/Codeforces/CodeChef/AtCoder/GFG - when a
verdict appears, an overlay should pop up in the bottom-right asking you to
rate it. If it doesn't (site DOM changed), just click the extension icon and
rate manually - that path always works.

## 3. Open the dashboard

Just open `frontend/index.html` directly in your browser (double-click it,
or `open frontend/index.html` / drag into a browser tab). It calls the
backend at `localhost:8000` directly, no build step needed.

From there you can:
- Filter problems by min. difficulty, solved-yourself, platform, tag
- Click "Find similar" on any problem to see embedding-similarity matches from your history
- Click "Train calibration model" once you have 10+ attempts logged
- Click "Send weekly digest now" to test the email without waiting for Sunday

## 4. MCP server (optional, but the most differentiated piece)

Lets you ask Claude Desktop things like "what DP problems have I failed this month"
directly, with Claude calling your own tracker as tools.

```bash
cd backend
pip install -r requirements.txt   # if running the MCP server outside Docker
python -m app.mcp_server
```

Add to Claude Desktop's config (`~/Library/Application Support/Claude/claude_desktop_config.json`
on Mac, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "algolog": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/absolute/path/to/algolog/backend",
      "env": {
        "BACKEND_URL": "http://localhost:8000",
        "API_KEY": "the-same-key-from-.env"
      }
    }
  }
}
```

Restart Claude Desktop, then try asking: "Using algolog, what problems have I rated 4 or 5?"

## Known limitations (be upfront about these if you show this off)

- **DOM-based submission detection is inherently fragile.** LeetCode/Codeforces/
  CodeChef/AtCoder/GFG all redesign their pages periodically. The selectors in
  `extension/content_scripts/*.js` are a reasonable starting point, not
  guaranteed-forever. When a site changes its DOM, auto-detection breaks silently -
  the manual popup rating always works as a fallback regardless.
- **The calibration model needs ~10+ logged attempts before it trains** -
  before that it just returns your running average.
- **The self-grading agent's question quality depends on the Ollama model you
  pull.** `phi3` is fast but sometimes shallow; `llama3.1` or `mistral` (matching
  what you used in SafeHer) will ask sharper follow-up questions if you have the
  RAM to spare.
- **Single-user, shared-secret auth** (`X-API-Key` header) - fine for a personal
  tool running on localhost, not meant to be exposed to the public internet as-is.

## Extending

- Swap `phi3` for any Ollama model by changing `OLLAMA_MODEL` in `.env`.
- Add a real user-facing auth (JWT) if you ever want multiple people using it.
- The MCP server currently proxies to the REST API - could talk to the DB
  directly for lower latency if needed.
