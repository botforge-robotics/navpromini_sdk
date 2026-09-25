// Open all external links in a new tab with noopener noreferrer
function setupExternalLinks() {
  const links = document.querySelectorAll("a[href^='http://'], a[href^='https://']");
  links.forEach(function (link) {
    try {
      const url = new URL(link.href, window.location.origin);
      if (url.hostname !== window.location.hostname) {
        link.setAttribute("target", "_blank");
        link.setAttribute("rel", "noopener noreferrer");
      }
    } catch (e) {
      // Ignore invalid URLs
    }
  });
}

// Support both standard DOMContentLoaded and MkDocs Material instant navigation (document$)
if (typeof document$ !== "undefined") {
  document$.subscribe(setupExternalLinks);
} else {
  document.addEventListener("DOMContentLoaded", setupExternalLinks);
}
