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

function setLogoUploadStatus(statusElement, message, isError) {
  if (!statusElement) {
    return;
  }

  statusElement.textContent = message;
  statusElement.classList.toggle("is-error", Boolean(isError));
}

function assignFileToInput(input, file) {
  if (!input || !file) {
    return false;
  }

  const dataTransfer = new DataTransfer();
  dataTransfer.items.add(file);
  input.files = dataTransfer.files;
  input.dispatchEvent(new Event("change", { bubbles: true }));
  return true;
}

function handleLogoFile(input, statusElement, file, successMessage) {
  if (!file) {
    return;
  }

  if (!file.type.startsWith("image/")) {
    setLogoUploadStatus(statusElement, "That file was not an image.", true);
    return;
  }

  if (file.type !== "image/png") {
    setLogoUploadStatus(statusElement, "Only PNG logos are supported.", true);
    return;
  }

  assignFileToInput(input, file);
  setLogoUploadStatus(statusElement, successMessage, false);
}

function bindLogoUploadField(field) {
  const input = field.querySelector(".logo-input");
  const dropzone = field.querySelector(".logo-dropzone");
  const statusElement = field.querySelector(".logo-upload-status");

  if (!input || !dropzone) {
    return;
  }

  dropzone.addEventListener("click", () => {
    input.click();
  });

  dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      input.click();
    }
  });

  input.addEventListener("change", () => {
    if (!input.files || input.files.length === 0) {
      setLogoUploadStatus(statusElement, "", false);
      return;
    }

    const [file] = input.files;
    if (file.type === "image/png") {
      setLogoUploadStatus(statusElement, `${file.name} ready`, false);
      return;
    }

    setLogoUploadStatus(statusElement, "Only PNG logos are supported.", true);
  });

  dropzone.addEventListener("paste", (event) => {
    const clipboardItems = event.clipboardData ? Array.from(event.clipboardData.items || []) : [];
    const imageItem = clipboardItems.find((item) => item.type.startsWith("image/"));

    if (!imageItem) {
      setLogoUploadStatus(
        statusElement,
        "Clipboard did not contain an image. Please save and upload the logo instead.",
        true
      );
      return;
    }

    event.preventDefault();
    const pastedFile = imageItem.getAsFile();
    handleLogoFile(input, statusElement, pastedFile, "Pasted image ready");
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.add("is-active");
    });
  });

  ["dragleave", "dragend"].forEach((eventName) => {
    dropzone.addEventListener(eventName, () => {
      dropzone.classList.remove("is-active");
    });
  });

  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzone.classList.remove("is-active");

    const files = event.dataTransfer ? Array.from(event.dataTransfer.files || []) : [];
    const [file] = files;

    if (!file) {
      setLogoUploadStatus(statusElement, "No file was dropped.", true);
      return;
    }

    handleLogoFile(input, statusElement, file, "Dropped file ready");
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".form-field").forEach((field) => {
    if (field.querySelector(".logo-input")) {
      bindLogoUploadField(field);
    }
  });

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
