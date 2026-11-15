const DEFAULT_API_BASE = "http://51.255.34.32:5050";

const els = {
  autoAddEnabled: document.getElementById("autoAddEnabled"),
  discountCode: document.getElementById("discountCode"),
  apiBase: document.getElementById("apiBase"),
  saveBtn: document.getElementById("saveBtn"),
  pollNowBtn: document.getElementById("pollNowBtn"),
  status: document.getElementById("status"),
};

function showStatus(text) {
  els.status.textContent = text;
  setTimeout(() => {
    els.status.textContent = "";
  }, 2000);
}

async function load() {
  const data = await chrome.storage.local.get(["autoAddEnabled", "discountCode", "apiBase"]);
  els.autoAddEnabled.checked = data.autoAddEnabled !== false;
  els.discountCode.value = data.discountCode || "";
  els.apiBase.value = data.apiBase || DEFAULT_API_BASE;
}

els.saveBtn.addEventListener("click", async () => {
  await chrome.storage.local.set({
    autoAddEnabled: els.autoAddEnabled.checked,
    discountCode: els.discountCode.value.trim(),
    apiBase: els.apiBase.value.trim() || DEFAULT_API_BASE,
  });
  showStatus("Zapisano ✔");
});

els.pollNowBtn.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "POLL_NOW" });
  showStatus("Sprawdzanie...");
});

load();
