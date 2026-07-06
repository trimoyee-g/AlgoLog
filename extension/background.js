chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.get(["apiKey"], (result) => {
    if (!result.apiKey) {
      chrome.storage.sync.set({ apiKey: "change-me-to-something-random" });
    }
  });
});
