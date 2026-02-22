import html
import json
import os
import sqlite3
from pathlib import Path

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
    return sqlite3.connect(str(DB_PATH))
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
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
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

def explode_cards(df: pd.DataFrame):
    cards = []
    for _, r in df.iterrows():
        labels = safe_json(r["labels_json"], [])
        if not isinstance(labels, list) or len(labels) == 0:
            labels = ["Unlabeled"]
        card = safe_json(r["card_json"], {})
        cards.append(
            {
                "pid": r["pid"],
                "title": r["title"] or "",
                "url": r["url"] or "",
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
    <div class="small">Hugging Face Daily Papers를 분야별로 분류하고, 카드 형태로 요약해서 보여줌 (어제 확정본 기준)</div>
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

    st.markdown("---")
    st.markdown("### 빠른 통계")
    total = len(cards)
    done = sum(1 for c in cards if c["card"])
    st.metric("총 논문", total)
    st.metric("분석 완료", done)
    st.metric("미분석", total - done)

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

def render_card(c):
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
    <div class="pid">{pid} · {labels_txt}</div>
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
            st.markdown("**문제**")
            st.write(card.get("problem", ""))
            st.markdown("**방법**")
            st.write(card.get("method", ""))
            st.markdown("**새로움**")
            st.write(card.get("what_is_new", ""))
        with colB:
            st.markdown("**근거**")
            st.write(card.get("evidence", ""))
            st.markdown("**한계**")
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

    for c in section_cards:
        render_card(c)

st.markdown("<div class='footerHint'>© minju · Daily Papers dashboard</div>", unsafe_allow_html=True)
