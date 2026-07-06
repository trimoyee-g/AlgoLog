/*
  Codeforces: verdict appears in the submissions table (class "verdict-accepted"
  / "verdict-rejected") on the status/submission page after a submit + refresh,
  or on the problem page's "My submissions" tab. We poll periodically since CF
  doesn't live-update the table via JS you can hook without their internal API.
*/
(function () {
  function getProblemInfo() {
    const title = document.querySelector(".problem-statement .title")?.textContent.trim()
      || document.title.replace(" - Codeforces", "");
    const tagEls = document.querySelectorAll(".tag-box");
    const tags = Array.from(tagEls).map((t) => t.textContent.trim()).join(",");
    const ratingEl = document.querySelector('span[title="Difficulty"]');
    return {
      url: window.location.href.split("?")[0],
      title,
      platform: "codeforces",
      official_difficulty: ratingEl ? ratingEl.textContent.trim() : null,
      tags,
      description_snippet: title,
    };
  }

  let lastSeenVerdict = null;

  function checkVerdict() {
    const verdictCell = document.querySelector("table.status-frame-datatable tr:nth-child(2) .submissionVerdictWrapper, .verdict-accepted, .verdict-rejected");
    if (verdictCell) {
      const text = verdictCell.textContent.trim();
      if (text && text !== lastSeenVerdict && /Accepted|Wrong answer|Time limit|Runtime error/i.test(text)) {
        lastSeenVerdict = text;
        window.AlgoLog.showOverlay(getProblemInfo());
      }
    }
  }

  setInterval(checkVerdict, 4000);
})();
