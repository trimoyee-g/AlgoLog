// Runs on the AlgoLog web app. After the user logs in there, supabase-js stores
// the session in the page's localStorage under a key like `sb-<ref>-auth-token`.
// The extension popup lives on a different origin and can't read that, so we copy
// the session into the extension's own storage.local (shared across extension contexts).
const api = globalThis.browser ?? globalThis.chrome;

function readSupabaseSession() {
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    // ponytail: single-key case. supabase-js chunks (.0/.1) only for large cookies,
    // not localStorage, so one key is enough here.
    if (key && key.startsWith("sb-") && key.endsWith("-auth-token")) {
      try {
        const parsed = JSON.parse(localStorage.getItem(key));
        return parsed.currentSession ?? parsed; // handle both stored shapes
      } catch {
        return null;
      }
    }
  }
  return null;
}

function sync() {
  const session = readSupabaseSession();
  if (session?.access_token) {
    api.storage.local.set({ session });
  } else {
    api.storage.local.remove("session"); // logged out on the web app -> clear here too
  }
}

sync(); // on page load
window.addEventListener("storage", sync); // and whenever the web app updates the session
