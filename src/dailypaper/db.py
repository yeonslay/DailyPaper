import sqlite3
import json
from datetime import datetime
from typing import List, Optional

from .config import PATHS
from .parse import Paper

def _connect():
    PATHS.db.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(PATHS.db))

def init_db():
    with _connect() as con:
        cur = con.cursor()
        cur.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS papers (
              date TEXT NOT NULL,
              pid TEXT NOT NULL,
              title TEXT,
              summary TEXT,
              url TEXT,
              fetched_at TEXT,
              PRIMARY KEY(date, pid)
            );

            CREATE TABLE IF NOT EXISTS annotations (
              date TEXT NOT NULL,
              pid TEXT NOT NULL,
              labels_json TEXT,
              card_json TEXT,
              created_at TEXT,
              PRIMARY KEY(date, pid)
            );
            """
        )
        con.commit()

def upsert_papers(date: str, papers: List[Paper]):
    now = datetime.utcnow().isoformat()
    with _connect() as con:
        cur = con.cursor()
        cur.executemany(
            "INSERT OR REPLACE INTO papers(date,pid,title,summary,url,fetched_at) VALUES(?,?,?,?,?,?)",
            [(date, p.pid, p.title, p.summary, p.url, now) for p in papers],
        )
        con.commit()

def list_unannotated(date: str) -> List[Paper]:
    with _connect() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT p.pid, p.title, p.summary, p.url
            FROM papers p
            LEFT JOIN annotations a
            ON p.date=a.date AND p.pid=a.pid
            WHERE p.date=? AND a.pid IS NULL
            """,
            (date,),
        )
        rows = cur.fetchall()

    return [Paper(pid=r[0], title=r[1] or "", summary=r[2] or "", url=r[3] or "") for r in rows]

def upsert_annotation(date: str, pid: str, labels_json: str, card_json: str):
    now = datetime.utcnow().isoformat()
    with _connect() as con:
        cur = con.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO annotations(date,pid,labels_json,card_json,created_at) VALUES(?,?,?,?,?)",
            (date, pid, labels_json, card_json, now),
        )
        con.commit()

def load_grouped_titles(date: str):
    with _connect() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT p.pid, p.title, COALESCE(a.labels_json, '[]')
            FROM papers p
            LEFT JOIN annotations a
            ON p.date=a.date AND p.pid=a.pid
            WHERE p.date=?
            ORDER BY p.title ASC
            """,
            (date,),
        )
        rows = cur.fetchall()

    buckets = {}
    for pid, title, labels_json in rows:
        try:
            labels = json.loads(labels_json) if labels_json else []
            if not isinstance(labels, list) or not labels:
                labels = ["Unlabeled"]
        except Exception:
            labels = ["Unlabeled"]

        for lb in labels:
            buckets.setdefault(lb, []).append(f"{title}  ({pid})")
    return buckets

def list_dates(limit: int = 30):
    with _connect() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT DISTINCT date FROM papers ORDER BY date DESC LIMIT ?",
            (limit,),
        )
        return [r[0] for r in cur.fetchall()]

def list_cards_by_label(date: str):
    import json as _json
    with _connect() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT p.pid, p.title, p.url, COALESCE(a.labels_json,'[]'), COALESCE(a.card_json,'{}')
            FROM papers p
            LEFT JOIN annotations a
            ON p.date=a.date AND p.pid=a.pid
            WHERE p.date=?
            ORDER BY p.title ASC
            """,
            (date,),
        )
        rows = cur.fetchall()

    buckets = {}
    for pid, title, url, labels_json, card_json in rows:
        try:
            labels = _json.loads(labels_json) if labels_json else []
            if not isinstance(labels, list) or not labels:
                labels = ["Unlabeled"]
        except Exception:
            labels = ["Unlabeled"]

        try:
            card = _json.loads(card_json) if card_json else {}
        except Exception:
            card = {}

        item = {
            "pid": pid,
            "title": title,
            "url": url,
            "card": card,
        }

        for lb in labels:
            buckets.setdefault(lb, []).append(item)
    return buckets
