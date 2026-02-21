from typing import List
from pydantic import BaseModel
import json

class Paper(BaseModel):
    pid: str
    title: str
    summary: str = ""
    url: str = ""

def parse_hf_raw(raw_json_text: str) -> List[Paper]:
    """
    HF daily papers 응답(raw)을 Paper 리스트로 표준화.
    """
    j = json.loads(raw_json_text)
    if not isinstance(j, list):
        raise ValueError("HF response is not a list")

    out: List[Paper] = []
    for item in j:
        # 보통 item["paper"] 아래에 들어있음(케이스 대응)
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
            pid = title  # fallback (최악의 경우)
        if not url and pid:
            url = f"https://arxiv.org/abs/{pid}"

        out.append(Paper(pid=pid, title=title, summary=summary, url=url))

    return out
