// Selektory oparte na widocznym tekście, nie na klasach CSS/data-testid,
// bo te ostatnie zmieniają się na Zalando bez ostrzeżenia. Jeśli coś tu
// przestanie działać, najpierw sprawdź w devtoolsach jaki tekst mają
// obecnie przyciski rozmiaru / "Dodaj do koszyka" / pole kodu rabatowego.

function findByText(selectors, textMatcher) {
  for (const sel of selectors) {
    const els = Array.from(document.querySelectorAll(sel));
    const match = els.find((el) => textMatcher((el.innerText || el.textContent || "").trim()));
    if (match) return match;
  }
  return null;
}

function waitFor(fn, { timeout = 15000, interval = 400 } = {}) {
  return new Promise((resolve) => {
    const start = Date.now();
    const tick = () => {
      const result = fn();
      if (result) {
        resolve(result);
        return;
      }
      if (Date.now() - start >= timeout) {
        resolve(null);
        return;
      }
      setTimeout(tick, interval);
    };
    tick();
  });
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function runAddToCartFlow(queueId, targetSize) {
  const normalizedTarget = targetSize.trim().toLowerCase();

  const sizeEl = await waitFor(() =>
    findByText(
      ["button", '[role="radio"]', '[role="button"]', "li", "label"],
      (text) => text.toLowerCase() === normalizedTarget
    )
  );

  if (!sizeEl) {
    chrome.runtime.sendMessage({
      type: "ADD_TO_CART_RESULT",
      queueId,
      ok: false,
      reason: "size-not-found",
    });
    return;
  }

  sizeEl.click();
  await sleep(800);

  const addButton = await waitFor(() =>
    findByText(["button"], (text) => /dodaj do koszyka/i.test(text))
  );

  if (!addButton) {
    chrome.runtime.sendMessage({
      type: "ADD_TO_CART_RESULT",
      queueId,
      ok: false,
      reason: "add-button-not-found",
    });
    return;
  }

  addButton.click();
  await sleep(1200);

  chrome.runtime.sendMessage({ type: "ADD_TO_CART_RESULT", queueId, ok: true });
}

async function runPromoFlow() {
  const { discountCode } = await chrome.storage.local.get("discountCode");
  if (!discountCode) return;

  const input = await waitFor(() => {
    const candidates = Array.from(document.querySelectorAll("input"));
    return candidates.find((el) => {
      const hint = `${el.placeholder || ""} ${el.name || ""} ${el.id || ""}`.toLowerCase();
      return hint.includes("kod") || hint.includes("promo") || hint.includes("voucher");
    });
  });

  if (!input) return;

  input.focus();
  input.value = discountCode;
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));

  await sleep(300);

  const applyButton = await waitFor(() =>
    findByText(["button"], (text) => /zastosuj|dodaj kod|aktywuj/i.test(text))
  );

  if (applyButton) applyButton.click();
}

(function main() {
  const params = new URLSearchParams(location.search);
  const queueId = params.get("extQueueId");
  const targetSize = params.get("extSize");
  const fillPromo = params.get("extFillPromo");

  if (queueId && targetSize) {
    runAddToCartFlow(queueId, targetSize);
  } else if (fillPromo) {
    runPromoFlow();
  }
})();
