import html
import json
import os
import re
import shutil
import sqlite3
from pathlib import Path
import urllib.request

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import streamlit as st
from openai import OpenAI
# -----------------------------
# Config / Paths
# -----------------------------
ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "db" / "dailypaper.sqlite3"
FAVORITES_ROOT = ROOT.parent / "DailyPaperFavorite"

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
    with urllib.request.urlopen(req, timeout=90) as resp, open(target, "wb") as f:
        shutil.copyfileobj(resp, f)

def explode_cards(df: pd.DataFrame):
    cards = []
    for _, r in df.iterrows():
        labels = safe_json(r["labels_json"], [])
        if not isinstance(labels, list) or len(labels) == 0:
            labels = ["Unlabeled"]
        card = safe_json(r["card_json"], {})
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

    _, heart_col = st.columns([0.95, 0.05], vertical_alignment="center")
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
    if clicked:
        try:
            save_favorite_pdf(c, date)
        except Exception:
            pass
        st.rerun(scope="fragment")

    # details (Streamlit expander가 UI 더 좋음)
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
