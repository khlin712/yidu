document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const value = button.dataset.copy || "";
    try {
      await navigator.clipboard.writeText(value);
      const original = button.textContent;
      button.textContent = "已複製";
      window.setTimeout(() => { button.textContent = original; }, 1600);
    } catch {
      button.textContent = "請手動複製";
      window.setTimeout(() => { button.textContent = "複製"; }, 1600);
    }
  });
});
