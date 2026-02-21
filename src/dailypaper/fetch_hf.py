import json
import time
from pathlib import Path
import requests

from .config import SETTINGS, PATHS

def fetch_hf_daily(date_yyyy_mm_dd: str, save_raw: bool = True) -> str:

    url = SETTINGS.hf_api_base + date_yyyy_mm_dd

    # 간단한 재시도(backoff): 429/5xx 대비
    backoffs = [1, 2, 4, 8]
    last_err = None

    for i, sec in enumerate([0] + backoffs):
        if sec:
            time.sleep(sec)

        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                raw = r.text
                if save_raw:
                    PATHS.raw.mkdir(parents=True, exist_ok=True)
                    raw_path = PATHS.raw / f"{date_yyyy_mm_dd}.json"
                    raw_path.write_text(raw, encoding="utf-8")
                return raw

            if r.status_code in (429, 500, 502, 503, 504):
                last_err = RuntimeError(f"HF HTTP {r.status_code}: {r.text[:300]}")
                continue

            raise RuntimeError(f"HF HTTP {r.status_code}: {r.text[:300]}")

        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"HF fetch failed after retries: {last_err}")

def load_raw(date_yyyy_mm_dd: str) -> str:
    p = PATHS.raw / f"{date_yyyy_mm_dd}.json"
    return p.read_text(encoding="utf-8")
