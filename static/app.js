document.addEventListener("click", async (event) => {
  const logoSearchButton = event.target.closest(".logo-search-button");
  if (logoSearchButton) {
    const form = logoSearchButton.closest("form");
    const nameInput = form?.querySelector('input[name="name"]');
    const rawName = nameInput?.value.trim() || "";
    const searchQuery = rawName ? `${rawName} logo filetype:png` : "company logo png filetype:png";
    const imageSearchUrl = `https://www.google.com/search?tbm=isch&tbs=isz:m&q=${encodeURIComponent(searchQuery)}`;

    window.open(imageSearchUrl, "_blank", "noopener,noreferrer");
    return;
  }

  const button = event.target.closest(".copy-url-button");
  if (!button) {
    return;
  }

  const url = button.getAttribute("data-copy-url");
  if (!url) {
    return;
  }

  const originalText = button.textContent;
  try {
    await navigator.clipboard.writeText(url);
    button.textContent = "Copied";
  } catch {
    button.textContent = "Copy failed";
  }

  window.setTimeout(() => {
    button.textContent = originalText;
  }, 1500);
});
