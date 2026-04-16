function buildLogoSearchUrl(nameValue) {
  const rawName = (nameValue || "").trim();
  const searchQuery = rawName ? `${rawName} logo filetype:png` : "company logo png filetype:png";

  return `https://www.google.com/search?tbm=isch&tbs=isz:m&q=${encodeURIComponent(searchQuery)}`;
}

function openLogoSearch(button) {
  const form = button.closest("form");
  const nameInput = form ? form.querySelector('input[name="name"]') : null;
  const imageSearchUrl = buildLogoSearchUrl(nameInput ? nameInput.value : "");
  const searchTab = window.open("", "_blank");

  if (searchTab) {
    searchTab.opener = null;
    searchTab.location = imageSearchUrl;
    return;
  }

  window.location.href = imageSearchUrl;
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".logo-search-button").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      openLogoSearch(button);
    });
  });

  document.querySelectorAll(".copy-url-button").forEach((button) => {
    button.addEventListener("click", () => {
      const url = button.getAttribute("data-copy-url");
      if (!url) {
        return;
      }

      const originalText = button.textContent;
      navigator.clipboard.writeText(url)
        .then(() => {
          button.textContent = "Copied";
        })
        .catch(() => {
          button.textContent = "Copy failed";
        })
        .finally(() => {
          window.setTimeout(() => {
            button.textContent = originalText;
          }, 1500);
        });
    });
  });
});
