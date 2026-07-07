// Chrome's service worker needs importScripts to load config.js; Firefox's event
// page loads it via the manifest "scripts" array instead (no importScripts there).
if (typeof importScripts === "function") importScripts("config.js"); // gives us `api` + URL constants

// First install: try to pop the action popup open (Chrome 127+), but from
// onInstalled there's no user gesture, so it often no-ops — and Firefox/Safari
// reject it entirely. Fall back to an onboarding tab so first-run always shows something.
api.runtime.onInstalled.addListener(async (details) => {
  if (details.reason !== "install") return;
  try {
    if (!api.action?.openPopup) throw new Error("openPopup unavailable");
    await api.action.openPopup();
  } catch {
    await api.tabs.create({ url: api.runtime.getURL("onboarding.html") });
  }
});
