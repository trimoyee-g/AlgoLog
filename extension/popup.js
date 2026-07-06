const BACKEND_URL = "http://localhost:8000";

let rating = 0;
let solvedSelf = null;

document.querySelectorAll("#stars span").forEach((star) => {
  star.addEventListener("click", () => {
    rating = parseInt(star.dataset.star, 10);
    document.querySelectorAll("#stars span").forEach((s) => {
      s.classList.toggle("active", parseInt(s.dataset.star, 10) <= rating);
    });
  });
});

document.querySelectorAll("#toggles button").forEach((btn) => {
  btn.addEventListener("click", () => {
    solvedSelf = btn.dataset.solved === "true";
    document.querySelectorAll("#toggles button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
  });
});

function guessPlatform(url) {
  if (url.includes("leetcode.com")) return "leetcode";
  if (url.includes("codeforces.com")) return "codeforces";
  if (url.includes("codechef.com")) return "codechef";
  if (url.includes("atcoder.jp")) return "atcoder";
  if (url.includes("geeksforgeeks.org")) return "gfg";
  return "leetcode";
}

document.getElementById("save").addEventListener("click", async () => {
  const statusEl = document.getElementById("status");
  if (!rating || solvedSelf === null) {
    statusEl.textContent = "Pick a rating and yes/no first.";
    return;
  }
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const notes = document.getElementById("notes").value;

  chrome.storage.sync.get(["apiKey"], async (result) => {
    const apiKey = result.apiKey || "change-me-to-something-random";
    try {
      const resp = await fetch(`${BACKEND_URL}/api/attempts`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({
          url: tab.url.split("?")[0],
          title: tab.title,
          platform: guessPlatform(tab.url),
          official_difficulty: null,
          tags: "",
          description_snippet: tab.title,
          rating,
          solved_self: solvedSelf,
          notes,
        }),
      });
      if (resp.ok) {
        statusEl.textContent = "Saved ✓";
      } else {
        statusEl.textContent = "Backend error - check it's running.";
      }
    } catch (e) {
      statusEl.textContent = "Backend unreachable at localhost:8000.";
    }
  });
});

document.getElementById("settingsToggle").addEventListener("click", () => {
  const panel = document.getElementById("settingsPanel");
  panel.style.display = panel.style.display === "none" ? "block" : "none";
  chrome.storage.sync.get(["apiKey"], (result) => {
    document.getElementById("apiKeyInput").value = result.apiKey || "";
  });
});

document.getElementById("saveKey").addEventListener("click", () => {
  const val = document.getElementById("apiKeyInput").value;
  chrome.storage.sync.set({ apiKey: val }, () => {
    document.getElementById("status").textContent = "API key saved.";
  });
});
