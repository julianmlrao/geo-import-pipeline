document.querySelectorAll("[data-copy]").forEach((b) => {
  b.addEventListener("click", async () => {
    const t = document.querySelector(b.dataset.copy)?.textContent.trim() ?? "";
    try { await navigator.clipboard.writeText(t); b.textContent = "Kopiert"; } catch { b.textContent = "Nicht möglich"; }
    setTimeout(() => (b.textContent = "Kopieren"), 1800);
  });
});
