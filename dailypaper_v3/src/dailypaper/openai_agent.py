import json
import time
from typing import Dict, Any
from openai import OpenAI

from .config import SETTINGS
from .parse import Paper


def analyze_paper(client: OpenAI, paper: Paper) -> Dict[str, Any]:
    if not SETTINGS.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is missing (.env 확인)")

    taxonomy = list(SETTINGS.taxonomy)

    system = f"""
너는 Hugging Face Daily Papers의 논문을 '분야 분류 + 요약 카드'로 정리하는 분석가다.
입력은 title과 summary 뿐이다. summary에 없는 내용을 절대 지어내지 마라.

라벨은 다음 중에서만 골라라(멀티라벨 가능):
{", ".join(taxonomy)}

출력은 반드시 JSON 하나만. 한국어로, 과장 없이, 그래도 날카롭게.
keywords는 반드시 영어로만 써라. (소문자 권장, 공백/하이픈 허용)
필드는 정확히 아래만 포함해라(추가 키 금지):

- labels: 라벨 리스트 (taxonomy 중에서만)
- label_confidence: 라벨별 0~1 확신도 (대충)
- one_liner: 한 문장 핵심
- problem: 해결하려는 문제
- method: 핵심 아이디어 2~4줄
- what_is_new: 기존 대비 차별점
- evidence: summary에 근거한 주장/결과만
- limitations: 요약에서 드러나는 한계/가정
- keywords: 5~8개 키워드 리스트
""".strip()

    user = f"""title:
{paper.title}

summary:
{paper.summary}

url:
{paper.url}
""".strip()

    # JSON 파싱 실패나 일시적 오류 대비 재시도
    backoffs = [0, 1, 2, 4]
    last_err = None

    for sec in backoffs:
        if sec:
            time.sleep(sec)
        try:
            resp = client.chat.completions.create(
                model=SETTINGS.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0,
                # "JSON만" 나오게 강제 (SDK/서버가 지원하는 경우에만 적용됨)
                response_format={"type": "json_object"},
            )

            text = resp.choices[0].message.content.strip()
            obj = json.loads(text)

            # 최소 검증 (키 누락 방지)
            required = [
                "labels",
                "label_confidence",
                "one_liner",
                "problem",
                "method",
                "what_is_new",
                "evidence",
                "limitations",
                "keywords",
            ]
            for k in required:
                if k not in obj:
                    raise ValueError(f"missing key: {k}")

            # labels taxonomy 필터링 (방어)
            obj["labels"] = [lb for lb in obj.get("labels", []) if lb in taxonomy]
            if not obj["labels"]:
                obj["labels"] = ["Other"]

            return obj

        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"OpenAI analyze failed: {last_err}")
