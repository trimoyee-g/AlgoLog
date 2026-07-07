// Shared constants + cross-browser API handle.
// Loaded first by popup.html / onboarding.html, and via importScripts() in background.js.

// Firefox/Safari expose promise-based `browser`; Chrome/Edge expose `chrome`
// (promise-capable on the APIs we use in MV3). One handle works on all four.
const api = globalThis.browser ?? globalThis.chrome;

// Must match frontend/.env. The publishable/anon key is safe to ship in a client.
const SUPABASE_URL = "https://zgeymiyigfcyowdyrdln.supabase.co"; // no trailing slash
const SUPABASE_ANON_KEY = "sb_publishable_AUs-POxEqR98ehNHh9eHkA_9Mm9vm7w";
const BACKEND_URL = "http://localhost:8000";
const WEBAPP_URL = "http://localhost:5173";
