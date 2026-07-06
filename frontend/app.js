// DEPRECATED: this plain JS dashboard has been replaced by the React + Vite
// app in src/ (see src/main.tsx / src/App.tsx). Run `npm install && npm run dev`
// in this folder instead of opening this file directly. Left in place only
// because files here can't be deleted automatically - safe to ignore or
// remove by hand.

const BACKEND_URL = "http://localhost:8000";
const API_KEY = "changemetosomethingrandom"; // must match backend API_KEY / extension

async function loadOverview() {
  const resp = await fetch(`${BACKEND_URL}/api/stats/overview`);
  const data = await resp.json();
  const el = document.getElementById("overview");
  el.innerHTML = `
    <div class="stat"><div class="value">${data.total_problems}</div><div class="label">Problems logged</div></div>
    <div class="stat"><div class="value">${data.total_attempts}</div><div class="label">Total attempts</div></div>
    <div class="stat"><div class="value">${data.solved_self_count}</div><div class="label">Solved unaided</div></div>
    <div class="stat"><div class="value">${data.hard_rated_count}</div><div class="label">Rated 4-5</div></div>
  `;
}

function ratingBadge(rating) {
  if (rating == null) return "-";
  return `<span class="rating-badge rating-${rating}">${rating}/5</span>`;
}

async function loadProblems() {
  const minRating = document.getElementById("minRating").value;
  const solvedSelf = document.getElementById("solvedSelf").value;
  const platform = document.getElementById("platform").value;
  const tag = document.getElementById("tagFilter").value;

  const params = new URLSearchParams();
  if (minRating) params.set("min_rating", minRating);
  if (solvedSelf) params.set("solved_self", solvedSelf);
  if (platform) params.set("platform", platform);
  if (tag) params.set("tag", tag);

  const resp = await fetch(`${BACKEND_URL}/api/problems?${params.toString()}`);
  const problems = await resp.json();

  const tbody = document.querySelector("#problemsTable tbody");
  tbody.innerHTML = "";

  problems.forEach((p) => {
    const latest = p.attempts.length
      ? p.attempts.reduce((a, b) => (new Date(a.created_at) > new Date(b.created_at) ? a : b))
      : null;
    const tr = document.createElement("tr");
    renderRow(tr, p, latest);
    tbody.appendChild(tr);
  });
}

const PLATFORMS = ["leetcode", "codeforces", "codechef", "atcoder", "gfg"];

function renderRow(tr, p, latest) {
  tr.innerHTML = `
    <td><a href="${p.url}" target="_blank" style="color:#818cf8; text-decoration:none;">${p.title}</a></td>
    <td>${p.platform}</td>
    <td>${p.tags || "-"}</td>
    <td>${ratingBadge(latest ? latest.rating : null)}</td>
    <td>${latest ? (latest.solved_self ? "Yes" : "No") : "-"}</td>
    <td>${p.attempts.length}</td>
    <td>
      <span class="similar-link" data-id="${p.id}">Find similar</span>
      <span class="edit-link" title="Edit or delete" style="cursor:pointer; margin-left:8px;">✏️</span>
    </td>
  `;
  tr.querySelector(".similar-link").addEventListener("click", () => showSimilar(p.id));
  tr.querySelector(".edit-link").addEventListener("click", () => renderEditRow(tr, p, latest));
}

function renderEditRow(tr, p, latest) {
  const platformOpts = PLATFORMS
    .map((v) => `<option value="${v}" ${v === p.platform ? "selected" : ""}>${v}</option>`)
    .join("");
  const ratingOpts = [1, 2, 3, 4, 5]
    .map((v) => `<option value="${v}" ${latest && latest.rating === v ? "selected" : ""}>${v}</option>`)
    .join("");
  const solved = latest ? latest.solved_self : false;
  tr.innerHTML = `
    <td>
      <input class="e-title" value="${p.title.replace(/"/g, "&quot;")}" placeholder="Title" style="width:100%" />
      <input class="e-url" value="${p.url.replace(/"/g, "&quot;")}" placeholder="URL" style="width:100%; margin-top:4px" />
    </td>
    <td><select class="e-platform">${platformOpts}</select></td>
    <td><input class="e-tags" value="${(p.tags || "").replace(/"/g, "&quot;")}" placeholder="tags" style="width:100%" /></td>
    <td><select class="e-rating">${ratingOpts}</select></td>
    <td>
      <select class="e-solved">
        <option value="true" ${solved ? "selected" : ""}>Yes</option>
        <option value="false" ${solved ? "" : "selected"}>No</option>
      </select>
    </td>
    <td>${p.attempts.length}</td>
    <td>
      <button class="e-save">Save</button>
      <button class="e-delete">Delete</button>
      <button class="e-cancel">Cancel</button>
    </td>
  `;

  tr.querySelector(".e-cancel").addEventListener("click", () => renderRow(tr, p, latest));

  tr.querySelector(".e-save").addEventListener("click", async () => {
    const payload = {
      url: tr.querySelector(".e-url").value.trim(),
      title: tr.querySelector(".e-title").value.trim(),
      platform: tr.querySelector(".e-platform").value,
      tags: tr.querySelector(".e-tags").value.trim() || null,
      rating: parseInt(tr.querySelector(".e-rating").value, 10),
      solved_self: tr.querySelector(".e-solved").value === "true",
    };
    const resp = await fetch(`${BACKEND_URL}/api/problems/${p.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
      body: JSON.stringify(payload),
    });
    if (resp.ok) {
      loadOverview();
      loadProblems();
    } else {
      alert(`Failed to save (${resp.status}).`);
    }
  });

  tr.querySelector(".e-delete").addEventListener("click", async () => {
    if (!confirm(`Delete "${p.title}" and all its attempts?`)) return;
    const resp = await fetch(`${BACKEND_URL}/api/problems/${p.id}`, {
      method: "DELETE",
      headers: { "X-API-Key": API_KEY },
    });
    if (resp.ok) {
      loadOverview();
      loadProblems();
    } else {
      alert(`Failed to delete (${resp.status}).`);
    }
  });
}

async function showSimilar(problemId) {
  const resp = await fetch(`${BACKEND_URL}/api/problems/${problemId}/similar`);
  const results = await resp.json();
  const panel = document.getElementById("similarPanel");
  const list = document.getElementById("similarList");
  list.innerHTML = results.length
    ? results.map((r) => `
        <div class="item">
          <a href="${r.url}" target="_blank" style="color:#818cf8;">${r.title}</a>
          — ${r.platform} — similarity ${r.similarity}
          ${r.latest_rating ? `— you rated it ${r.latest_rating}/5` : ""}
        </div>
      `).join("")
    : "<div class='item'>No similar problems found yet.</div>";
  panel.style.display = "block";
}

document.getElementById("closeSimilar").addEventListener("click", () => {
  document.getElementById("similarPanel").style.display = "none";
});

document.getElementById("applyFilters").addEventListener("click", loadProblems);

document.getElementById("addProblemBtn").addEventListener("click", async () => {
  const url = document.getElementById("addUrl").value.trim();
  const title = document.getElementById("addTitle").value.trim();
  if (!url || !title) {
    alert("URL and title are required.");
    return;
  }
  const payload = {
    url,
    title,
    platform: document.getElementById("addPlatform").value,
    tags: document.getElementById("addTags").value.trim() || null,
    rating: parseInt(document.getElementById("addRating").value, 10),
    solved_self: document.getElementById("addSolvedSelf").value === "true",
  };
  const resp = await fetch(`${BACKEND_URL}/api/attempts`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    body: JSON.stringify(payload),
  });
  if (resp.ok) {
    document.getElementById("addUrl").value = "";
    document.getElementById("addTitle").value = "";
    document.getElementById("addTags").value = "";
    loadOverview();
    loadProblems();
  } else {
    alert(`Failed to add problem (${resp.status}). Check the API key.`);
  }
});

document.getElementById("trainModelBtn").addEventListener("click", async () => {
  const resp = await fetch(`${BACKEND_URL}/api/calibration/train`, { method: "POST" });
  const data = await resp.json();
  alert(data.trained ? `Model trained on ${data.samples_used} attempts.` : data.reason);
});

document.getElementById("sendDigestBtn").addEventListener("click", async () => {
  const resp = await fetch(`${BACKEND_URL}/api/stats/digest/send-now`, { method: "POST" });
  const data = await resp.json();
  alert(data.narrative || "Digest sent (check console/email).");
});

loadOverview();
loadProblems();
