/* Revalidate the GitHub source facts cached by the theme.
 *
 * The theme stores `__source` in sessionStorage for the whole browser session,
 * so a long-lived tab keeps showing the release tag it saw first. Refresh it
 * after an hour and update the header in place.
 */
(() => {
  const TTL = 60 * 60 * 1000;
  const CHECKED = "__source_checked";

  const run = () => {
    const link = document.querySelector(".md-source");
    const match = link?.href.match(/^https:\/\/github\.com\/([^/]+)\/([^/]+?)\/?$/);
    if (!match || typeof window.__md_get !== "function" || typeof window.__md_set !== "function") {
      return;
    }

    const cached = window.__md_get("__source", sessionStorage);
    if (!cached) {
      return; // the theme fetches it on this load
    }

    const checked = Number(window.__md_get(CHECKED, sessionStorage) || 0);
    if (checked && Date.now() - checked < TTL) {
      return;
    }
    window.__md_set(CHECKED, Date.now(), sessionStorage);

    const [, owner, repo] = match;
    const json = (url) =>
      fetch(url)
        .then((response) => (response.ok ? response.json() : null))
        .catch(() => null);

    Promise.all([
      json(`https://api.github.com/repos/${owner}/${repo}/releases/latest`),
      json(`https://api.github.com/repos/${owner}/${repo}`),
    ]).then(([release, info]) => {
      const next = {
        version: release?.tag_name ?? cached.version,
        stars: info?.stargazers_count ?? cached.stars,
        forks: info?.forks_count ?? cached.forks,
      };
      if (
        next.version === cached.version &&
        next.stars === cached.stars &&
        next.forks === cached.forks
      ) {
        return;
      }

      window.__md_set("__source", next, sessionStorage);
      const setAll = (selector, value) => {
        if (value === undefined) {
          return;
        }
        document.querySelectorAll(selector).forEach((element) => {
          element.textContent = String(value);
        });
      };
      setAll(".md-source__fact--version", next.version);
      setAll(".md-source__fact--stars", next.stars);
      setAll(".md-source__fact--forks", next.forks);
    });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run, { once: true });
  } else {
    run();
  }
})();
