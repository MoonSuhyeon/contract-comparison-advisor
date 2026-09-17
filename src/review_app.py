"""
Streamlit 검토 UI — 05_업무효과검증_설계.md 구현.

Stage 1: TC-01 하나만 대상. AI 비교 초안(결과)을 사람이 확인·수정·추가해서
최종 비교 결과를 만드는 흐름을 구현하고, 소요시간·수정량을 자동으로 기록한다.

Ground Truth는 이 앱에서 절대 읽지 않는다(실험 중 정답 노출 금지, 05번 문서 §6-3).
사후 채점은 별도 스크립트에서 수행한다.

배지 색상은 변화 유형(증가/감소/단축 등)별 고정 색상이며, "좋다/나쁘다"를 뜻하지
않는다. 보험료 감소는 유리하지만 보장금액 감소는 불리한 것처럼 방향의 의미는
항목마다 다르므로, 색으로 유불리를 암시하면 이 프로젝트가 금지하는 "AI가
판단을 대신하는 것"(judgment: null 원칙)이 되어버린다.
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

ITEM_LABELS = {
    "premium": "보험료",
    "renewal_period": "갱신 주기",
    "surrender_value": "해지환급률",
    "surrender_value_at_10y": "10년 해지환급률",
    "coverage_amount_cancer": "암 진단비",
    "coverage_amount_cerebro_cardiac": "뇌혈관질환·급성심근경색 진단비",
    "coverage_items.cancer_diagnosis": "암 진단비",
    "coverage_items.cerebro_cardiac_diagnosis": "뇌혈관질환·급성심근경색 진단비",
}
WON_ITEMS = {
    "premium", "coverage_amount_cancer", "coverage_amount_cerebro_cardiac",
    "coverage_items.cancer_diagnosis", "coverage_items.cerebro_cardiac_diagnosis",
}
# 유형별 고정 색상(유불리 아님). 같은 유형이면 어떤 항목이든 항상 같은 색.
DELTA_BADGES = {
    "decrease": ("감소", "#2563eb"),
    "increase": ("증가", "#ea580c"),
    "shortened": ("단축", "#7c3aed"),
    "extended": ("연장", "#0891b2"),
    "removed": ("삭제", "#334155"),
    "unchanged": ("변경없음", "#6b7280"),
}


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


def label_for_item(item: str) -> str:
    return ITEM_LABELS.get(item, item)


def format_value(item: str, value) -> str:
    if value is None or value == "":
        return "—"
    if item in WON_ITEMS and isinstance(value, (int, float)):
        return f"{int(value):,}원"
    return str(value)


def badge_html(text: str, color: str) -> str:
    return (
        f'<span style="display:inline-block;background:{color}1A;color:{color};'
        f'border:1px solid {color}55;border-radius:999px;padding:3px 12px;'
        f'font-size:12.5px;font-weight:600;white-space:nowrap;">{text}</span>'
    )


def delta_badge_html(delta_type: str) -> str:
    label, color = DELTA_BADGES.get(delta_type, (delta_type or "-", "#475569"))
    return badge_html(label, color)


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


def field_rows_html(data: dict, indent: int = 0) -> str:
    rows = []
    for key, value in data.items():
        pad = 16 * indent
        if isinstance(value, dict):
            rows.append(f'<div style="margin-left:{pad}px;font-weight:700;margin-top:6px;">{key}</div>')
            rows.append(field_rows_html(value, indent + 1))
        else:
            rows.append(f'<div style="margin-left:{pad}px;">• <b>{key}</b>: {value}</div>')
    return "".join(rows)


def render_contract_card(title: str, subtitle: str, color: str, inner_html: str) -> None:
    subtitle_html = f'<div style="color:#64748b;font-size:12.5px;margin-bottom:8px;">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div style="background:{color}0d;border:1px solid {color}55;border-left:4px solid {color};'
        'border-radius:10px;padding:14px 18px;margin-bottom:14px;">'
        f'<div style="font-weight:700;color:{color};margin-bottom:4px;">{title}</div>'
        f'{subtitle_html}'
        f'<div style="color:#0f172a;font-size:14px;line-height:1.8;">{inner_html}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


SPEAKER_STYLE = {
    "agent": ("설계사", "#eff6ff", "#93c5fd", "#1d4ed8"),
    "customer": ("고객", "#f8fafc", "#cbd5e1", "#334155"),
}


def chat_bubble_html(speaker: str, text: str, msg_id: str) -> str:
    label, bg, accent, label_color = SPEAKER_STYLE.get(speaker, (speaker, "#f8fafc", "#cbd5e1", "#334155"))
    return (
        f'<div style="background:{bg};border:1px solid {accent}66;border-left:4px solid {accent};'
        'border-radius:8px;padding:10px 14px;margin-bottom:8px;">'
        f'<div style="font-size:12px;font-weight:700;color:{label_color};margin-bottom:4px;">{label}</div>'
        f'<div style="color:#0f172a;font-size:14.5px;">{text}</div>'
        f'<div style="font-size:11px;color:#94a3b8;margin-top:4px;">{msg_id}</div>'
        '</div>'
    )


def render_review_list(items: list[dict], box, key_prefix: str) -> None:
    for item in items:
        with box(f"**{item['항목']}**" if item["항목"] else "(항목 미지정)"):
            st.write(item.get("설명", ""))
            if item.get("출처"):
                st.caption(f"출처: {item['출처']}")
            cols = st.columns([1, 3])
            item["checked"] = cols[0].checkbox("확인 완료", value=item["checked"], key=f"{key_prefix}-{item['_id']}-chk")
            item["note"] = cols[1].text_input("비고 / 수정", value=item["note"], key=f"{key_prefix}-{item['_id']}-note")


def render_kpi_cards(comparison_count: int, conflict_count: int, unknown_count: int, elapsed: int) -> None:
    def card(label: str, value: str, alert: bool = False) -> str:
        border = "#dc2626" if alert else "#e2e8f0"
        value_color = "#dc2626" if alert else "#0f172a"
        return (
            '<div style="flex:1;background:#fff;border:1px solid {border};border-radius:12px;'
            'padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
            '<div style="font-size:13px;color:#64748b;font-weight:500;margin-bottom:6px;">{label}</div>'
            '<div style="font-size:28px;font-weight:700;color:{value_color};">{value}</div>'
            '</div>'
        ).format(border=border, label=label, value_color=value_color, value=value)

    cards = "".join([
        card("비교 항목", str(comparison_count)),
        card("Conflict", str(conflict_count), alert=conflict_count > 0),
        card("Unknown", str(unknown_count), alert=unknown_count > 0),
        card("경과 시간", f"{elapsed // 60}분 {elapsed % 60}초"),
    ])
    st.markdown(f'<div style="display:flex;gap:14px;margin-bottom:22px;">{cards}</div>', unsafe_allow_html=True)


def render_comparison_summary(rows: list[dict], case_data: dict) -> None:
    for row in rows:
        item = row["항목"]
        old_v = format_value(item, row["기존값"])
        new_v = format_value(item, row["신규값"])
        card_html = (
            '<div style="display:flex;align-items:center;gap:16px;background:#fff;'
            'border:1px solid #e2e8f0;border-radius:10px 10px 0 0;border-bottom:none;'
            'padding:14px 18px;box-shadow:0 1px 2px rgba(0,0,0,0.04);">'
            f'<div style="flex:2;font-weight:600;color:#0f172a;">{label_for_item(item)}</div>'
            f'<div style="flex:3;color:#334155;font-size:14.5px;">{old_v} &rarr; {new_v}</div>'
            f'<div style="flex:2;">{delta_badge_html(row["변화방향"])}</div>'
            f'<div style="flex:1;text-align:right;">{badge_html(row["상태"], "#0f172a")}</div>'
            '</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)
        source_id = row.get("_source_id", "")
        source_location = row.get("_source_location", "")
        with st.expander(f"근거: {row['근거'] or '(없음)'}"):
            if source_location:
                st.write(find_source_text(case_data, source_id, source_location))
            else:
                st.caption("연결된 원문 출처가 없습니다.")
        st.markdown('<div style="margin-bottom:10px;"></div>', unsafe_allow_html=True)


CUSTOM_CSS = """
<style>
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px; }
div[data-testid="stButton"] > button {
    border-radius: 8px;
    font-weight: 600;
}
div[data-testid="stButton"] > button[kind="primary"] {
    padding: 0.65rem 1.2rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
}
div[data-testid="stExpander"] {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    margin-bottom: 14px;
}
div[data-testid="stMetric"] {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px 14px;
}
</style>
"""


def main() -> None:
    st.set_page_config(page_title="계약 비교 검토", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    st.title("계약 비교 결과 검토")
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

    render_kpi_cards(
        len(st.session_state[table_key]),
        len(st.session_state[conflicts_key]),
        len(st.session_state[unknowns_key]),
        elapsed,
    )

    # 확인이 필요한 영역(Conflict/Unknown)은 표보다 먼저, 화면 상단에 배치한다.
    col_conflict, col_unknown = st.columns(2)
    with col_conflict:
        st.markdown("#### Conflict")
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
        st.markdown("#### Unknown")
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

    tab_compare, tab_source = st.tabs(["비교표", "원문 자료"])

    with tab_compare:
        if condition_code == "B" and ai_output:
            st.caption("AI 제안 요약(읽기 전용, 항목별 \"근거\"를 펼치면 원문을 바로 확인합니다) "
                       "— 실제 수정은 아래 \"표 직접 수정\"에서 합니다.")
            render_comparison_summary(ai_output_to_comparison_rows(ai_output), case_data)
            with st.expander("표 직접 수정", expanded=False):
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
        else:
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

    with tab_source:
        with st.expander("고객 정보", expanded=True):
            render_fields(case_data.get("customer", {}))

        with st.expander("상담 내용", expanded=True):
            bubbles = "".join(
                chat_bubble_html(msg["speaker"], msg["text"], msg["message_id"])
                for msg in case_data.get("conversation", {}).get("messages", [])
            )
            st.markdown(bubbles, unsafe_allow_html=True)

        existing = case_data.get("existing_contract", {})
        render_contract_card(
            f"기존 계약 — {existing.get('product_name', '')}",
            existing.get("source_id", ""),
            "#d97706",
            field_rows_html(existing.get("fields", {})),
        )

        new_product = case_data.get("new_product", {})
        new_product_html = "".join(
            f'<div>• <b>{loc}</b>: {doc.get("text", "")}</div>'
            for loc, doc in new_product.get("documents", {}).items()
        )
        render_contract_card(
            f"신규 상품 — {new_product.get('product_name', '')}",
            new_product.get("source_id", ""),
            "#059669",
            new_product_html,
        )

    st.divider()
    if st.button("최종 확정", type="primary", use_container_width=True):
        end_time = time.time()
        duration = round(end_time - st.session_state[start_key], 1)

        original = st.session_state[session_key(case_id, condition_code, "original")]
        original_by_id = {r["_row_id"]: r for r in original.to_dict("records") if r["_row_id"]}
        edited_df = st.session_state[table_key]

        human_edit_count = 0
        human_added_count = 0
        for row in edited_df.to_dict("records"):
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
            "final_table": edited_df.drop(columns=["_source_id", "_source_location"], errors="ignore").to_dict("records"),
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
