// Get Started: if already logged in, tell them to use the toolbar icon;
// otherwise send them to the web app to log in (per the agreed flow).
document.getElementById("getStarted").addEventListener("click", async () => {
  const token = await getAccessToken();
  const hint = document.getElementById("hint");
  if (token) {
    hint.textContent =
      "You're signed in ✓  Open a problem page and click the AlgoLog icon in your toolbar to rate it.";
  } else {
    openLogin();
    hint.textContent = "Opening the login page… once you're in, click the AlgoLog toolbar icon to start rating.";
  }
});
