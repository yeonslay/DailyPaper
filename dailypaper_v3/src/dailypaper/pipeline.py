from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from openai import OpenAI

from .config import PATHS, SETTINGS
from .fetch_hf import fetch_hf_daily
from .parse import parse_hf_raw
from .db import init_db, upsert_papers, list_unannotated, upsert_annotation, load_grouped_titles
from .openai_agent import analyze_paper
import json

def yesterday_kst() -> str:
    kst = ZoneInfo("Asia/Seoul")
    now = datetime.now(tz=kst)
    y = now - timedelta(days=1)
    return y.strftime("%Y-%m-%d")

def run_for_date(date: str):
    init_db()

    raw = fetch_hf_daily(date, save_raw=True)
    papers = parse_hf_raw(raw)
    upsert_papers(date, papers)

    todo = list_unannotated(date)
    print(f"date={date} fetched={len(papers)} to_analyze={len(todo)}")

    client = OpenAI(api_key=SETTINGS.openai_api_key)

    for idx, p in enumerate(todo, 1):
        card = analyze_paper(client, p)

        labels = card.get("labels", [])
        labels_json = json.dumps(labels, ensure_ascii=False)

        card_json = json.dumps(card, ensure_ascii=False)
        upsert_annotation(date, p.pid, labels_json, card_json)

        print(f"[{idx}/{len(todo)}] ok: {p.pid}")

def show_for_date(date: str):
    init_db()
    buckets = load_grouped_titles(date)
    for lb in sorted(buckets.keys()):
        print("")
        print("== " + lb + " ==")
        for line in buckets[lb]:
            print("- " + line)

def run_yesterday():
    run_for_date(yesterday_kst())

def show_yesterday():
    show_for_date(yesterday_kst())
