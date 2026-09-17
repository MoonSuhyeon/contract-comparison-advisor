"""
Phase 3 (⑨ baseline): 스키마/Unknown·Conflict·Evidence 규칙 없이, 일반적인 비교 지시문
하나로 자유 텍스트 응답을 받는다. 구조화 파이프라인(llm_extractor.py)과 비교하기 위한
naive baseline. 입력 데이터는 구조화 파이프라인과 동일하게 주되(공정한 비교), 지침만 약하게
한다. 응답은 별도 파서로 구조화하지 않는다 — 그러면 "naive LLM + 파서 성능"이 섞이기 때문
(사용자 결정 사항).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent.parent

NAIVE_INSTRUCTION = (
    "기존 계약과 신규 계약을 비교하여 변경된 보장, 보험료, 갱신 조건, 환급률 등을 정리하고 "
    "고객에게 중요한 차이가 있는지 설명하세요."
)


def load_case(case_id: str) -> dict:
    fname = case_id.lower().replace("-", "") + "_data.json"
    return json.loads((BASE / "data" / fname).read_text(encoding="utf-8"))


def build_user_message(case: dict) -> str:
    payload = {
        "customer": case["customer"],
        "conversation": case["conversation"],
        "existing_contract": case["existing_contract"],
        "new_product": case["new_product"],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n\n" + NAIVE_INSTRUCTION


def _get_client():
    load_dotenv(BASE / ".env")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 없습니다.")
    from openai import OpenAI

    return OpenAI(api_key=api_key)


def run_case(case_id: str) -> dict:
    """토큰 사용량·처리시간을 실측 기록한다. 맨 처음 실행한 7건은 이 계측(및 저장) 로직이
    생기기 전에 실행돼 실측치가 없다 — 06_종합정리.md §4에 이 사실을 그대로 밝혀둔다.
    이 함수 자체는 매 호출마다 실측하지만, __main__에서 파일로 저장해야 재현 가능한
    기록으로 남는다."""
    case = load_case(case_id)
    client = _get_client()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    start = time.monotonic()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": build_user_message(case)}],
    )
    elapsed = time.monotonic() - start
    usage = response.usage
    return {
        "text": response.choices[0].message.content,
        "elapsed_seconds": round(elapsed, 2),
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "total_tokens": usage.total_tokens if usage else None,
    }


if __name__ == "__main__":
    case_id = sys.argv[1] if len(sys.argv) > 1 else "TC-01"
    result = run_case(case_id)
    out_dir = BASE / "results" / "baseline"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{case_id}.txt"
    out_path.write_text(result["text"], encoding="utf-8")

    meta_path = out_dir / f"{case_id}_meta.json"
    meta_path.write_text(
        json.dumps(
            {k: v for k, v in result.items() if k != "text"} | {"case_id": case_id},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    print(f"저장: {out_path} (실측: {result['total_tokens']} tokens, {result['elapsed_seconds']}s)")
    print("-" * 40)
    print(result["text"])
