/*
  Shared across every platform content script.
  Each platform script (leetcode.js, codeforces.js, ...) is responsible for:
    1. Detecting a submission verdict on the page (MutationObserver on the
       verdict/result element - simplest approach that works across all 5
       sites without needing platform-specific API reverse-engineering).
    2. Pulling problem metadata (title, tags, difficulty, url).
    3. Calling window.AlgoLog.showOverlay(problemInfo) when a verdict appears.

  NOTE ON ROBUSTNESS: LeetCode, Codeforces, CodeChef, AtCoder, and GFG all
  redesign their DOM periodically. The selectors in each platform file are a
  reasonable starting point, not guaranteed-forever - if detection stops
  firing, open devtools on the verdict element and update the selector in
  that platform's file. The manual "click the extension icon" popup path
  always works regardless of DOM changes, as a fallback.
*/

window.AlgoLog = (function () {
  const BACKEND_URL = "http://localhost:8000";

  function getApiKey() {
    return new Promise((resolve) => {
      chrome.storage.sync.get(["apiKey"], (result) => {
        resolve(result.apiKey || "change-me-to-something-random");
      });
    });
  }

  async function submitAttempt(payload) {
    const apiKey = await getApiKey();
    try {
      const resp = await fetch(`${BACKEND_URL}/api/attempts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
        },
        body: JSON.stringify(payload),
      });
      return await resp.json();
    } catch (e) {
      console.error("[AlgoLog] Failed to submit attempt:", e);
      return null;
    }
  }

  function removeExisting() {
    const existing = document.getElementById("algolog-overlay");
    if (existing) existing.remove();
  }

  function showOverlay(problemInfo) {
    removeExisting();

    const box = document.createElement("div");
    box.id = "algolog-overlay";
    box.innerHTML = `
      <span class="algolog-close">&times;</span>
      <h3>Rate this problem</h3>
      <div class="algolog-row">
        <div class="algolog-stars">
          ${[1, 2, 3, 4, 5].map((n) => `<span data-star="${n}">★</span>`).join("")}
        </div>
        <span style="opacity:0.7;">difficulty</span>
      </div>
      <div class="algolog-row">
        <button class="algolog-toggle" data-solved="true">Solved myself</button>
        <button class="algolog-toggle" data-solved="false">Needed help</button>
      </div>
      <textarea placeholder="Optional note (what tripped you up, key insight, etc.)"></textarea>
      <button class="algolog-submit">Save</button>
    `;
    document.body.appendChild(box);

    let rating = 0;
    let solvedSelf = null;

    box.querySelectorAll(".algolog-stars span").forEach((star) => {
      star.addEventListener("click", () => {
        rating = parseInt(star.dataset.star, 10);
        box.querySelectorAll(".algolog-stars span").forEach((s) => {
          s.classList.toggle("active", parseInt(s.dataset.star, 10) <= rating);
        });
      });
    });

    box.querySelectorAll(".algolog-toggle").forEach((btn) => {
      btn.addEventListener("click", () => {
        solvedSelf = btn.dataset.solved === "true";
        box.querySelectorAll(".algolog-toggle").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
      });
    });

    box.querySelector(".algolog-close").addEventListener("click", removeExisting);

    box.querySelector(".algolog-submit").addEventListener("click", async () => {
      if (!rating || solvedSelf === null) {
        alert("Please pick a difficulty rating and whether you solved it yourself.");
        return;
      }
      const notes = box.querySelector("textarea").value;
      const payload = { ...problemInfo, rating, solved_self: solvedSelf, notes };
      const result = await submitAttempt(payload);
      box.innerHTML = result
        ? `<div style="text-align:center;padding:10px;">Saved ✓</div>`
        : `<div style="text-align:center;padding:10px;color:#f87171;">Backend unreachable. Is it running?</div>`;
      setTimeout(removeExisting, 1500);
    });
  }

  return { showOverlay, submitAttempt };
})();
