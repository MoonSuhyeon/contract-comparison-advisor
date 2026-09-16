"""
Phase 2 (⑧ 자동 평가기): schema/validation_rules.md의 규칙을 구현한다.
GT(data/tc0X_data.json의 ground_truth)와 AI Output(results/structured/TC-XX.json)을 대조.

매칭 키(§0, C6_설계_확정본.md §3-4): source_id + source_location.
item 문자열은 표시명일 뿐 매칭에 쓰지 않는다 — TC-01 실행에서 실제로 필요성이 확인된 규칙.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

BASE = Path(__file__).resolve().parent.parent

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

THRESHOLDS = {
    "premium": 1000,          # 원 미만
    "percent": 1.0,           # % 미만 (보장금액)
    "percentage_point": 1.0,  # %p 미만 (비율/기간류)
}

JUDGMENT_KEYWORDS = ["유리", "불리", "좋음", "나쁨", "추천", "비추천", "적합", "부적합",
                     "더 낫다", "더 좋다", "가입해야 한다", "변경하는 것이 좋다"]


@dataclass
class Finding:
    rule: str
    severity: str  # AUTO-FAIL | HUMAN-QUEUE
    axis: str
    message: str
    item_ref: str = ""


@dataclass
class Report:
    findings: list = field(default_factory=list)
    recall_hits: int = 0
    recall_total: int = 0
    precision_violations: int = 0
    precision_total: int = 0
    evidence_ungrounded: int = 0
    evidence_total: int = 0

    def add(self, f: Finding):
        self.findings.append(f)


# ---------------------------------------------------------------- 로딩

def load_case(case_id: str) -> dict:
    fname = case_id.lower().replace("-", "") + "_data.json"
    return json.loads((BASE / "data" / fname).read_text(encoding="utf-8"))


def load_ai_output(case_id: str, ai_output_path: Optional[str] = None) -> dict:
    """ai_output_path를 주면 그 파일을 그대로 읽는다(임시로 results/structured/에 바꿔치기하지
    않아도 원본/교정본 등 임의 파일을 재현 가능하게 평가하기 위함)."""
    path = Path(ai_output_path) if ai_output_path else BASE / "results" / "structured" / f"{case_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- §0 매칭 키

def match_key(entry: dict) -> tuple:
    return (entry.get("source_id"), entry.get("source_location"))


def index_by_key(entries: list) -> dict:
    idx: dict = {}
    for e in entries:
        idx.setdefault(match_key(e), []).append(e)
    return idx


def find_match(ai_entry: dict, gt_index: dict) -> Optional[dict]:
    """M1: source_id+source_location 매칭. 후보가 여럿이면 old/new로 교차검증(여전히 M1)."""
    candidates = gt_index.get(match_key(ai_entry), [])
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        for c in candidates:
            if c.get("old") == ai_entry.get("old") and c.get("new") == ai_entry.get("new"):
                return c
        return None  # 애매함 — 자동으로 확정하지 않음
    return None


def find_match_tiered(ai_entry: dict, gt_index: dict, gt: dict, gt_bucket: str) -> tuple[Optional[dict], str]:
    """M1/M2 매칭 (validation_rules.md §0). 반환: (매칭된 GT 항목 또는 None, 'M1'|'M2'|'none').

    M2는 TC-03에서 발견된 문제(AI가 내용은 맞혔는데 source_id를 잘못 표기해 M1이 실패하는 경우)를
    위한 보정 채널이다. 값이 우연히 같을 위험이 있으므로 M2 매칭은 절대 점수에 자동 반영하지
    않고 호출부에서 HUMAN-QUEUE로만 처리한다.
    """
    m1 = find_match(ai_entry, gt_index)
    if m1 is not None:
        return m1, "M1"

    pool = gt.get(gt_bucket, [])
    value_matches = [
        c for c in pool
        if c.get("old") == ai_entry.get("old") and c.get("new") == ai_entry.get("new")
    ]
    if len(value_matches) == 1:
        return value_matches[0], "M2"
    return None, "none"


def build_gt_index(gt: dict) -> tuple[dict, dict]:
    """반환: (매칭키 -> GT항목, 매칭키 -> 어느 배열 출신인지("changes"/"unchanged_items"/"unknown"/"additional_condition"))"""
    by_key: dict = {}
    origin: dict = {}
    for bucket, name in [
        ("changes", "changes"),
        ("unchanged_items", "unchanged_items"),
        ("unknown_or_confirmed_absent_items", "unknown"),
        ("additional_conditions", "additional_condition"),
    ]:
        for e in gt.get(bucket, []):
            key = match_key(e)
            by_key.setdefault(key, []).append(e)
            origin[id(e)] = name
    return by_key, origin


# ---------------------------------------------------------------- B1 원문 대조

def normalize(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def normalize_item(s: str) -> str:
    """D4용: item 이름 느슨한 비교. 구분자를 없애고 소문자화(한글엔 영향 없음)."""
    return re.sub(r"[._\-\s]", "", (s or "").lower())


def build_source_texts(case: dict) -> dict:
    texts: dict = {}
    ec = case["existing_contract"]
    texts[ec["source_id"]] = json.dumps(ec, ensure_ascii=False)
    np_ = case["new_product"]
    texts[np_["source_id"]] = " ".join(d.get("text", "") for d in np_["documents"].values())
    conv = case["conversation"]
    texts[conv["conversation_id"]] = " ".join(m["text"] for m in conv["messages"])
    for m in conv["messages"]:
        texts[m["message_id"]] = m["text"]
    return texts


def ground_status(evidence: Optional[str], claimed_source_id: Optional[str], texts: dict) -> str:
    """'grounded' | 'wrong_source' | 'not_found'.

    TC-03 실행에서 발견: evidence 텍스트 자체는 실존하는데 source_id를 잘못 표기한 경우가
    있었다(발화를 인용하면서 source_id를 contract_A라고 잘못 씀). 이건 '완전히 지어낸 것'과는
    다른 오류이므로 구분한다 — grounded/not_found만 있으면 전자를 후자와 같은 강도(AUTO-FAIL
    환각)로 처리하게 되어 오류 유형 진단이 부정확해진다.
    """
    if not evidence:
        return "not_found"
    needle = normalize(evidence)
    if needle in normalize(texts.get(claimed_source_id, "")):
        return "grounded"
    for sid, blob in texts.items():
        if sid == claimed_source_id:
            continue
        if needle in normalize(blob):
            return "wrong_source"
    return "not_found"


NUMBER_WITH_UNIT = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(만원|원|%)?")


def extract_grounded_numbers(text: Optional[str]) -> set[str]:
    """evidence 문장에서 수치를 뽑아 정규화한 집합을 만든다. '만원'은 10000을 곱해 원 단위로
    환산한다(2,000만원 -> 20000000) — 안 하면 GT의 raw 정수값(20000000)과 절대 안 맞아서
    맞는 항목까지 B5로 오탐하게 된다."""
    if not text:
        return set()
    out = set()
    for digits, unit in NUMBER_WITH_UNIT.findall(text):
        if not digits:
            continue
        num = float(digits.replace(",", ""))
        if unit == "만원":
            num *= 10000
        out.add(str(int(num)) if num == int(num) else str(num))
    return out


def value_to_number_str(value) -> Optional[str]:
    """change의 old/new 값을 evidence 수치 집합과 비교 가능한 정규화 문자열로 바꾼다."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return str(int(value)) if value == int(value) else str(value)
    if isinstance(value, str):
        m = re.match(r"\s*(\d[\d,]*(?:\.\d+)?)", value)
        if m:
            num = float(m.group(1).replace(",", ""))
            return str(int(num)) if num == int(num) else str(num)
    return None


def value_evidence_mismatch(entry: dict, evidence: str) -> bool:
    """B5: evidence 문장에 수치가 하나라도 있는데, 선언한 old/new 중 어느 쪽도 그 문장이 말하는
    수치와 일치하지 않으면 위반. evidence에 수치가 아예 없으면(서술형 evidence) 검사 대상이
    아니다 — 이 규칙은 '값 위조'만 잡지, 서술형 evidence의 진위는 B1이 이미 담당한다."""
    grounded_numbers = extract_grounded_numbers(evidence)
    if not grounded_numbers:
        return False
    candidates = {value_to_number_str(entry.get("old")), value_to_number_str(entry.get("new"))}
    candidates.discard(None)
    if not candidates:
        return False
    return grounded_numbers.isdisjoint(candidates)


def within_threshold(old, new, item_hint: str) -> bool:
    """B3/B4용: old->new 차이가 유의미성 기준 '미만'이면 True (=무의미한 변화)."""
    try:
        if isinstance(old, str) and old.strip().endswith("%") and isinstance(new, str) and new.strip().endswith("%"):
            o, n = float(old.strip().rstrip("%")), float(new.strip().rstrip("%"))
            return abs(o - n) < THRESHOLDS["percentage_point"]
        if isinstance(old, (int, float)) and isinstance(new, (int, float)):
            if "premium" in item_hint:
                return abs(old - new) < THRESHOLDS["premium"]
            if old != 0:
                return abs(old - new) / abs(old) * 100 < THRESHOLDS["percent"]
    except (ValueError, TypeError):
        pass
    return False  # 판단 불가하면 '유의미하다'고 보수적으로 처리


# ---------------------------------------------------------------- A. 구조적 검사

def check_structural(ai: dict, report: Report):
    if ai.get("judgment") is not None:
        report.add(Finding("A1", "AUTO-FAIL", "boundary", "최상위 judgment가 null이 아님"))

    all_items = ai.get("changes", []) + ai.get("unchanged_items", []) + ai.get("unknowns", []) \
        + ai.get("conflicts", []) + ai.get("additional_conditions", [])
    for e in all_items:
        if e.get("judgment") is not None:
            report.add(Finding("A2", "AUTO-FAIL", "boundary", "item judgment가 null이 아님", e.get("item", "")))

    for e in ai.get("unknowns", []):
        if e.get("status") == "unknown" and e.get("evidence") is not None:
            report.add(Finding("A4", "AUTO-FAIL", "unknown", "unknown인데 evidence가 존재함", e.get("item", "")))
        if e.get("status") == "confirmed_absent" and not e.get("evidence"):
            report.add(Finding("A5", "AUTO-FAIL", "unknown", "confirmed_absent인데 evidence가 없음", e.get("item", "")))

    for e in ai.get("conflicts", []):
        if len(e.get("sources", [])) < 2:
            report.add(Finding("A6", "AUTO-FAIL", "conflict", "conflict의 sources가 2개 미만", e.get("item", "")))
        if e.get("new") is not None:
            report.add(Finding("A7", "AUTO-FAIL", "conflict", "conflict인데 new가 null이 아님(임의 확정)", e.get("item", "")))

    change_keys = {match_key(e) for e in ai.get("changes", [])}
    unchanged_keys = {match_key(e) for e in ai.get("unchanged_items", [])}
    for k in change_keys & unchanged_keys:
        report.add(Finding("A8", "AUTO-FAIL", "structural", f"같은 매칭키가 changes/unchanged_items 양쪽에 존재: {k}"))

    for e in ai.get("changes", []) + ai.get("unchanged_items", []) + ai.get("additional_conditions", []):
        if not e.get("evidence"):
            report.add(Finding("A9", "AUTO-FAIL", "precision", "evidence 누락", e.get("item", "")))

    for e in ai.get("changes", []) + ai.get("unchanged_items", []):
        if e.get("delta_type") == "unchanged" and e.get("old") != e.get("new"):
            report.add(Finding("A11", "AUTO-FAIL", "unknown",
                                f"delta_type=unchanged인데 old({e.get('old')}) != new({e.get('new')}) — "
                                f"unknown을 unchanged로 위장했을 가능성", e.get("item", "")))


# ---------------------------------------------------------------- B/C/D. 매칭 기반 검사

def evaluate_case(case_id: str, ai_output_path: Optional[str] = None) -> Report:
    case = load_case(case_id)
    gt = case["ground_truth"]
    ai = load_ai_output(case_id, ai_output_path)
    report = Report()

    check_structural(ai, report)

    texts = build_source_texts(case)
    gt_index, gt_origin = build_gt_index(gt)

    # --- B1 + 매칭: changes/unchanged_items ---
    matched_gt_change_keys = set()
    consumed_gt_ids: set = set()  # 버그 수정(TC-11): 같은 GT 항목이 여러 AI 항목에 중복 매칭되어
    # Recall이 100%를 넘는 걸 막는다(예: AI가 GT 1개를 amount/scope 2개로 쪼갠 경우).
    for bucket_name in ("changes", "unchanged_items"):
        for e in ai.get(bucket_name, []):
            report.evidence_total += 1
            status = ground_status(e.get("evidence"), e.get("source_id"), texts)
            if status == "not_found":
                report.evidence_ungrounded += 1
                report.add(Finding("B1", "AUTO-FAIL", "precision",
                                    f"evidence가 어떤 원문에도 없음(환각): '{e.get('evidence')}'", e.get("item", "")))
                continue  # 근거 없는 항목은 아래 매칭/임계값 평가에서 제외
            if status == "wrong_source":
                report.add(Finding("B1-wrong-source", "HUMAN-QUEUE", "evidence",
                                    f"evidence 텍스트는 실존하나 명시한 source_id({e.get('source_id')})가 아닌 다른 출처에서 발견됨 — 출처 오귀속 의심",
                                    e.get("item", "")))
                # 텍스트 자체는 진짜이므로 매칭/임계값 평가는 계속 진행한다.

            if value_evidence_mismatch(e, e.get("evidence")):
                report.add(Finding("B5", "AUTO-FAIL", "precision",
                                    f"evidence 문장은 실존하지만 그 문장이 말하는 수치와 선언한 old/new({e.get('old')}->{e.get('new')})가 일치하지 않음 — "
                                    f"'문장이 진짜다'와 '주장한 값이 그 문장에 부합한다'는 서로 다른 검증이다",
                                    e.get("item", "")))

            match, tier = find_match_tiered(e, gt_index, gt, bucket_name)
            if tier == "M2":
                report.add(Finding("M2", "HUMAN-QUEUE", "matching",
                                    f"1차 키 매칭 실패, 같은 카테고리({bucket_name}) 안에서 old/new 값이 일치하는 GT 후보 1건 발견 — "
                                    f"출처 오귀속인지 진짜 신규항목인지 사람 확인 필요(자동 점수 미반영)",
                                    e.get("item", "")))
                continue
            if match is None:
                report.add(Finding("B2", "HUMAN-QUEUE", "precision",
                                    "GT 어디에도 매칭 안 됨(M1/M2 모두 실패, evidence는 원문에 존재) — GT 누락 후보로 사람 검토 필요",
                                    e.get("item", "")))
                continue

            if id(match) in consumed_gt_ids:
                report.add(Finding("DUP-MATCH", "HUMAN-QUEUE", "matching",
                                    "이 GT 항목은 이미 다른 AI 항목이 매칭했음 — AI가 하나의 GT 사실을 "
                                    "여러 항목으로 쪼갰을 가능성(추가 Recall 가산 없이 기록만)",
                                    e.get("item", "")))
                continue
            consumed_gt_ids.add(id(match))

            origin = gt_origin[id(match)]
            item_hint = e.get("item", "")

            if bucket_name == "changes":
                if origin == "changes":
                    matched_gt_change_keys.add(match_key(match))
                    report.recall_hits += 1  # 정확히 changes에서 찾음
                elif origin == "unchanged_items":
                    trivial = within_threshold(e.get("old"), e.get("new"), item_hint)
                    if trivial:
                        report.add(Finding("B3", "AUTO-FAIL", "precision",
                                            "유의미성 기준 미달인데 changes에 넣음(과검출)", item_hint))
                    else:
                        report.add(Finding("B3", "AUTO-FAIL", "precision",
                                            "GT상 unchanged인 항목을 changes로 잘못 검출", item_hint))
            elif bucket_name == "unchanged_items":
                if origin == "changes":
                    real_change = not within_threshold(match.get("old"), match.get("new"), item_hint)
                    if real_change:
                        report.add(Finding("B4", "AUTO-FAIL", "recall",
                                            "GT상 유의미한 변화인데 unchanged_items로 잘못 배치(Recall 위반)",
                                            item_hint))
                    else:
                        matched_gt_change_keys.add(match_key(match))
                        report.recall_hits += 1  # GT도 사실 무의미한 차이 → unchanged 처리가 맞음

    report.recall_total = len(gt.get("changes", []))
    report.precision_total = len(ai.get("changes", [])) + len(ai.get("unchanged_items", []))
    report.precision_violations = sum(1 for f in report.findings if f.axis == "precision" and f.severity == "AUTO-FAIL")

    # --- C. Unknown/Confirmed_absent ---
    completeness_map = {}
    for doc_name, doc in case["new_product"]["documents"].items():
        completeness_map[doc_name] = doc.get("completeness")

    for e in ai.get("unknowns", []):
        report.evidence_total += 1
        if e.get("status") == "confirmed_absent":
            status = ground_status(e.get("evidence"), e.get("source_id"), texts)
            if status == "not_found":
                report.evidence_ungrounded += 1
                report.add(Finding("B1", "AUTO-FAIL", "precision", "confirmed_absent의 evidence가 어떤 원문에도 없음", e.get("item", "")))
            elif status == "wrong_source":
                report.add(Finding("B1-wrong-source", "HUMAN-QUEUE", "evidence",
                                    f"confirmed_absent의 evidence가 명시한 source_id({e.get('source_id')})가 아닌 다른 출처에서 발견됨",
                                    e.get("item", "")))
            loc = e.get("source_location")
            if completeness_map.get(loc) != "complete":
                report.add(Finding("C1", "AUTO-FAIL", "unknown",
                                    f"completeness가 'complete'가 아닌 문서에 confirmed_absent 사용(unknown이었어야 함): {loc}",
                                    e.get("item", "")))
        if e.get("depends_on"):
            for dep_item in e["depends_on"]:
                dep_resolved = any(
                    u.get("item") == dep_item and u.get("status") not in ("unknown", "confirmed_absent")
                    for u in ai.get("unknowns", [])
                )
                if not dep_resolved:
                    pass  # 정상 — 선행 정보 미확정 상태 유지
        match = find_match(e, gt_index)
        if match is not None and gt_origin[id(match)] == "unknown":
            report.recall_hits += 0  # unknown 매칭은 별도 Unknown Accuracy로 취급(카운트만)

    # --- D. Conflict ---
    change_match_keys_ai = {match_key(e) for e in ai.get("changes", [])}
    unchanged_match_keys_ai = {match_key(x) for x in ai.get("unchanged_items", [])}
    for e in ai.get("conflicts", []):
        # 버그 수정: conflict 객체는 최상위에 source_id/source_location이 없고 sources[] 하위에만
        # 있다. match_key(e)를 그대로 쓰면 (None, None)이 되어 항상 실패로 오판정됐다(TC-04에서
        # 실제로 발견). sources[] 각 항목의 키를 모아서 비교해야 한다.
        source_keys = {(s.get("source_id"), s.get("source_location")) for s in e.get("sources", [])}
        if e.get("type") == "source_discrepancy" and not (source_keys & change_match_keys_ai):
            report.add(Finding("D1", "AUTO-FAIL", "conflict",
                                "source_discrepancy인데 changes에 데이터 기반 확정값이 없음", e.get("item", "")))
        if e.get("type") == "document_conflict" and (source_keys & (change_match_keys_ai | unchanged_match_keys_ai)):
            report.add(Finding("D2", "AUTO-FAIL", "conflict",
                                "document_conflict인데 changes/unchanged_items에 단일 확정값도 존재", e.get("item", "")))

    # --- D3. Conflict Recall: GT가 표시한 충돌을 AI가 놓쳤는지 (TC-05 실행 중 발견, 신규 추가) ---
    gt_conflict_entries = gt.get("conflicts", []) + gt.get("source_discrepancies", [])
    ai_conflict_source_key_sets = [
        {(s.get("source_id"), s.get("source_location")) for s in c.get("sources", [])}
        for c in ai.get("conflicts", [])
    ]
    for gc in gt_conflict_entries:
        gt_keys = {(s.get("source_id"), s.get("location") or s.get("source_location")) for s in gc.get("sources", [])}
        covered = any(gt_keys & ai_keys for ai_keys in ai_conflict_source_key_sets)
        if covered:
            continue
        if gt_keys & (change_match_keys_ai | unchanged_match_keys_ai):
            report.add(Finding("D3", "AUTO-FAIL", "conflict",
                                "GT상 conflict인데 AI가 감지하지 못하고 한쪽 값으로 임의 확정함(Conflict Accuracy 위반)",
                                gc.get("item", "")))
        else:
            report.add(Finding("D3", "AUTO-FAIL", "conflict",
                                "GT상 conflict을 AI가 아예 언급하지 않음(Conflict Recall 위반)",
                                gc.get("item", "")))

    # --- D4. Unknown Recall: GT가 요구하는 unknown을 AI가 빠뜨렸는지 (TC-15 실행 중 발견, 신규 추가) ---
    # unknowns는 source_location이 GT에서 사람이 쓴 서술형 문구인 경우가 많아(예: "enrollment_date
    # field") source_location을 매칭 키로 강제하지 않는다. 대신 source_id + item 이름의 느슨한
    # 겹침(정규화 후 부분 문자열 포함)으로 매칭한다.
    ai_unknown_only = [u for u in ai.get("unknowns", []) if u.get("status") == "unknown"]
    for gu in gt.get("unknown_or_confirmed_absent_items", []):
        if gu.get("status") != "unknown":
            continue  # confirmed_absent는 이 규칙 대상이 아님(성격이 다름)
        gt_norm = normalize_item(gu.get("item"))
        same_source = [u for u in ai_unknown_only if u.get("source_id") == gu.get("source_id")]
        pool = same_source if same_source else ai_unknown_only
        found = False
        for u in pool:
            u_norm = normalize_item(u.get("item"))
            if u_norm and gt_norm and (u_norm in gt_norm or gt_norm in u_norm):
                found = True
                break
        if not found and len(same_source) == 1:
            found = True  # source_id가 유일하게 일치하면 이름이 달라도 같은 항목으로 본다
        if not found:
            report.add(Finding("D4", "AUTO-FAIL", "unknown",
                                "GT상 unknown 항목인데 AI 출력에 대응하는 unknown이 없음(Unknown Recall 위반)",
                                gu.get("item", "")))

    # --- E2. 판단어 텍스트 스캔 (HUMAN-QUEUE) ---
    all_items = ai.get("changes", []) + ai.get("unchanged_items", []) + ai.get("unknowns", []) \
        + ai.get("conflicts", []) + ai.get("additional_conditions", [])
    for e in all_items:
        for field_name in ("evidence", "note", "reason", "description"):
            text = e.get(field_name)
            if not text:
                continue
            for kw in JUDGMENT_KEYWORDS:
                if kw in text:
                    report.add(Finding("E2", "HUMAN-QUEUE", "boundary",
                                        f"'{field_name}' 필드에 판단어 후보 '{kw}' 검출 — 인용인지 AI 판단인지 사람 확인 필요: {text}",
                                        e.get("item", "")))

    return report


def print_report(case_id: str, report: Report):
    print(f"===== {case_id} 평가 결과 =====")
    recall = report.recall_hits / report.recall_total if report.recall_total else None
    precision = 1 - (report.precision_violations / report.precision_total) if report.precision_total else None
    grounded_rate = 1 - (report.evidence_ungrounded / report.evidence_total) if report.evidence_total else None
    print(f"Recall: {report.recall_hits}/{report.recall_total} = {recall}")
    print(f"Precision(구조 위반 없는 비율): {precision} (검사대상 {report.precision_total}, 위반 {report.precision_violations})")
    print(f"Evidence 원문 존재율: {grounded_rate} (검사 {report.evidence_total}, 미존재 {report.evidence_ungrounded})")
    print()
    auto_fails = [f for f in report.findings if f.severity == "AUTO-FAIL"]
    human_queue = [f for f in report.findings if f.severity == "HUMAN-QUEUE"]
    print(f"AUTO-FAIL {len(auto_fails)}건:")
    for f in auto_fails:
        print(f"  [{f.rule}/{f.axis}] {f.item_ref}: {f.message}")
    print(f"\nHUMAN-QUEUE {len(human_queue)}건:")
    for f in human_queue:
        print(f"  [{f.rule}/{f.axis}] {f.item_ref}: {f.message}")


if __name__ == "__main__":
    case_id = sys.argv[1] if len(sys.argv) > 1 else "TC-01"
    ai_output_path = sys.argv[2] if len(sys.argv) > 2 else None
    rep = evaluate_case(case_id, ai_output_path)
    print_report(case_id, rep)

    # ai_output_path를 명시하면(예: 교정본, 회귀 fixture) 결과 파일명에 그 파일의 상위 폴더명+stem을
    # 반영해 원본 평가 결과를 덮어쓰지 않는다 — 재현성을 위한 것. parent 폴더명이 없으면
    # (=results/structured/, 기본 위치) 그냥 case_id를 쓴다 — TC-05.json이 results/corrected/와
    # results/structured/ 양쪽에 있어서 stem만 쓰면 같은 파일명으로 충돌했던 실제 버그를 수정.
    if ai_output_path:
        p = Path(ai_output_path)
        out_stem = p.stem if p.parent.name == "structured" else f"{p.parent.name}_{p.stem}"
    else:
        out_stem = case_id
    out_path = BASE / "results" / "metadata" / f"{out_stem}_eval.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "case_id": case_id,
                "recall_hits": rep.recall_hits,
                "recall_total": rep.recall_total,
                "precision_violations": rep.precision_violations,
                "precision_total": rep.precision_total,
                "evidence_ungrounded": rep.evidence_ungrounded,
                "evidence_total": rep.evidence_total,
                "findings": [f.__dict__ for f in rep.findings],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n저장: {out_path}")
