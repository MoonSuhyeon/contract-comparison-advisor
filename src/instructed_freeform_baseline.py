"""
Phase 10: 세 번째 baseline — naive와 동일하게 자유 텍스트로 답하되,
structured와 동일한 근거/충돌/판단경계 지침(prompt/instructed_freeform_prompt.md)을 준다.
naive와 structured의 차이에 "지침 상세도"와 "출력 구조(스키마) 강제"가 각각 얼마나
기여했는지 분리해서 보기 위한 세 번째 축.

토큰 사용량·처리시간을 실측 기록한다(비용은 측정값과 추정을 나눠서 밝힌다).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent.parent

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def load_instructed_prompt() -> str:
    text = (BASE / "prompt" / "instructed_freeform_prompt.md").read_text(encoding="utf-8")
    m = re.search(r"```\n(.*)\n```", text, re.DOTALL)
    if not m:
        raise RuntimeError("instructed_freeform_prompt.md에서 코드펜스 본문을 찾지 못함")
    return m.group(1)


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
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _get_client():
    load_dotenv(BASE / ".env")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 없습니다.")
    from openai import OpenAI

    return OpenAI(api_key=api_key)


def run_case(case_id: str) -> dict:
    case = load_case(case_id)
    client = _get_client()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    system_prompt = load_instructed_prompt()

    start = time.monotonic()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": build_user_message(case)},
        ],
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

    out_dir = BASE / "results" / "instructed_freeform"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{case_id}.txt").write_text(result["text"], encoding="utf-8")

    meta_path = out_dir / f"{case_id}_meta.json"
    meta_path.write_text(
        json.dumps(
            {k: v for k, v in result.items() if k != "text"} | {"case_id": case_id},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    print(f"저장: {out_dir / f'{case_id}.txt'} (실측: {result['total_tokens']} tokens, {result['elapsed_seconds']}s)")
    print("-" * 40)
    print(result["text"])
