// Session helpers shared by popup.js and onboarding.js. Needs config.js loaded first
// (provides `api`, SUPABASE_URL, SUPABASE_ANON_KEY, WEBAPP_URL).

async function getStoredSession() {
  const { session } = await api.storage.local.get("session");
  return session ?? null;
}

function isExpired(session) {
  if (!session?.expires_at) return true;
  return Date.now() / 1000 > session.expires_at - 60; // refresh 60s early
}

// Exchange the refresh_token for a fresh access_token (the same thing supabase-js
// does under the hood — one POST, so no need to bundle the SDK into the extension).
async function refreshSession(session) {
  if (!session?.refresh_token) return null;
  try {
    const resp = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`, {
      method: "POST",
      headers: { "Content-Type": "application/json", apikey: SUPABASE_ANON_KEY },
      body: JSON.stringify({ refresh_token: session.refresh_token }),
    });
    if (!resp.ok) return null;
    const d = await resp.json();
    const fresh = {
      access_token: d.access_token,
      refresh_token: d.refresh_token,
      expires_at: d.expires_at,
      user: d.user,
    };
    await api.storage.local.set({ session: fresh });
    return fresh;
  } catch {
    return null;
  }
}

// Valid access token (refreshing if needed), or null if logged out.
async function getAccessToken() {
  let session = await getStoredSession();
  if (!session) return null;
  if (isExpired(session)) {
    session = await refreshSession(session);
    if (!session) {
      await api.storage.local.remove("session");
      return null;
    }
  }
  return session.access_token;
}

function openLogin() {
  api.tabs.create({ url: `${WEBAPP_URL}/login` });
}
