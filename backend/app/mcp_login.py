"""
One-time interactive login for the AlgoLog MCP server.

Run this once (`python -m app.mcp_login`) before first connecting the MCP
server to Claude Desktop / Claude Code.

Why this exists: the MCP server needs its own Supabase session so it can act
as you when Claude calls its tools. The obvious shortcut is to copy the
refresh token the dashboard's browser tab is already using out of
localStorage -- but Supabase rotates a refresh token every time it's
redeemed and invalidates the previous one. If the MCP server and the
dashboard both hold a copy of the *same* live token, whichever one refreshes
first silently invalidates the other's session, and you get logged out of
your browser (or the MCP server starts failing) for no reason you'd connect
to what actually caused it.

The fix is for the MCP server to log in independently -- its own OAuth
round-trip, producing its own refresh-token lineage that was never shared
with the browser. Then the dashboard and the MCP server can each refresh on
their own schedule forever without ever colliding, because neither one's
rotation touches anything the other is holding.

This script does that: it spins up a short-lived local HTTP server, opens
your browser to Supabase's GitHub OAuth flow, and captures the resulting
session when Supabase redirects back -- the same "open a browser, listen on
localhost" pattern used by tools like the GitHub or Vercel CLI.

One-time setup: in your Supabase project's dashboard, under
Authentication > URL Configuration > Redirect URLs, add:
    http://localhost:8765/
Supabase rejects OAuth redirects to URLs that aren't explicitly allow-listed,
so this step is required once before the login flow will complete.
"""
import json
import os
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://zgeymiyigfcyowdyrdln.supabase.co").rstrip("/")
CALLBACK_PORT = 8765
TOKEN_FILE = Path.home() / ".algolog" / "mcp_refresh_token"

_captured: dict = {}
_done = threading.Event()

# Supabase's OAuth redirect lands with the session in the URL *fragment*
# (`#access_token=...&refresh_token=...`), which never reaches an HTTP
# server -- fragments are resolved client-side only and aren't sent in the
# request. So the callback page is a few lines of JS that reads
# `location.hash` in the browser and POSTs it back to this local server.
_CALLBACK_HTML = b"""<!doctype html><html><body>
<p>Signing in to AlgoLog MCP...</p>
<script>
  const params = new URLSearchParams(window.location.hash.slice(1));
  fetch("/token", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      access_token: params.get("access_token"),
      refresh_token: params.get("refresh_token"),
      error: params.get("error_description"),
    }),
  }).then(() => {
    document.body.innerHTML = "<p>Signed in - you can close this tab.</p>";
  });
</script>
</body></html>"""


class _CallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # quiet the default request logging
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(_CALLBACK_HTML)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        _captured.update(json.loads(self.rfile.read(length)))
        self.send_response(200)
        self.end_headers()
        _done.set()


def main() -> None:
    server = HTTPServer(("localhost", CALLBACK_PORT), _CallbackHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    redirect_to = f"http://localhost:{CALLBACK_PORT}/"
    authorize_url = (
        f"{SUPABASE_URL}/auth/v1/authorize"
        f"?provider=github&redirect_to={urllib.parse.quote(redirect_to, safe='')}"
    )
    print("Opening your browser to sign in independently for the MCP server.")
    print("This is a separate login from your dashboard session, by design --")
    print("see the top of this script for why that matters.\n")
    print(f"If your browser doesn't open automatically, visit:\n  {authorize_url}\n")
    webbrowser.open(authorize_url)

    if not _done.wait(timeout=180):
        server.shutdown()
        raise SystemExit(
            "Timed out waiting for login. Run `python -m app.mcp_login` again.\n"
            "If you kept seeing an error page, check that "
            f"http://localhost:{CALLBACK_PORT}/ is added under Authentication > "
            "URL Configuration > Redirect URLs in your Supabase project."
        )
    server.shutdown()

    if _captured.get("error"):
        raise SystemExit(f"Login failed: {_captured['error']}")

    refresh_token = _captured.get("refresh_token")
    if not refresh_token:
        raise SystemExit(
            "Login didn't return a refresh token. Double-check SUPABASE_URL and "
            "that the redirect URL above is allow-listed in Supabase, then try again."
        )

    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(refresh_token)
    print(f"Saved an MCP-only session to {TOKEN_FILE}")
    print("This session is independent of your dashboard login: the MCP server will")
    print("refresh it on its own from now on, without touching your browser session")
    print("(or being touched by it). Restart Claude Desktop / Claude Code to pick it up.")


if __name__ == "__main__":
    main()
