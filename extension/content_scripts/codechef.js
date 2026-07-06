/*
  CodeChef: verdict shows up on the submission result page/panel, typically
  containing "Accepted" / "Wrong Answer" text. Selectors here target the
  common result panel; adjust if CodeChef's React app changes class names.
*/
(function () {
  function getProblemInfo() {
    const title = document.querySelector("h1, ._problem-heading_")?.textContent.trim()
      || document.title.replace(" | CodeChef", "");
    return {
      url: window.location.href.split("?")[0],
      title,
      platform: "codechef",
      official_difficulty: null,
      tags: "",
      description_snippet: title,
    };
  }

  let lastFired = 0;
  const observer = new MutationObserver(() => {
    const resultEl = document.querySelector('[class*="result"], [class*="verdict"]');
    if (resultEl && Date.now() - lastFired > 3000) {
      const text = resultEl.textContent.trim();
      if (/Accepted|Wrong Answer|Time Limit Exceeded|Runtime Error/i.test(text)) {
        lastFired = Date.now();
        window.AlgoLog.showOverlay(getProblemInfo());
      }
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
