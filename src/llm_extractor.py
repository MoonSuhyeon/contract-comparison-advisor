"""
Phase 1 (⑦ AI 기능 구현): system_prompt.md + output_schema.json으로 실제 LLM을 호출해
tc0X_data.json 하나를 구조화된 JSON으로 변환한다.

먼저 TC-01 단건으로 end-to-end가 도는지 확인하는 용도. (PLAN.md Phase 1)
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import jsonschema
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent.parent


def load_system_prompt() -> str:
    """prompt/system_prompt.md의 ``` 코드펜스 안 본문만 추출한다."""
    text = (BASE / "prompt" / "system_prompt.md").read_text(encoding="utf-8")
    m = re.search(r"```\n(.*)\n```", text, re.DOTALL)
    if not m:
        raise RuntimeError("system_prompt.md에서 코드펜스로 감싼 프롬프트 본문을 찾지 못함")
    return m.group(1)


def load_output_schema() -> dict:
    return json.loads((BASE / "schema" / "output_schema.json").read_text(encoding="utf-8"))


def load_case(case_id: str) -> dict:
    path = BASE / "data" / f"{case_id.lower().replace('-', '')}_data.json"
    if not path.exists():
        # tc01_data.json 형식(하이픈 없이)과 tc-01 두 표기 다 허용
        path = BASE / "data" / f"{case_id.lower()}_data.json"
    return json.loads(path.read_text(encoding="utf-8"))


def build_user_message(case: dict) -> str:
    """system_prompt의 '1. 입력 데이터 구조'에 맞춰 case에서 4개 필드만 추려 전달한다.
    ground_truth/expected_ai_behavior/notes_for_evaluator 등은 정답이므로 절대 포함하지 않는다."""
    payload = {
        "customer": case["customer"],
        "conversation": case["conversation"],
        "existing_contract": case["existing_contract"],
        "new_product": case["new_product"],
    }
    return (
        "아래 입력 데이터를 분석해서 submit_contract_comparison 함수로 결과를 제출하세요.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def _get_client():
    load_dotenv(BASE / ".env")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY가 없습니다. .env.example을 .env로 복사하고 키를 채워주세요. "
            "(키 없이 mock으로 대체하지 않고 여기서 즉시 중단합니다)"
        )
    from openai import OpenAI

    return OpenAI(api_key=api_key)


def run_case(case_id: str, max_retries: int = 2) -> dict:
    system_prompt = load_system_prompt()
    schema_doc = load_output_schema()
    case = load_case(case_id)
    user_message = build_user_message(case)

    tool = {
        "type": "function",
        "function": {
            "name": schema_doc["name"],
            "description": schema_doc["description"],
            "parameters": schema_doc["input_schema"],
        },
    }
    validator = jsonschema.Draft202012Validator(schema_doc["input_schema"])

    client = _get_client()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    last_errors = None
    last_output = None
    for attempt in range(1, max_retries + 2):  # 최초 1회 + 재시도 max_retries회
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[tool],
            tool_choice={"type": "function", "function": {"name": schema_doc["name"]}},
        )
        message = response.choices[0].message
        if not message.tool_calls:
            raise RuntimeError(f"{case_id}: 모델이 함수 호출을 반환하지 않음 (attempt {attempt}) — {message.content}")

        call = message.tool_calls[0]
        try:
            output = json.loads(call.function.arguments)
        except json.JSONDecodeError as e:
            last_errors = [f"JSON 파싱 실패: {e}"]
            print(f"  [attempt {attempt}] JSON 파싱 실패, 재시도")
            messages.append({"role": "assistant", "content": None, "tool_calls": [call]})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": f"JSON 파싱에 실패했습니다: {e}. 유효한 JSON으로 다시 제출하세요.",
                }
            )
            continue

        last_output = output
        errors = list(validator.iter_errors(output))
        if not errors:
            output["_usage"] = {
                "model": model,
                "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                "completion_tokens": response.usage.completion_tokens if response.usage else None,
                "attempts": attempt,
            }
            output["_case_id"] = case_id
            return output

        last_errors = [f"{list(e.path)}: {e.message}" for e in errors]
        print(f"  [attempt {attempt}] 스키마 검증 실패 {len(errors)}건, 재시도")
        messages.append({"role": "assistant", "content": None, "tool_calls": [call]})
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.id,
                "content": "스키마 검증 실패:\n" + "\n".join(last_errors) + "\n다시 규칙에 맞게 제출하세요.",
            }
        )

    # 관찰 목적: 계속 실패해도 그냥 죽이지 않고, 마지막(무효) 출력을 표시해서 저장한다.
    # 이 프로젝트의 목적이 AI 오류를 발견·기록하는 것이므로, "왜 계속 실패했는지"를 볼 수 있는
    # 것이 크래시로 아무것도 안 남기는 것보다 낫다.
    print(f"  경고: {max_retries + 1}회 시도 후에도 스키마 검증 실패. 마지막 무효 출력을 그대로 저장합니다.")
    output = last_output or {}
    output["_schema_valid"] = False
    output["_validation_errors"] = last_errors
    output["_usage"] = {"model": model, "attempts": max_retries + 1}
    output["_case_id"] = case_id
    return output


if __name__ == "__main__":
    case_id = sys.argv[1] if len(sys.argv) > 1 else "TC-01"
    print(f"실행 중: {case_id}")
    result = run_case(case_id)

    out_dir = BASE / "results" / "structured"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{case_id}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    usage = result.get("_usage", {})
    print(f"성공 (시도 {usage.get('attempts')}회) -> {out_path}")
    print(f"토큰: prompt={usage.get('prompt_tokens')}, completion={usage.get('completion_tokens')}")
    print(f"changes={len(result.get('changes', []))}, unchanged={len(result.get('unchanged_items', []))}, "
          f"unknowns={len(result.get('unknowns', []))}, conflicts={len(result.get('conflicts', []))}, "
          f"additional_conditions={len(result.get('additional_conditions', []))}, "
          f"customer_needs={len(result.get('customer_needs', []))}")
