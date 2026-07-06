/*
  AtCoder: submission status table has a cell with class "label-Accepted" /
  "label-WA" etc. after refresh on the submissions page.
*/
(function () {
  function getProblemInfo() {
    const title = document.querySelector("#task-statement .h2, span.h2")?.textContent.trim()
      || document.title.replace(" - AtCoder", "");
    return {
      url: window.location.href.split("?")[0],
      title,
      platform: "atcoder",
      official_difficulty: null,
      tags: "",
      description_snippet: title,
    };
  }

  let lastSeenVerdict = null;

  function checkVerdict() {
    const verdictCell = document.querySelector('td[class*="label-"]');
    if (verdictCell) {
      const text = verdictCell.textContent.trim();
      if (text && text !== lastSeenVerdict && /AC|WA|TLE|RE/i.test(text)) {
        lastSeenVerdict = text;
        window.AlgoLog.showOverlay(getProblemInfo());
      }
    }
  }

  setInterval(checkVerdict, 4000);
})();
