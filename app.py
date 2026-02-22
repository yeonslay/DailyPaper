import html
import hashlib
import json
import os
import re
import shutil
import sqlite3
import ssl
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

from dotenv import load_dotenv
load_dotenv()
try:
    import certifi
except Exception:
    certifi = None

import pandas as pd
import requests
import streamlit as st
from openai import OpenAI
# -----------------------------
# Config / Paths
# -----------------------------
ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "db" / "dailypaper.sqlite3"
FAVORITES_ROOT = ROOT.parent / "DailyPaperFavorite"
ZOTERO_API_KEY = os.environ.get("ZOTERO_API_KEY", "").strip()
ZOTERO_USER_ID = os.environ.get("ZOTERO_USER_ID", "").strip()
ZOTERO_COLLECTION = os.environ.get("ZOTERO_COLLECTION", "").strip()
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where()) if certifi else ssl.create_default_context()
APP_LABEL_CONFIDENCE_THRESHOLD = 0.60

class ZoteroSyncError(RuntimeError):
    def __init__(self, message: str, logs: list[str] | None = None):
        super().__init__(message)
        self.logs = logs or []

st.set_page_config(
    page_title="Daily Papers",
    page_icon="🗞️",
    layout="wide",
)

# -----------------------------
# CSS (웹페이지 느낌)
# -----------------------------
st.markdown(
    """
<style>

:root { --bg:#0b0f14; --panel:#121823; --card:#161f2e; --text:#e8eefc; --muted:#a8b3c7; --line:#22304a; --chip:#1d2b44; --accent:#7aa2ff; }
html, body, [class*="css"] { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial !important; }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1400px; }
[data-testid="stAppViewContainer"] { background: radial-gradient(1200px 700px at 20% 0%, rgba(122,162,255,0.14), rgba(0,0,0,0)), linear-gradient(180deg, #070a0f, var(--bg)); color: var(--text); }
[data-testid="stSidebar"] { background: rgba(18,24,35,.92); border-right: 1px solid rgba(255,255,255,.06); }
h1,h2,h3 { letter-spacing: -0.02em; }
.small { color: var(--muted); font-size: 0.92rem; }

.card {
  background: linear-gradient(180deg, rgba(28,40,60,.98), rgba(18,24,35,.98));
  border: 1px solid rgba(255,255,255,.10);
  border-radius: 18px;
  padding: 18px 24px 16px 24px;
  box-shadow: 0 12px 32px rgba(0,0,0,.28);
}
.cardTop { display:flex; justify-content:space-between; align-items:center; gap:10px; margin-bottom:8px; }
.pid { color: var(--muted); font-size: 0.85rem; }
.metaSep { color: rgba(255,255,255,0.25); margin: 0 6px; font-weight: 300; }
.badge {
  display:inline-flex; align-items:center; gap:6px;
  border: 1px solid rgba(122,162,255,.25);
  color: var(--accent);
  background: rgba(122,162,255,.08);
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 0.82rem;
  text-decoration:none;
  white-space: nowrap;
  flex-shrink: 0;
}
a.badge { text-decoration: underline; }
a.badge:hover { opacity: 0.9; }
span.badge--nolink { color: var(--muted); cursor: default; }
.title { font-weight: 900; font-size: 1.08rem; line-height: 1.38; margin: 0 0 8px 0; }
.one {
  color: var(--text);
  font-size: 0.95rem;
  line-height: 1.55;
  margin: 0 0 10px 0;
}
.chips { display:flex; flex-wrap:wrap; gap:6px; }
.chip {
  background: rgba(29,43,68,.9);
  border: 1px solid rgba(255,255,255,.06);
  color: #cfe0ff;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 0.80rem;
}
[data-testid="stButton"] {
  margin-top: -40px;
  margin-bottom: 8px;
}
/* 자세히 expander를 위 카드에 더 가깝게 */
[data-testid="stExpander"] {
  margin-top: -20px !important;
  margin-bottom: 2px !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span {
  color: var(--muted) !important;
}
[data-testid="stButton"] > button[kind="tertiary"] {
  width: 36px !important;
  min-width: 36px !important;
  height: 36px !important;
  min-height: 36px !important;
  border-radius: 999px !important;
  padding: 0 !important;
  font-size: 1.2rem !important;
  line-height: 1 !important;
  border: 1px solid rgba(255,255,255,.12) !important;
  background: rgba(17,24,36,.82) !important;
}
[data-testid="stButton"] > button[kind="tertiary"]:hover,
[data-testid="stButton"] > button[kind="tertiary"]:active,
[data-testid="stButton"] > button[kind="tertiary"]:focus {
  transform: none !important;
}
.hr { height: 1px; background: rgba(255,255,255,.06); margin: 10px 0; }
.kv b { display:block; color: var(--muted); font-size: 0.82rem; margin-bottom: 6px; }
.kv div { font-size: 0.92rem; line-height: 1.5; }
.footerHint { color: var(--muted); font-size: 0.86rem; margin-top: 6px; }
/* ✅ Streamlit 상단 헤더/툴바 배경 제거 */
[data-testid="stHeader"] {
  background: transparent !important;
}
[data-testid="stToolbar"] {
  background: transparent !important;
}
[data-testid="stDecoration"] {
  background: transparent !important;
}
/* ✅ 메인 영역 st.metric 글씨 밝게 */
[data-testid="stAppViewContainer"] [data-testid="stMetricLabel"] {
  color: rgba(255,255,255,0.92) !important;
  font-weight: 700 !important;
}
[data-testid="stAppViewContainer"] [data-testid="stMetricValue"] {
  color: rgba(255,255,255,0.98) !important;
  font-weight: 900 !important;
}
[data-testid="stAppViewContainer"] [data-testid="stMetricDelta"] {
  color: rgba(255,255,255,0.80) !important;
}
/* ===== Sidebar: 라벨은 흰색, 입력/선택값은 검정 ===== */

/* 사이드바 제목/라벨 텍스트만 밝게 */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stMarkdown * {
  color: rgba(255,255,255,0.92) !important;
}

/* 입력창/텍스트박스: 배경 흰색 + 글씨 검정 */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea {
  background: #ffffff !important;
  color: #111111 !important;
}

/* placeholder: 회색 */
[data-testid="stSidebar"] input::placeholder,
[data-testid="stSidebar"] textarea::placeholder {
  color: rgba(0,0,0,0.45) !important;
}

/* selectbox (BaseWeb) : 배경 흰색 + 글씨 검정 */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background: #ffffff !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] * {
  color: #111111 !important;
}

/* 드롭다운 화살표(아이콘) 검정 */
[data-testid="stSidebar"] [data-baseweb="select"] svg {
  fill: #111111 !important;
}
/* ✅ 상단 여백 줄이기 */
.block-container { padding-top: 0.7rem !important; }
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# DB helpers
# -----------------------------
def connect():
    if not DB_PATH.exists():
        st.error(f"DB not found: {DB_PATH}\n먼저 run-yesterday를 돌려서 data/db/dailypaper.sqlite3를 만들어줘.")
        st.stop()
    con = sqlite3.connect(str(DB_PATH))
    # migration: submitted_by, organization
    cur = con.cursor()
    cur.execute("PRAGMA table_info(papers)")
    cols = {r[1] for r in cur.fetchall()}
    if "submitted_by" not in cols:
        cur.execute("ALTER TABLE papers ADD COLUMN submitted_by TEXT DEFAULT ''")
    if "organization" not in cols:
        cur.execute("ALTER TABLE papers ADD COLUMN organization TEXT DEFAULT ''")
    if "published_at" not in cols:
        cur.execute("ALTER TABLE papers ADD COLUMN published_at TEXT DEFAULT ''")
    con.commit()
    return con
@st.cache_data(ttl=60*60*24)
def translate_keywords_to_en(kws: list[str]) -> list[str]:
    # 한글이 없으면 그대로 반환
    joined = " | ".join(kws)
    if not any("가" <= ch <= "힣" for ch in joined):
        return kws

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return kws  # 키 없으면 그냥 원본

    client = OpenAI(api_key=api_key)

    prompt = f"""
Translate the following keyword phrases into natural, concise English keywords.
Rules:
- Output ONLY a JSON array of strings.
- Keep each item short (1~4 words).
- Use lowercase.
- Preserve technical terms (e.g., egocentric, slam, state-space).
Input: {kws}
"""

    try:
        r = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-5.2"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}  # 혹시 안 먹으면 지워도 됨
        )
        txt = r.choices[0].message.content.strip()

        # response_format이 json_object라 dict로 올 수 있어 방어
        import json
        obj = json.loads(txt)
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict):
            # {"keywords":[...]} 형태로 올 수도 있어서 방어
            for v in obj.values():
                if isinstance(v, list):
                    return v
    except Exception:
        pass

    return kws
@st.cache_data(ttl=60)
def get_dates(limit=60):
    with connect() as con:
        df = pd.read_sql_query(
            "SELECT DISTINCT date FROM papers ORDER BY date DESC LIMIT ?",
            con,
            params=(limit,),
        )
    return df["date"].tolist()

@st.cache_data(ttl=60)
def load_rows(date: str):
    q = """
    SELECT
      p.date, p.pid, p.title, p.summary, p.url,
      COALESCE(p.submitted_by,'') as submitted_by,
      COALESCE(p.organization,'') as organization,
      COALESCE(p.published_at,'') as published_at,
      COALESCE(a.labels_json,'[]') as labels_json,
      COALESCE(a.card_json,'{}')   as card_json
    FROM papers p
    LEFT JOIN annotations a
    ON p.date=a.date AND p.pid=a.pid
    WHERE p.date=?
    ORDER BY p.title ASC
    """
    with connect() as con:
        df = pd.read_sql_query(q, con, params=(date,))
    return df

def safe_json(s, default):
    try:
        return json.loads(s) if isinstance(s, str) and s.strip() else default
    except Exception:
        return default

def _is_confident_score(value, threshold: float) -> bool:
    try:
        return float(value) >= float(threshold)
    except Exception:
        return False

INVALID_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1F]')

def sanitize_filename(name: str, fallback: str = "paper") -> str:
    cleaned = INVALID_FILENAME_RE.sub("_", (name or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).rstrip(" .")
    if not cleaned:
        cleaned = INVALID_FILENAME_RE.sub("_", fallback).strip() or "paper"
    return cleaned[:180]

def to_pdf_url(pid: str, url: str) -> str:
    raw = (url or "").strip()
    if not raw and pid:
        return f"https://arxiv.org/pdf/{pid}.pdf"
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw

    if "arxiv.org/abs/" in raw:
        aid = raw.split("arxiv.org/abs/", 1)[1]
        aid = aid.split("?", 1)[0].split("#", 1)[0].strip("/")
        return f"https://arxiv.org/pdf/{aid}.pdf"

    if "arxiv.org/pdf/" in raw:
        base = raw.split("?", 1)[0].split("#", 1)[0]
        return base if base.endswith(".pdf") else f"{base}.pdf"

    return raw

def favorite_pdf_path(card: dict, fallback_date: str) -> Path:
    paper_date = str(card.get("date") or fallback_date)
    pid = str(card.get("pid") or "").strip()
    title = str(card.get("title") or "").strip()
    stem = sanitize_filename(title or pid, fallback=(pid or "paper"))
    return FAVORITES_ROOT / paper_date / f"{stem}.pdf"

def save_favorite_pdf(card: dict, fallback_date: str):
    target = favorite_pdf_path(card, fallback_date)
    if target.exists():
        return

    pid = str(card.get("pid") or "").strip()
    url = str(card.get("url") or "").strip()
    pdf_url = to_pdf_url(pid, url)
    if not pdf_url:
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(pdf_url, headers={"User-Agent": "DailyPaper/1.0"})
    with urllib.request.urlopen(req, timeout=90, context=SSL_CONTEXT) as resp, open(target, "wb") as f:
        shutil.copyfileobj(resp, f)

ZOTERO_FAVORITE_COLLECTION = "DailyPaperFavorite"

def _zotero_fetch_collections(parent_key: str | None = None) -> list:
    """Fetch collections (top-level if parent_key is None, else subcollections)."""
    if not (ZOTERO_API_KEY and ZOTERO_USER_ID):
        return []
    if parent_key:
        path = f"/collections/{parent_key}/collections?limit=100"
    else:
        path = "/collections?limit=100"
    req = urllib.request.Request(
        f"https://api.zotero.org/users/{ZOTERO_USER_ID}{path}",
        headers={
            "Zotero-API-Key": ZOTERO_API_KEY,
            "Zotero-API-Version": "3",
        },
    )
    with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as resp:
        return json.loads(resp.read().decode("utf-8"))

def zotero_collection_key_by_name(name: str, parent_key: str | None = None) -> str:
    collection_name = (name or "").strip()
    if not collection_name:
        return ""
    rows = _zotero_fetch_collections(parent_key)
    for row in rows:
        data = row.get("data", {}) if isinstance(row, dict) else {}
        if str(data.get("name") or "").strip() == collection_name:
            return str(data.get("key") or "").strip()
    return ""

def zotero_get_or_create_collection(name: str, parent_key: str | None, logs: list[str]) -> str:
    """Get existing collection key or create it. parent_key=None means top-level."""
    name = (name or "").strip()
    if not name:
        return ""
    key = zotero_collection_key_by_name(name, parent_key)
    if key:
        logs.append(f"collection:found name={name} key={key}")
        return key
    payload = {"name": name, "parentCollection": parent_key if parent_key else False}
    logs.append(f"collection:create name={name} parent={parent_key or 'root'}")
    res = _zotero_post_json("/collections", [payload], timeout=30)
    key = _zotero_created_key(res)
    if key:
        logs.append(f"collection:created key={key}")
    return key

def _zotero_api_headers(extra: dict | None = None) -> dict:
    headers = {
        "Zotero-API-Key": ZOTERO_API_KEY,
        "Zotero-API-Version": "3",
    }
    if extra:
        headers.update(extra)
    return headers

def _zotero_post_json(path: str, payload, timeout: int = 30):
    req = urllib.request.Request(
        f"https://api.zotero.org/users/{ZOTERO_USER_ID}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers=_zotero_api_headers({"Content-Type": "application/json"}),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            return json.loads(body) if body.strip() else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(detail or f"Zotero HTTP {e.code}") from e

def _zotero_delete_item(item_key: str, timeout: int = 20):
    if not item_key:
        return
    req = urllib.request.Request(
        f"https://api.zotero.org/users/{ZOTERO_USER_ID}/items/{item_key}",
        headers=_zotero_api_headers(),
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as resp:
            _ = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(detail or f"Zotero delete HTTP {e.code}") from e

def _zotero_created_key(write_result: dict) -> str:
    successful = write_result.get("successful", {}) if isinstance(write_result, dict) else {}
    row = successful.get("0")
    if isinstance(row, str):
        return row
    if isinstance(row, dict):
        data = row.get("data", {}) if isinstance(row.get("data"), dict) else {}
        return str(row.get("key") or data.get("key") or "").strip()
    return ""

def _download_pdf_bytes(pdf_url: str) -> bytes:
    req = urllib.request.Request(pdf_url, headers={"User-Agent": "DailyPaper/1.0"})
    with urllib.request.urlopen(req, timeout=90, context=SSL_CONTEXT) as resp:
        return resp.read()

def _zotero_upload_attachment_bytes(attachment_key: str, filename: str, pdf_bytes: bytes, logs: list[str] | None = None):
    logs = logs if logs is not None else []
    if not attachment_key:
        raise RuntimeError("Missing Zotero attachment key")
    if not pdf_bytes:
        raise RuntimeError("Empty PDF bytes")

    md5_hex = hashlib.md5(pdf_bytes).hexdigest()
    verify_path = certifi.where() if certifi else True
    logs.append(f"upload_auth:start attachment={attachment_key} bytes={len(pdf_bytes)}")
    try:
        r = requests.post(
            f"https://api.zotero.org/users/{ZOTERO_USER_ID}/items/{attachment_key}/file",
            headers=_zotero_api_headers({"If-None-Match": "*"}),
            data={
                "md5": md5_hex,
                "filename": filename,
                "filesize": str(len(pdf_bytes)),
                "mtime": str(int(time.time() * 1000)),
            },
            timeout=30,
            verify=verify_path,
        )
        r.raise_for_status()
        auth = r.json() if r.text.strip() else {}
        logs.append(f"upload_auth:ok exists={bool(auth.get('exists'))}")
    except requests.RequestException as e:
        detail = ""
        if getattr(e, "response", None) is not None:
            detail = e.response.text
        raise RuntimeError(detail or f"Zotero upload auth failed: {e}") from e

    if auth.get("exists"):
        logs.append("upload_auth:exists (already uploaded)")
        return

    upload_url = str(auth.get("url") or "").strip()
    upload_key = str(auth.get("uploadKey") or "").strip()
    if not upload_url or not upload_key:
        raise RuntimeError(f"Invalid Zotero upload auth response: {auth}")

    prefix = auth.get("prefix", "")
    suffix = auth.get("suffix", "")
    content_type = str(auth.get("contentType") or "application/octet-stream")
    upload_body = (
        (prefix.encode("utf-8") if isinstance(prefix, str) else bytes(prefix))
        + pdf_bytes
        + (suffix.encode("utf-8") if isinstance(suffix, str) else bytes(suffix))
    )
    logs.append("upload_binary:start")
    try:
        r = requests.post(
            upload_url,
            headers={"Content-Type": content_type},
            data=upload_body,
            timeout=120,
            verify=verify_path,
        )
        r.raise_for_status()
        logs.append(f"upload_binary:ok status={r.status_code}")
    except requests.RequestException as e:
        detail = ""
        if getattr(e, "response", None) is not None:
            detail = e.response.text
        raise RuntimeError(detail or f"Zotero file upload failed: {e}") from e

    logs.append("upload_register:start")
    try:
        r = requests.post(
            f"https://api.zotero.org/users/{ZOTERO_USER_ID}/items/{attachment_key}/file",
            headers=_zotero_api_headers({"If-None-Match": "*"}),
            data={"upload": upload_key},
            timeout=30,
            verify=verify_path,
        )
        r.raise_for_status()
        logs.append(f"upload_register:ok status={r.status_code}")
    except requests.RequestException as e:
        detail = ""
        if getattr(e, "response", None) is not None:
            detail = e.response.text
        raise RuntimeError(detail or f"Zotero file register failed: {e}") from e

def add_to_zotero(card: dict, fallback_date: str):
    if not (ZOTERO_API_KEY and ZOTERO_USER_ID):
        raise RuntimeError("Zotero env is not configured")

    logs: list[str] = []
    parent_key = ""
    attachment_key = ""
    pid = str(card.get("pid") or "").strip()
    title = str(card.get("title") or "").strip() or (pid or "Untitled")
    raw_url = str(card.get("url") or "").strip()
    pdf_url = to_pdf_url(pid, raw_url)
    abs_url = raw_url.strip()
    if not abs_url and pid:
        abs_url = f"https://arxiv.org/abs/{pid}"
    if abs_url and not abs_url.startswith(("http://", "https://")):
        abs_url = "https://" + abs_url
    doi = f"10.48550/arXiv.{pid}" if pid else ""
    analyzed = card.get("card") if isinstance(card.get("card"), dict) else {}
    one_liner = str(analyzed.get("one_liner") or "").strip()
    raw_summary = str(card.get("raw_summary") or "").strip()
    abstract_note = "\n\n".join(s for s in [one_liner, raw_summary] if s)[:20000]
    tags = [{"tag": str(lb)} for lb in (card.get("labels") or []) if str(lb).strip()]

    item = {
        "itemType": "preprint",
        "title": title,
        "abstractNote": abstract_note,
        "repository": "arXiv" if pid else "",
        "archiveID": f"arXiv:{pid}" if pid else "",
        "date": str(card.get("published_at") or card.get("date") or fallback_date or ""),
        "DOI": doi,
        "url": abs_url,
        "accessDate": "CURRENT_TIMESTAMP",
        "libraryCatalog": "arXiv.org" if pid else "",
        "language": "en",
        "extra": f"arXiv: {pid}" if pid else "",
        "tags": tags,
    }

    # 내 라이브러리/DailyPaperFavorite/날짜 구조로 저장
    paper_date = str(card.get("date") or fallback_date or "").strip()
    if paper_date:
        logs.append("collection:DailyPaperFavorite/date structure")
        parent_coll = zotero_get_or_create_collection(ZOTERO_FAVORITE_COLLECTION, None, logs)
        if parent_coll:
            date_coll = zotero_get_or_create_collection(paper_date, parent_coll, logs)
            if date_coll:
                item["collections"] = [date_coll]
                logs.append(f"collection:assigned date_key={date_coll}")

    try:
        logs.append("parent_create:start")
        parent_res = _zotero_post_json("/items", [item], timeout=30)
        parent_key = _zotero_created_key(parent_res)
        if not parent_key:
            raise RuntimeError(f"Failed to create Zotero item: {parent_res}")
        logs.append(f"parent_create:ok key={parent_key}")

        if not pdf_url:
            logs.append("pdf_url:missing (metadata-only item)")
            return {"parent": parent_res, "attachment": None, "logs": logs}

        logs.append(f"pdf_download:start url={pdf_url}")
        pdf_bytes = _download_pdf_bytes(pdf_url)
        logs.append(f"pdf_download:ok bytes={len(pdf_bytes)}")
        filename = sanitize_filename(title or pid, fallback=(pid or "paper")) + ".pdf"
        attachment = {
            "itemType": "attachment",
            "linkMode": "imported_file",
            "title": "PDF",
            "parentItem": parent_key,
            "accessDate": "CURRENT_TIMESTAMP",
            "contentType": "application/pdf",
            "filename": filename,
        }
        logs.append("attachment_create:start")
        attach_res = _zotero_post_json("/items", [attachment], timeout=30)
        attachment_key = _zotero_created_key(attach_res)
        if not attachment_key:
            raise RuntimeError(f"Failed to create Zotero attachment item: {attach_res}")
        logs.append(f"attachment_create:ok key={attachment_key}")

        _zotero_upload_attachment_bytes(attachment_key, filename, pdf_bytes, logs=logs)
        logs.append("zotero_sync:done")
        return {"parent": parent_res, "attachment": attach_res, "logs": logs}
    except Exception as e:
        rollback_errors = []
        if attachment_key:
            try:
                _zotero_delete_item(attachment_key)
                logs.append(f"rollback:deleted attachment={attachment_key}")
            except Exception as de:
                rollback_errors.append(f"attachment={attachment_key}: {de}")
        if parent_key:
            try:
                _zotero_delete_item(parent_key)
                logs.append(f"rollback:deleted parent={parent_key}")
            except Exception as de:
                rollback_errors.append(f"parent={parent_key}: {de}")
        if rollback_errors:
            logs.append("rollback:failed " + " | ".join(rollback_errors))
        raise ZoteroSyncError(str(e), logs=logs) from e

def explode_cards(df: pd.DataFrame):
    cards = []
    for _, r in df.iterrows():
        labels = safe_json(r["labels_json"], [])
        if not isinstance(labels, list) or len(labels) == 0:
            labels = ["Unlabeled"]
        card = safe_json(r["card_json"], {})
        if isinstance(card, dict):
            conf = card.get("label_confidence", {})
            if isinstance(conf, dict) and conf:
                filtered_labels = []
                for lb in labels:
                    try:
                        score = float(conf.get(lb, 0))
                    except Exception:
                        score = 0.0
                    if score >= APP_LABEL_CONFIDENCE_THRESHOLD:
                        filtered_labels.append(lb)
                if filtered_labels:
                    labels = filtered_labels
                else:
                    labels = ["Unlabeled"]
        cards.append(
            {
                "date": r["date"],
                "pid": r["pid"],
                "title": r["title"] or "",
                "url": r["url"] or "",
                "submitted_by": r.get("submitted_by") or "",
                "organization": r.get("organization") or "",
                "published_at": r.get("published_at") or "",
                "labels": labels,
                "card": card if isinstance(card, dict) else {},
                "raw_summary": r["summary"] or "",
            }
        )
    return cards

def label_color(label: str):
    # 색은 CSS에서 직접 안 박고, 뱃지 스타일 통일 (너무 알록달록하면 구려짐)
    return label

# -----------------------------
# Header
# -----------------------------
st.markdown(
    """
<div style="display:flex;align-items:flex-end;gap:14px;margin-bottom:10px;">
  <div style="font-size:2.0rem;">🗞️</div>
  <div>
    <div style="font-size:1.55rem;font-weight:900;line-height:1.1;">Daily Papers</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Sidebar controls
# -----------------------------
with st.sidebar:
    st.markdown("### 설정")
    dates = get_dates()
    if not dates:
        st.warning("저장된 날짜가 없어. 먼저 `run-yesterday`를 돌려줘.")
        st.stop()

    date = st.selectbox("날짜", dates, index=0)
    df = load_rows(date)
    cards = explode_cards(df)

    all_labels = sorted({lb for c in cards for lb in c["labels"]})
    label = st.selectbox("라벨", ["(전체)"] + all_labels, index=0)

    q = st.text_input("검색", placeholder="제목/키워드/요약 내용 검색")
    only_done = st.toggle("분석 완료만 보기", value=True)

# rerun 직후 토스트 표시 (st.rerun 전에 st.toast 호출하면 사라지므로, 세션에 저장 후 다음 로드에서 표시)
if "toast_msg" in st.session_state:
    msg = st.session_state.pop("toast_msg")
    st.toast(msg, duration=3)

# -----------------------------
# Filter
# -----------------------------
def matches(c):
    if only_done and not c["card"]:
        return False
    if label != "(전체)" and label not in c["labels"]:
        return False
    if q:
        qq = q.lower().strip()
        title = c["title"].lower()
        kws = " ".join(c["card"].get("keywords", [])).lower() if c["card"] else ""
        raw = (c["raw_summary"] or "").lower()
        if qq not in title and qq not in kws and qq not in raw:
            return False
    return True

cards_f = [c for c in cards if matches(c)]

# -----------------------------
# Top summary row
# -----------------------------
c1, c2, c3 = st.columns(3)
c1.metric("선택 날짜", date)
c2.metric("필터 후 논문", len(cards_f))
c3.metric("라벨 수", len(all_labels))

st.markdown("")

# -----------------------------
# Group by label for nice layout
# -----------------------------
# "전체"면 라벨별 섹션, 특정 라벨이면 그 라벨만 섹션 하나
if label == "(전체)":
    # 라벨 우선순위: 너가 좋아할만한 순서로 (Robotics/LLM 먼저)
    preferred = ["Robotics", "LLM", "Multimodal", "Vision", "RL", "Systems", "Audio", "Theory", "Other", "Unlabeled"]
    ordered_labels = [lb for lb in preferred if lb in all_labels] + [lb for lb in all_labels if lb not in preferred]
else:
    ordered_labels = [label]

@st.fragment
def render_card(c, render_key: str):
    card = c["card"]
    pid = c["pid"]
    title = c["title"]
    url = (c.get("url") or "").strip()
    if not url and pid:
        url = f"https://arxiv.org/abs/{pid}"
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    labels = c["labels"]

    one = card.get("one_liner", "") if card else ""
    kws = card.get("keywords", []) if card else []
    kws = translate_keywords_to_en(kws) if kws else kws

    labels_txt = " · ".join(labels)
    published_at = (c.get("published_at") or "").strip()
    organization = (c.get("organization") or "").strip()
    segs = [labels_txt]
    if published_at:
        segs.append(published_at)
    if organization:
        segs.append(organization)
    top_line = f'<span class="metaSep"> | </span>'.join(html.escape(s) for s in segs)

    # 원문: DB에 있는 url로 클릭 시 원본 링크 열기 (URL 정규화 + href 이스케이프)
    if url:
        safe_url = html.escape(url, quote=True)
        top_right = f'<a class="badge" href="{safe_url}" target="_blank" rel="noopener noreferrer">원문</a>'
    else:
        top_right = '<span class="badge badge--nolink">원문</span>'

    st.markdown(
        f"""
<div class="card">
  <div class="cardTop">
    <div class="pid">{top_line}</div>
    {top_right}
  </div>
  <div class="title">{title}</div>
  <div class="one">{one if one else '<span class="small">아직 분석 전</span>'}</div>
  <div class="chips">
    {''.join([f'<span class="chip">{k}</span>' for k in kws[:6]])}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    _, heart_col, zotero_col = st.columns([0.90, 0.05, 0.05], vertical_alignment="center")
    with heart_col:
        is_saved = favorite_pdf_path(c, date).exists()
        heart_icon = "❤️" if is_saved else "♡"
        clicked = st.button(
            heart_icon,
            key=f"fav_{render_key}_{pid}",
            type="tertiary",
            width="content",
            help="Save PDF",
        )
    with zotero_col:
        zotero_clicked = st.button(
            "Z",
            key=f"zot_{render_key}_{pid}",
            type="tertiary",
            width="content",
            help="Add to Zotero",
        )
    if clicked:
        try:
            save_favorite_pdf(c, date)
            st.session_state["toast_msg"] = "저장됨"
        except Exception:
            pass
        st.rerun()
    if zotero_clicked:
        try:
            add_to_zotero(c, date)
            st.session_state["toast_msg"] = "Zotero에 저장됨"
            st.rerun()
        except Exception as e:
            st.toast(f"Zotero 실패: {e}", icon="⚠️", duration=3)

    with st.expander("자세히", expanded=False):
        if not card:
            st.info("아직 분석 카드가 없어. `run-yesterday`를 다시 돌리면 채워질 거야.")
            if c["raw_summary"]:
                st.markdown("**원본 summary**")
                st.write(c["raw_summary"])
            return

        st.markdown("##### 구조화 요약")
        colA, colB = st.columns(2)
        with colA:
            st.markdown("**배경**")
            st.write(card.get("problem", ""))
            st.markdown("**기존의 한계**")
            st.write(card.get("what_is_new", ""))
        with colB:
            st.markdown("**방법**")
            st.write(card.get("method", ""))
            st.markdown("**근거 및 성능 주장**")
            st.write(card.get("evidence", ""))
            st.markdown("**한계 및 적용 범위**")
            st.write(card.get("limitations", ""))

        # confidence table (있으면)
        conf = card.get("label_confidence", {})
        if isinstance(conf, dict) and conf:
            conf = {
                k: v for k, v in conf.items()
                if _is_confident_score(v, APP_LABEL_CONFIDENCE_THRESHOLD)
            }
        if isinstance(conf, dict) and conf:
            st.markdown("**라벨 확신도**")
            conf_df = pd.DataFrame({"label": list(conf.keys()), "score": list(conf.values())})
            st.dataframe(conf_df.sort_values("score", ascending=False), width="stretch", hide_index=True)

# -----------------------------
# Render sections
# -----------------------------
for lb in ordered_labels:
    section_cards = [c for c in cards_f if lb in c["labels"]]
    if not section_cards:
        continue

    st.markdown(f"## {lb}  <span class='small'>({len(section_cards)})</span>", unsafe_allow_html=True)

    for idx, c in enumerate(section_cards):
        render_card(c, f"{lb}_{idx}")

st.markdown("<div class='footerHint'>© minju · Daily Papers dashboard</div>", unsafe_allow_html=True)
