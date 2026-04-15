document.addEventListener("click", async (event) => {
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
