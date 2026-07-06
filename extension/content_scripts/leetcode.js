/*
  LeetCode: after a submission, a result banner appears containing text like
  "Accepted" or "Wrong Answer". We watch for that element via MutationObserver.
  (A more robust approach would intercept the GraphQL submission-check response,
  but DOM-watching is simpler to maintain and good enough for a personal tool.)
*/
(function () {
  function getProblemInfo() {
    const titleEl = document.querySelector('[data-cy="question-title"], a[href*="/problems/"] > div');
    const title = titleEl ? titleEl.textContent.trim() : document.title.replace(" - LeetCode", "");
    const tagEls = document.querySelectorAll('a[href*="/tag/"]');
    const tags = Array.from(tagEls).map((t) => t.textContent.trim()).join(",");
    const diffEl = document.querySelector('[diff], .text-difficulty-easy, .text-difficulty-medium, .text-difficulty-hard');
    const difficulty = diffEl ? diffEl.textContent.trim() : null;
    return {
      url: window.location.href.split("?")[0],
      title,
      platform: "leetcode",
      official_difficulty: difficulty,
      tags,
      description_snippet: title, // full description scraping is fragile; title+tags is enough for embeddings
    };
  }

  let lastFired = 0;
  const observer = new MutationObserver(() => {
    const resultEl = document.querySelector('[data-e2e-locator="submission-result"]');
    if (resultEl && Date.now() - lastFired > 3000) {
      const text = resultEl.textContent.trim();
      if (/Accepted|Wrong Answer|Runtime Error|Time Limit Exceeded/i.test(text)) {
        lastFired = Date.now();
        window.AlgoLog.showOverlay(getProblemInfo());
      }
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
