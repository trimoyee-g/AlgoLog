// Shared constants + cross-browser API handle.
// Loaded first by popup.html / onboarding.html, and via importScripts() in background.js.

// Firefox/Safari expose promise-based `browser`; Chrome/Edge expose `chrome`
// (promise-capable on the APIs we use in MV3). One handle works on all four.
const api = globalThis.browser ?? globalThis.chrome;

// The extension never talks to Supabase directly — it only ever reuses the
// session bridge.js copies over from the dashboard (see auth.js) — so no
// Supabase URL or key is needed here, just where the backend and dashboard live.
const BACKEND_URL = "http://localhost:8000";
const WEBAPP_URL = "http://localhost:5173";
