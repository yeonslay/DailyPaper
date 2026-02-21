from typing import List
from pydantic import BaseModel
import json

class Paper(BaseModel):
    pid: str
    title: str
    summary: str = ""
    url: str = ""

def parse_hf_raw(raw_json_text: str) -> List[Paper]:
    j = json.loads(raw_json_text)
    if not isinstance(j, list):
        raise ValueError("HF response is not a list")

    out: List[Paper] = []
    for item in j:
        if isinstance(item, dict) and "paper" in item and isinstance(item["paper"], dict):
            pp = item["paper"]
        else:
            pp = item if isinstance(item, dict) else {}

        pid = str(pp.get("id", "")).strip()
        title = str(pp.get("title", "")).strip()
        summary = str(pp.get("summary", "")).strip()
        url = str(pp.get("url", "")).strip()

        if not title:
            continue
        if not pid:
            pid = title  
        if not url and pid:
            url = f"https://arxiv.org/abs/{pid}"

        out.append(Paper(pid=pid, title=title, summary=summary, url=url))

    return out
