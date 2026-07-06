/*
  GeeksforGeeks Practice: verdict appears in the result panel after running
  "Submit" on a practice problem (class names vary; this targets the common
  result/verdict container). GFG's article pages (non-practice) have no
  judge, so this only fires on /problems/ practice pages.
*/
(function () {
  if (!window.location.href.includes("/problems/")) return;

  function getProblemInfo() {
    const title = document.querySelector(".problem-tab h2, h1")?.textContent.trim()
      || document.title.replace(" | Practice | GeeksforGeeks", "");
    const tagEls = document.querySelectorAll('.problem_tags a, a[href*="/tag/"]');
    const tags = Array.from(tagEls).map((t) => t.textContent.trim()).join(",");
    return {
      url: window.location.href.split("?")[0],
      title,
      platform: "gfg",
      official_difficulty: null,
      tags,
      description_snippet: title,
    };
  }

  let lastFired = 0;
  const observer = new MutationObserver(() => {
    const resultEl = document.querySelector('[class*="verdict"], [class*="result-panel"]');
    if (resultEl && Date.now() - lastFired > 3000) {
      const text = resultEl.textContent.trim();
      if (/Correct Answer|Wrong Answer|Compilation Error|Runtime Error/i.test(text)) {
        lastFired = Date.now();
        window.AlgoLog.showOverlay(getProblemInfo());
      }
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
