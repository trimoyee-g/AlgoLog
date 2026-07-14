// Session helpers shared by popup.js and onboarding.js. Needs config.js loaded first
// (provides `api`, WEBAPP_URL).
//
// The extension never talks to Supabase directly and never refreshes a token
// itself. The dashboard's supabase-js client is the only thing that refreshes
// sessions; bridge.js (running on the dashboard origin) copies whatever
// supabase-js currently holds into the extension's storage.local every time
// it changes. This file just reads that copy. If it's missing or past
// expiry, getAccessToken() returns null and the caller shows a login prompt
// that sends the user to the dashboard — see openLogin() below.

async function getStoredSession() {
  const { session } = await api.storage.local.get("session");
  return session ?? null;
}

function isExpired(session) {
  if (!session?.expires_at) return true;
  return Date.now() / 1000 > session.expires_at - 60; // treat "about to expire" as expired
}

// The access token from the last session bridge.js synced, or null if there
// isn't one / it's stale. Never attempts a refresh — that's the dashboard's
// job. A null return means the caller should show the login view.
async function getAccessToken() {
  const session = await getStoredSession();
  if (!session || isExpired(session)) {
    if (session) await api.storage.local.remove("session"); // stale copy, drop it
    return null;
  }
  return session.access_token;
}

// User-initiated only (never called automatically): opens the dashboard's
// login page. supabase-js there will silently restore/refresh the session if
// the refresh token is still valid, or show the real login form if not.
// Either way, bridge.js syncs the result back into extension storage, and the
// user reopens the popup to pick up the now-valid session.
function openLogin() {
  api.tabs.create({ url: `${WEBAPP_URL}/login` });
}
