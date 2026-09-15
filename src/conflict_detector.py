"""
GT 없는 Conflict 검출 (evaluate.py의 D3와는 다른 층위).

D3(evaluate.py)는 GT에 이미 적힌 conflict를 AI가 놓쳤는지 사후 대조한다 — GT가 있어야 동작한다.
이 모듈은 GT를 전혀 보지 않고, new_product.documents(같은 신규 상품의 서로 다른 공식 문서들)의
원문 텍스트만 정규식+문자 bigram 유사도로 훑어서 "같은 항목인데 다른 값"을 스스로 찾아낸다.
LLM도 쓰지 않는다 — 순수 규칙 기반이라 재현 가능하고, 왜 그 후보를 골랐는지 그대로 설명된다.

범위(의도적으로 좁힘): 퍼센트(%)·원화(원) 수치가 서로 다른 문서에 등장하고, 그 수치를 둘러싼
문맥(같은 문장)이 겹칠 때만 후보로 표시한다. TC-04 유형(발화 vs 데이터 불일치)이나 TC-15 유형
(자기모순/면책조항)은 다루지 않는다 — 그건 다른 실패 유형이라 이 탐지기의 대상이 아니다.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

NUMBER_PATTERN = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(%|원)")
HANGUL_ONLY = re.compile(r"[가-힣]+")
BIGRAM_OVERLAP_THRESHOLD = 0.25


def load_case(case_id: str) -> dict:
    path = BASE / "data" / f"{case_id.lower().replace('-', '')}_data.json"
    return json.loads(path.read_text(encoding="utf-8"))


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"[.\n]", text)
    return [p.strip() for p in parts if p.strip()]


def extract_number_mentions(source_id: str, location: str, text: str) -> list[dict]:
    """문서 텍스트에서 %/원 수치를 문장 단위 문맥과 함께 뽑는다. GT는 전혀 참조하지 않는다."""
    mentions = []
    for sentence in split_sentences(text):
        for m in NUMBER_PATTERN.finditer(sentence):
            mentions.append({
                "source_id": source_id,
                "location": location,
                "value": m.group(1).replace(",", ""),
                "unit": m.group(2),
                "sentence": sentence,
                "evidence": sentence,
            })
    return mentions


def bigram_overlap(a: str, b: str) -> float:
    """한글 문자만 남긴 뒤 2-gram Jaccard 유사도. 조사(은/는/이/가 등) 변형에도 안정적."""
    def bigrams(s: str) -> set:
        hangul = "".join(HANGUL_ONLY.findall(s))
        return {hangul[i:i + 2] for i in range(len(hangul) - 1)} if len(hangul) >= 2 else set()

    ba, bb = bigrams(a), bigrams(b)
    if not ba or not bb:
        return 0.0
    return len(ba & bb) / len(ba | bb)


def find_document_conflicts(case: dict) -> list[dict]:
    """new_product.documents 안에서, 서로 다른 문서가 같은 항목을 다른 값으로 제시하는 경우를 찾는다."""
    new_product = case.get("new_product", {})
    docs = new_product.get("documents")
    if not docs or len(docs) < 2:
        return []

    source_id = new_product.get("source_id")
    all_mentions = []
    for location, doc in docs.items():
        all_mentions.extend(extract_number_mentions(source_id, location, doc.get("text", "")))

    conflicts = []
    seen = set()
    for i, a in enumerate(all_mentions):
        for b in all_mentions[i + 1:]:
            if a["location"] == b["location"]:
                continue  # 같은 문서 안 비교는 충돌이 아님
            if a["unit"] != b["unit"]:
                continue
            if a["value"] == b["value"]:
                continue  # 같은 값이면 오히려 서로 확인해주는 것 — 충돌 아님
            overlap = bigram_overlap(a["sentence"], b["sentence"])
            if overlap < BIGRAM_OVERLAP_THRESHOLD:
                continue
            key = tuple(sorted([(a["location"], a["value"]), (b["location"], b["value"])]))
            if key in seen:
                continue
            seen.add(key)
            conflicts.append({
                "type": "document_conflict",
                "context_overlap": round(overlap, 3),
                "sources": [
                    {"source_id": a["source_id"], "source_location": a["location"], "evidence": a["evidence"]},
                    {"source_id": b["source_id"], "source_location": b["location"], "evidence": b["evidence"]},
                ],
                "note": "GT 미참조 · 정규식+문자 bigram 유사도로 탐지된 후보 — 사람 확인 필요(Human Review)",
            })
    return conflicts


def run(case_id: str) -> dict:
    case = load_case(case_id)
    candidates = find_document_conflicts(case)
    result = {
        "case_id": case_id,
        "method": "regex(%/원 수치 추출) + 문장 단위 한글 2-gram Jaccard 유사도, GT/LLM 미사용",
        "candidates_found": len(candidates),
        "candidates": candidates,
    }
    out_dir = BASE / "results" / "conflict_detection"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{case_id}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n-> {out_path}")
    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("사용법: python src/conflict_detector.py TC-05")
        sys.exit(1)
    run(sys.argv[1])
