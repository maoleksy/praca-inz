# services/health.py
# Stan każdego monitora w pamięci procesu (scheduler działa w tym samym
# procesie co Flask): kiedy ostatnio przeszedł, ile produktów, ostatni błąd.
import time

_state = {}


def record(shop, checked, failed, error=None):
    s = _state.setdefault(shop, {"last_ok": None, "last_error": None, "last_error_at": None})
    now = time.time()
    s["last_run"] = now
    s["checked"] = checked
    s["failed"] = failed
    if failed == 0:
        s["last_ok"] = now
    if error is not None:
        s["last_error"] = str(error)[:300]
        s["last_error_at"] = now


def snapshot():
    now = time.time()
    out = {}
    for shop, s in _state.items():
        age = now - s["last_ok"] if s.get("last_ok") else None
        if s.get("failed") and s.get("checked") is not None and s["failed"] >= max(1, s["checked"]):
            level = "down"
        elif s.get("failed"):
            level = "warn"
        elif age is not None and age < 600:
            level = "ok"
        else:
            level = "warn"
        out[shop] = {**s, "level": level, "ok_ago": age}
    return out
