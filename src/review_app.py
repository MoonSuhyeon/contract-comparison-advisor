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
KIND_OPTIONS = ["변경", "변경없음"]
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


def ai_output_to_comparison_rows(ai: dict) -> list[dict]:
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
    return rows


def empty_comparison_rows(n: int = 4) -> list[dict]:
    return [
        {"_row_id": "", "구분": "변경", "항목": "", "기존값": "", "신규값": "",
         "변화방향": "", "근거": "", "상태": "사람 추가", "_source_id": "", "_source_location": ""}
        for _ in range(n)
    ]


def ai_output_to_unknowns(ai: dict) -> list[dict]:
    items = []
    for i, un in enumerate(ai.get("unknowns", [])):
        items.append({
            "_id": f"unknown-{i}", "항목": un.get("item", ""),
            "설명": un.get("reason") or un.get("evidence") or "",
            "출처": f"{un.get('source_id', '')}/{un.get('source_location', '')}",
            "checked": False, "note": "",
        })
    return items


def ai_output_to_conflicts(ai: dict) -> list[dict]:
    items = []
    for i, cf in enumerate(ai.get("conflicts", [])):
        sources = cf.get("sources", [])
        desc = " / ".join(f"[{s.get('source_id', '')}] {s.get('evidence', '')}" for s in sources)
        items.append({
            "_id": f"conflict-{i}", "항목": cf.get("item", cf.get("description", "")),
            "설명": desc, "checked": False, "note": "",
        })
    return items


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


def render_fields(data: dict, indent: int = 0) -> None:
    for key, value in data.items():
        prefix = "  " * indent + "-"
        if isinstance(value, dict):
            st.markdown(f"{prefix} **{key}**")
            render_fields(value, indent + 1)
        else:
            st.markdown(f"{prefix} **{key}**: {value}")


def render_review_list(items: list[dict], box, key_prefix: str) -> None:
    for item in items:
        with box(f"**{item['항목']}**" if item["항목"] else "(항목 미지정)"):
            st.write(item.get("설명", ""))
            if item.get("출처"):
                st.caption(f"출처: {item['출처']}")
            cols = st.columns([1, 3])
            item["checked"] = cols[0].checkbox("확인 완료", value=item["checked"], key=f"{key_prefix}-{item['_id']}-chk")
            item["note"] = cols[1].text_input("비고 / 수정", value=item["note"], key=f"{key_prefix}-{item['_id']}-note")


def main() -> None:
    st.set_page_config(page_title="계약 비교 검토", layout="wide")
    st.title("📋 계약 비교 결과 검토")
    st.caption("AI가 만든 비교 초안을 확인·수정한 뒤 최종 결과를 확정하세요. Ground Truth는 이 화면에 없습니다.")

    with st.sidebar:
        st.header("설정")
        case_id = st.selectbox("케이스", CASES)
        condition = st.radio("조건", ["A · 원문만 보고 직접 작성", "B · AI 초안 검토"])
        condition_code = "A" if condition.startswith("A") else "B"
        if condition_code == "A":
            st.info("AI 결과 없이 원문만 보고 비교표를 처음부터 작성합니다.")
        else:
            st.info("AI가 만든 초안을 확인·수정해서 최종 결과를 만듭니다.")

    case_data = load_case_data(case_id)
    ai_output = load_ai_output(case_id) if condition_code == "B" else None

    start_key = session_key(case_id, condition_code, "start_time")
    if start_key not in st.session_state:
        st.session_state[start_key] = time.time()
    elapsed = int(time.time() - st.session_state[start_key])

    table_key = session_key(case_id, condition_code, "table")
    unknowns_key = session_key(case_id, condition_code, "unknowns")
    conflicts_key = session_key(case_id, condition_code, "conflicts")

    if table_key not in st.session_state:
        rows = ai_output_to_comparison_rows(ai_output) if (condition_code == "B" and ai_output) else empty_comparison_rows()
        st.session_state[table_key] = pd.DataFrame(rows, columns=TABLE_COLUMNS + ["_source_id", "_source_location"])
        st.session_state[session_key(case_id, condition_code, "original")] = st.session_state[table_key].copy()
        st.session_state[unknowns_key] = ai_output_to_unknowns(ai_output) if (condition_code == "B" and ai_output) else []
        st.session_state[conflicts_key] = ai_output_to_conflicts(ai_output) if (condition_code == "B" and ai_output) else []

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("비교 항목", len(st.session_state[table_key]))
    m2.metric("⚠️ Conflict", len(st.session_state[conflicts_key]))
    m3.metric("❓ Unknown", len(st.session_state[unknowns_key]))
    m4.metric("⏱ 경과 시간", f"{elapsed // 60}분 {elapsed % 60}초")

    with st.expander("📄 원문 자료 (상담 · 기존 계약 · 신규 상품)", expanded=(condition_code == "A")):
        st.markdown("**고객 정보**")
        render_fields(case_data.get("customer", {}))

        st.markdown("**상담 내용**")
        for msg in case_data.get("conversation", {}).get("messages", []):
            st.markdown(f"- `[{msg['message_id']}]` **{msg['speaker']}**: {msg['text']}")

        existing = case_data.get("existing_contract", {})
        st.markdown(f"**기존 계약** — {existing.get('product_name', '')} (`{existing.get('source_id', '')}`)")
        render_fields(existing.get("fields", {}))

        new_product = case_data.get("new_product", {})
        st.markdown(f"**신규 상품** — {new_product.get('product_name', '')} (`{new_product.get('source_id', '')}`)")
        for loc, doc in new_product.get("documents", {}).items():
            st.markdown(f"- `{loc}`: {doc.get('text', '')}")

    st.subheader("비교표")
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
        with st.expander("🔍 근거 원문 보기"):
            seen = set()
            for row in ai_output_to_comparison_rows(ai_output):
                loc = (row["_source_id"], row["_source_location"])
                if loc in seen or not row["_source_location"]:
                    continue
                seen.add(loc)
                st.write(f"**[{row['_source_id']}/{row['_source_location']}]** "
                         f"{find_source_text(case_data, *loc)}")

    col_conflict, col_unknown = st.columns(2)
    with col_conflict:
        st.markdown("### ⚠️ Conflict")
        if st.session_state[conflicts_key]:
            render_review_list(st.session_state[conflicts_key], st.error, "conflict")
        else:
            st.caption("표시된 Conflict가 없습니다.")
        if st.button("+ Conflict 추가", key=f"add_conflict_{case_id}_{condition_code}"):
            st.session_state[conflicts_key].append(
                {"_id": f"conflict-manual-{uuid.uuid4().hex[:6]}", "항목": "", "설명": "", "checked": False, "note": ""}
            )
            st.rerun()

    with col_unknown:
        st.markdown("### ❓ Unknown")
        if st.session_state[unknowns_key]:
            render_review_list(st.session_state[unknowns_key], st.warning, "unknown")
        else:
            st.caption("표시된 Unknown이 없습니다.")
        if st.button("+ Unknown 추가", key=f"add_unknown_{case_id}_{condition_code}"):
            st.session_state[unknowns_key].append(
                {"_id": f"unknown-manual-{uuid.uuid4().hex[:6]}", "항목": "", "설명": "", "출처": "", "checked": False, "note": ""}
            )
            st.rerun()

    st.divider()
    if st.button("✅ 최종 확정", type="primary", use_container_width=True):
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
        conflict_review_count = sum(1 for c in st.session_state[conflicts_key] if c["checked"])
        unknown_review_count = sum(1 for u in st.session_state[unknowns_key] if u["checked"])

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
            "final_conflicts": st.session_state[conflicts_key],
            "final_unknowns": st.session_state[unknowns_key],
        }

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        out_path = LOG_DIR / f"{case_id}_{condition_code}_{log['run_id']}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)

        st.success(f"저장 완료 — {out_path.relative_to(ROOT)}")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("소요 시간", f"{duration}초")
        r2.metric("수정한 항목", human_edit_count)
        r3.metric("새로 추가한 항목", human_added_count)
        r4.metric("Conflict/Unknown 확인", conflict_review_count + unknown_review_count)


if __name__ == "__main__":
    main()
