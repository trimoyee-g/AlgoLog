let rating = 0;
let solvedSelf = null;
let accessToken = null;

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
  return "other";
}

function showLoggedOut() {
  document.getElementById("loggedOut").classList.remove("hidden");
  document.getElementById("rating").classList.add("hidden");
}

function showRating() {
  document.getElementById("rating").classList.remove("hidden");
  document.getElementById("loggedOut").classList.add("hidden");
}

document.getElementById("loginBtn").addEventListener("click", () => {
  openLogin();
  document.getElementById("loginHint").textContent =
    "After you log in, reopen this popup — it'll unlock automatically.";
});

document.getElementById("save").addEventListener("click", async () => {
  const statusEl = document.getElementById("status");
  const saveBtn = document.getElementById("save");
  if (!rating || solvedSelf === null) {
    statusEl.textContent = "Pick a rating and yes/no first.";
    return;
  }
  const tags = document.getElementById("tags").value.trim();
  if (!tags) {
    statusEl.textContent = "Add at least one tag — that's what powers 'find similar'.";
    return;
  }
  const [tab] = await api.tabs.query({ active: true, currentWindow: true });
  const notes = document.getElementById("notes").value;
  const title = document.getElementById("title").value.trim() || tab.title;

  saveBtn.disabled = true;
  saveBtn.textContent = "Saving…";
  statusEl.textContent = "";

  try {
    const resp = await fetch(`${BACKEND_URL}/api/attempts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        url: tab.url.split("?")[0],
        title,
        platform: guessPlatform(tab.url),
        official_difficulty: null,
        tags,
        rating,
        solved_self: solvedSelf,
        notes,
      }),
    });
    if (resp.ok) {
      statusEl.textContent = "Saved ✓";
    } else if (resp.status === 401) {
      // token rejected/expired mid-session -> back to login
      await api.storage.local.remove("session");
      statusEl.textContent = "Session expired — please log in again.";
      showLoggedOut();
    } else {
      statusEl.textContent = "Backend error - check it's running.";
    }
  } catch (e) {
    statusEl.textContent = "Backend unreachable at localhost:8000.";
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = "+ Add problem";
  }
});

// On open: decide which view to show based on a valid session.
(async () => {
  accessToken = await getAccessToken();
  if (accessToken) {
    showRating();
    const [tab] = await api.tabs.query({ active: true, currentWindow: true });
    if (tab?.title) document.getElementById("title").value = tab.title;
  } else {
    showLoggedOut();
  }
})();
