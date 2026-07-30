# MCP Server

Three tools — `get_weak_problems`, `get_stats_overview`, and `get_recommended_problem` (the
reasoned "what next", ranked with `reason` and `priority`) — served two ways.

Both paths call the same service layer as the REST API (see
[Architecture](architecture.md)), so behavior and results are identical regardless of client.

## Hosted (recommended)

`POST /mcp`, Streamable HTTP, mounted into the FastAPI app. The MCP client owns the OAuth
session and sends the user's JWT per request, so one process serves every user and stores no
token. Add the URL as a custom connector in Claude and sign in through Supabase. In a real
deployment, set `MCP_PUBLIC_URL` to the address clients actually reach — Claude checks the
token was issued for that exact URL.

Needs three things on the Supabase side, none of them on by default — in
**Authentication → OAuth Server**:

1. Enable the OAuth server.
2. Enable **Allow Dynamic OAuth Apps** (MCP clients register themselves via DCR; there is no
   client id to pre-provision).
3. Implement the consent screen at the **Authorization Path** you configure there — Supabase
   delegates that UI to your own frontend.

Without all three, the client's discovery dead-ends and the only symptom is an empty
`SDK auth failed:`.

## stdio (`app.mcp_server`)

One process per user, on your machine. It holds its own Supabase refresh token rather than
copying the dashboard's, because Supabase rotates and invalidates a refresh token on every
redemption — two clients sharing one would silently log each other out. The same caveat
applies to running Claude Code and Claude Desktop side by side: both read the one token file,
so a simultaneous refresh can lose the race. It self-heals on the next call (the file is
re-read every refresh, never cached); rerun `app.mcp_login` if it ever wedges.

### Setup

1. In Supabase → **Authentication → URL Configuration → Redirect URLs**, add
   `http://localhost:8765/` (the login script listens there to catch the redirect).
2. From `backend/`, run `python -m app.mcp_login`. It opens a browser to sign in and saves the
   refresh token to `~/.algolog/mcp_refresh_token`, persisting each rotation back to that file.
3. Register it.

**Claude Code:**

```bash
claude mcp add --scope user \
  -e PYTHONPATH=/absolute/path/to/repo/backend \
  -e BACKEND_URL=http://localhost:8000 \
  -e SUPABASE_URL=https://<your-ref>.supabase.co \
  -e SUPABASE_ANON_KEY=<your-anon-key> \
  -- algolog python -m app.mcp_server
```

**Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "algolog": {
      "command": "/absolute/path/to/python",
      "args": ["-m", "app.mcp_server"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/repo/backend",
        "BACKEND_URL": "http://localhost:8000",
        "SUPABASE_URL": "https://<your-ref>.supabase.co",
        "SUPABASE_ANON_KEY": "<your-anon-key>"
      }
    }
  }
}
```

Both spell out the interpreter and `PYTHONPATH` rather than relying on `cwd` and a bare
`python`. Clients launch the server from their own working directory and their own `PATH`, so a
bare `python` can resolve to an interpreter without the deps installed — which surfaces only as
"Server disconnected", with the real `ModuleNotFoundError` buried in the client's MCP log.

## Example

Ask: _"Using algolog, what should I revisit next?"_ →
_"Due for review (last solved 12 days ago, interval 14d) AND tagged 'dp', where you solve
only 35% unaided."_
