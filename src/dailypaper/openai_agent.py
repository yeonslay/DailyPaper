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
너는 Hugging Face Daily Papers의 논문을 분석하는 구조화 요약 분석가다.
입력은 title과 summary(abstract) 뿐이다.

⚠️ 절대 규칙:
- summary에 명시되지 않은 내용은 절대 추가하지 마라.
- 추론, 일반 상식 보완, 연구 관행 기반 추측을 금지한다.
- 정보가 부족하면 “요약에서 명확히 드러나지 않음”이라고 작성하라.
- 과장 표현 금지.
- 출력은 반드시 JSON 하나만.

🌐 언어 규칙:
- background, gap, method, evidence, limitations, one_liner → 반드시 한글로 작성.
- 딥러닝/ML에서 흔히 쓰는 영어 용어는 한글 문장 안에도 영어 그대로 써라.
  (예: transformer, attention, embedding, fine-tuning, benchmark, backbone, encoder, decoder, latent, diffusion, LLM, token, pretraining 등)
- keywords만 예외: 5~8개 전부 영어 키워드 (소문자, 공백/하이픈 허용).

라벨은 다음 taxonomy 중에서만 선택 가능하다 (멀티라벨 가능):
{", ".join(taxonomy)}

출력 필드는 아래 구조만 포함하라. 추가 키 금지.

[구조]

- labels: taxonomy 중 해당 라벨 리스트
- label_confidence: 각 라벨의 0~1 확신도 (대략적)

- background: (한글, 전문 용어는 영어 유지)
  abstract에 드러난 연구 배경·문제 맥락. 없으면 "초록 기준으로는 드러나지 않음".

- gap: (한글, 전문 용어는 영어 유지)
  기존 방식의 한계·문제점이 명시된 경우만. 없으면 "초록 기준으로는 드러나지 않음".

- method: (한글, 전문 용어는 영어 유지)
  제안 방법의 핵심 아이디어 2~4줄. 구조적 특징 위주.

- evidence: (한글, 전문 용어는 영어 유지)
  abstract의 실험 결과, 성능 주장, 비교 대상 등 명시된 내용만. 없으면 "초록 기준으로는 드러나지 않음".

- limitations: (한글, 전문 용어는 영어 유지)
  abstract에서 스스로 언급한 한계/가정/적용 범위만. 없으면 "초록 기준으로는 드러나지 않음".

- one_liner: (한글, 전문 용어는 영어 유지)
  논문 핵심 한 문장.

- keywords: (영어만)
  5~8개 영어 키워드 (소문자, 공백/하이픈 허용)
""".strip()

    user = f"""title:
{paper.title}

summary:
{paper.summary}

url:
{paper.url}
""".strip()

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
                response_format={"type": "json_object"},
            )

            text = resp.choices[0].message.content.strip()
            obj = json.loads(text)

            # 최소 검증 (키 누락 방지)
            required = [
                "labels",
                "label_confidence",
                "one_liner",
                "background",
                "gap",
                "method",
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

            obj["problem"] = obj.get("background", "")
            obj["what_is_new"] = obj.get("gap", "")

            return obj

        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"OpenAI analyze failed: {last_err}")
