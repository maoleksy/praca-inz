importScripts("config.js");

const ALARM_NAME = "pollCartQueue";

chrome.runtime.onInstalled.addListener(async () => {
  const current = await chrome.storage.local.get(["apiBase", "autoAddEnabled"]);
  if (!current.apiBase) {
    await chrome.storage.local.set({ apiBase: DEFAULT_API_BASE });
  }
  if (current.autoAddEnabled === undefined) {
    await chrome.storage.local.set({ autoAddEnabled: true });
  }
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: 1 });
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) {
    pollQueue();
  }
});

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.type === "POLL_NOW") {
    pollQueue();
  }
  if (msg.type === "ADD_TO_CART_RESULT") {
    handleAddResult(msg, sender.tab && sender.tab.id);
  }
});

async function getApiBase() {
  const { apiBase } = await chrome.storage.local.get("apiBase");
  return apiBase || DEFAULT_API_BASE;
}

async function pollQueue() {
  const { autoAddEnabled } = await chrome.storage.local.get("autoAddEnabled");
  if (autoAddEnabled === false) return;

  const base = await getApiBase();

  try {
    const res = await fetch(`${base}/api/cart-queue`);
    if (!res.ok) return;
    const items = await res.json();

    for (const item of items) {
      await openProductTab(item);
    }
  } catch (e) {
    console.error("[ZalandoCartMonitor] poll failed:", e);
  }
}

async function openProductTab(item) {
  const url = new URL(item.url);
  url.searchParams.set("extQueueId", item.id);
  url.searchParams.set("extSize", item.size);

  await chrome.tabs.create({ url: url.toString(), active: false });
}

async function handleAddResult(msg, tabId) {
  const base = await getApiBase();

  try {
    await fetch(`${base}/api/cart-queue/ack`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: [Number(msg.queueId)] }),
    });
  } catch (e) {
    console.error("[ZalandoCartMonitor] ack failed:", e);
  }

  if (msg.ok) {
    await chrome.tabs.create({
      url: `${CART_URL}?extFillPromo=1`,
      active: true,
    });
  } else {
    console.warn("[ZalandoCartMonitor] nie udało się dodać do koszyka:", msg.reason);
  }

  if (tabId) {
    setTimeout(() => chrome.tabs.remove(tabId).catch(() => {}), 2000);
  }
}
