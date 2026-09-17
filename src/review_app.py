"""
Streamlit 검토 UI — 05_업무효과검증_설계.md 구현.

Stage 1: TC-01 하나만 대상. AI 비교 초안(결과)을 사람이 확인·수정·추가해서
최종 비교 결과를 만드는 흐름을 구현하고, 소요시간·수정량을 자동으로 기록한다.

Ground Truth는 이 앱에서 절대 읽지 않는다(실험 중 정답 노출 금지, 05번 문서 §6-3).
사후 채점은 별도 스크립트에서 수행한다.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STRUCTURED_DIR = ROOT / "results" / "structured"
LOG_DIR = ROOT / "results" / "work_effect" / "app_logs"

CASES = ["TC-01"]  # Stage 3에서 TC-03/04/05/10/11/15 추가

TABLE_COLUMNS = ["_row_id", "구분", "항목", "기존값", "신규값", "변화방향", "근거", "상태"]
KIND_OPTIONS = ["변경", "변경없음", "Unknown", "Conflict"]
STATUS_OPTIONS = ["AI 제안", "확인", "수정", "사람 추가"]


def load_case_data(case_id: str) -> dict:
    path = DATA_DIR / f"{case_id.lower().replace('-', '')}_data.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.pop("ground_truth", None)
    return data


def load_ai_output(case_id: str) -> dict | None:
    path = STRUCTURED_DIR / f"{case_id}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ai_output_to_rows(ai: dict) -> list[dict]:
    rows = []
    for i, c in enumerate(ai.get("changes", [])):
        rows.append({
            "_row_id": f"change-{i}", "구분": "변경", "항목": c.get("item", ""),
            "기존값": c.get("old"), "신규값": c.get("new"),
            "변화방향": c.get("delta_type", ""), "근거": c.get("evidence") or "",
            "상태": "AI 제안",
            "_source_id": c.get("source_id", ""), "_source_location": c.get("source_location", ""),
        })
    for i, u in enumerate(ai.get("unchanged_items", [])):
        rows.append({
            "_row_id": f"unchanged-{i}", "구분": "변경없음", "항목": u.get("item", ""),
            "기존값": u.get("old"), "신규값": u.get("new"),
            "변화방향": u.get("delta_type", "unchanged"), "근거": u.get("evidence") or "",
            "상태": "AI 제안",
            "_source_id": u.get("source_id", ""), "_source_location": u.get("source_location", ""),
        })
    for i, un in enumerate(ai.get("unknowns", [])):
        rows.append({
            "_row_id": f"unknown-{i}", "구분": "Unknown", "항목": un.get("item", ""),
            "기존값": un.get("old"), "신규값": un.get("new"),
            "변화방향": un.get("status", "unknown"), "근거": un.get("reason") or un.get("evidence") or "",
            "상태": "AI 제안",
            "_source_id": un.get("source_id", ""), "_source_location": un.get("source_location", ""),
        })
    for i, cf in enumerate(ai.get("conflicts", [])):
        sources = cf.get("sources", [])
        evidence = " / ".join(
            f"[{s.get('source_id', '')}] {s.get('evidence', '')}" for s in sources
        )
        values = [s.get("evidence", "") for s in sources]
        rows.append({
            "_row_id": f"conflict-{i}", "구분": "Conflict", "항목": cf.get("item", cf.get("description", "")),
            "기존값": values[0] if len(values) > 0 else "", "신규값": values[1] if len(values) > 1 else "",
            "변화방향": cf.get("type", "conflict"), "근거": evidence,
            "상태": "AI 제안",
            "_source_id": "", "_source_location": "",
        })
    return rows


def empty_rows(n: int = 4) -> list[dict]:
    return [
        {"_row_id": "", "구분": "변경", "항목": "", "기존값": "", "신규값": "",
         "변화방향": "", "근거": "", "상태": "사람 추가", "_source_id": "", "_source_location": ""}
        for _ in range(n)
    ]


def find_source_text(case_data: dict, source_id: str, source_location: str) -> str:
    new_product = case_data.get("new_product", {})
    if source_id == new_product.get("source_id"):
        doc = new_product.get("documents", {}).get(source_location)
        if doc:
            return doc.get("text", "")
    for msg in case_data.get("conversation", {}).get("messages", []):
        if msg.get("message_id") == source_location:
            return f"[{msg.get('speaker')}] {msg.get('text')}"
    existing = case_data.get("existing_contract", {})
    if source_id == existing.get("source_id"):
        return f"(계약 필드 원본값) {existing.get('fields', {})}"
    return "원문을 찾을 수 없습니다."


def session_key(case_id: str, condition: str, name: str) -> str:
    return f"{case_id}_{condition}_{name}"


def main() -> None:
    st.set_page_config(page_title="계약 비교 검토", layout="wide")
    st.title("계약 비교 결과 검토")

    case_id = st.sidebar.selectbox("케이스", CASES)
    condition = st.sidebar.radio("조건", ["A (원문만)", "B (AI 결과 검토)"])
    condition_code = "A" if condition.startswith("A") else "B"

    case_data = load_case_data(case_id)
    ai_output = load_ai_output(case_id) if condition_code == "B" else None

    start_key = session_key(case_id, condition_code, "start_time")
    if start_key not in st.session_state:
        st.session_state[start_key] = time.time()

    with st.expander("원문 자료 (상담 · 기존 계약 · 신규 상품)", expanded=(condition_code == "A")):
        st.write("**고객 정보**", case_data.get("customer", {}))
        st.write("**상담 내용**")
        for msg in case_data.get("conversation", {}).get("messages", []):
            st.write(f"- [{msg['message_id']}] {msg['speaker']}: {msg['text']}")
        st.write("**기존 계약**", case_data.get("existing_contract", {}))
        st.write("**신규 상품**", case_data.get("new_product", {}))

    table_key = session_key(case_id, condition_code, "table")
    if table_key not in st.session_state:
        if condition_code == "B" and ai_output:
            rows = ai_output_to_rows(ai_output)
        else:
            rows = empty_rows()
        st.session_state[table_key] = pd.DataFrame(rows, columns=TABLE_COLUMNS + ["_source_id", "_source_location"])
        st.session_state[session_key(case_id, condition_code, "original")] = st.session_state[table_key].copy()

    st.subheader("비교 결과")
    edited = st.data_editor(
        st.session_state[table_key],
        num_rows="dynamic",
        column_order=["구분", "항목", "기존값", "신규값", "변화방향", "근거", "상태"],
        column_config={
            "구분": st.column_config.SelectboxColumn(options=KIND_OPTIONS),
            "상태": st.column_config.SelectboxColumn(options=STATUS_OPTIONS),
        },
        key=f"editor_widget_{case_id}_{condition_code}",
        use_container_width=True,
    )
    st.session_state[table_key] = edited

    if condition_code == "B" and ai_output:
        with st.expander("근거 원문 보기"):
            seen = set()
            for row in ai_output_to_rows(ai_output):
                loc = (row["_source_id"], row["_source_location"])
                if loc in seen or not row["_source_location"]:
                    continue
                seen.add(loc)
                st.write(f"**[{row['_source_id']}/{row['_source_location']}]** "
                         f"{find_source_text(case_data, *loc)}")

    st.divider()
    if st.button("최종 확정", type="primary"):
        end_time = time.time()
        duration = round(end_time - st.session_state[start_key], 1)

        original = st.session_state[session_key(case_id, condition_code, "original")]
        original_by_id = {r["_row_id"]: r for r in original.to_dict("records") if r["_row_id"]}

        human_edit_count = 0
        human_added_count = 0
        for row in edited.to_dict("records"):
            rid = row.get("_row_id") or ""
            if not rid:
                if any(str(row.get(c, "")).strip() for c in ("항목", "기존값", "신규값", "근거")):
                    human_added_count += 1
                continue
            orig = original_by_id.get(rid)
            if orig and any(
                str(row.get(c, "")) != str(orig.get(c, "")) for c in ("기존값", "신규값", "변화방향", "근거", "구분")
            ):
                human_edit_count += 1

        ai_suggestion_count = len(original_by_id)
        conflict_review_count = sum(
            1 for row in edited.to_dict("records") if row.get("구분") == "Conflict" and row.get("상태") != "AI 제안"
        )
        unknown_review_count = sum(
            1 for row in edited.to_dict("records") if row.get("구분") == "Unknown" and row.get("상태") != "AI 제안"
        )

        log = {
            "run_id": str(uuid.uuid4())[:8],
            "case_id": case_id,
            "condition": condition_code,
            "start_time": st.session_state[start_key],
            "end_time": end_time,
            "duration_sec": duration,
            "ai_suggestion_count": ai_suggestion_count,
            "human_edit_count": human_edit_count,
            "human_added_count": human_added_count,
            "conflict_review_count": conflict_review_count,
            "unknown_review_count": unknown_review_count,
            "final_table": edited.drop(columns=["_source_id", "_source_location"], errors="ignore").to_dict("records"),
        }

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        out_path = LOG_DIR / f"{case_id}_{condition_code}_{log['run_id']}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)

        st.success(f"저장 완료 ({duration}초 소요) → {out_path.relative_to(ROOT)}")
        st.json(log)


if __name__ == "__main__":
    main()
