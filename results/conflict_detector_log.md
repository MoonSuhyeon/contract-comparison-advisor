# GT 없는 Conflict 검출 실험 기록 (`src/conflict_detector.py`)

## 배경

지금까지 conflict 누락(TC-05, TC-15)은 두 가지 방식으로만 다뤘다:
1. `evaluate.py`의 D3 규칙 — **GT가 있어야** AI가 conflict를 놓쳤는지 사후 대조 가능
2. TC-05 Human Review — AI 출력을 **사람이 수동으로** 고침

둘 다 "AI가 이미 낸 출력"을 사후에 점검하는 방식이었고, GT 없이 원본 문서만 보고 충돌을
스스로 찾아내는 장치는 없었다. 이번에 그 빈 자리를 채우는 최소 구현을 추가했다.

## 방법 (`src/conflict_detector.py`)

- **LLM도, GT도 쓰지 않는다.** `new_product.documents`(신규 상품의 서로 다른 공식 문서들)의
  원문 텍스트에서 정규식으로 `%`/`원` 수치를 문장 단위로 추출하고, 서로 다른 문서에서 값이
  다른데 문맥(한글 2-gram Jaccard 유사도, 조사 변형에 안정적)이 겹치면 충돌 후보로 표시한다.
- 의도적으로 좁힌 범위: **문서 대 문서** 충돌(TC-05 유형)만 다룬다. 발화 대 데이터 불일치
  (TC-04/TC-15의 source_discrepancy 유형)나 자기모순(TC-15 unchanged 위장)은 다른 실패
  유형이라 이 탐지기의 대상이 아니다 — 범위를 넓히지 않고 명시적으로 한계로 남긴다.

## 실행 결과 (N=7 전체, GT 미참조 상태로 실행)

| 케이스 | candidates_found | 비고 |
|---|---|---|
| TC-01 | 0 | documents 있음, 실제로 값 충돌 없음 — 정상 |
| TC-03 | 0 | 동일 |
| TC-04 | 0 | GT상 conflict가 있지만 유형이 source_discrepancy(발화 vs 데이터)라 이 탐지기 범위 밖 — 설계상 의도된 결과 |
| **TC-05** | **1** | **정확히 탐지** — `product_summary_brochure`(40%) vs `product_terms_detail`(35%), context_overlap 0.316 |
| TC-10 | 0 | documents 있음, 값 충돌 없음 |
| TC-11 | 0 | 동일 |
| TC-15 | 0 | GT상 conflict가 있지만 역시 source_discrepancy 유형이라 범위 밖(TC-04와 동일 사유) |

**오탐(false positive) 0건, 진탐(true positive) 1/1건.** 특히 TC-05의 `premium`(보험료
90,000원)은 한 문서에만 등장해 비교 대상 자체가 없어 정상적으로 충돌로 잡히지 않았다 —
"아무 숫자나 다르면 다 충돌로 본다"는 식의 과잉탐지가 아님을 확인.

## Human Review (TC-05)

`results/conflict_detection/TC-05.json`의 `_human_review` 필드에 기록. 검증 목적으로만
GT와 대조했고(탐지 자체는 GT 미참조), 결과는 true_positive — GT의 conflict 항목과 정확히
일치.

## 이 실험이 증명하는 것 / 증명하지 않는 것

- 증명: 문서 간 수치 충돌은 LLM의 판단 없이도, 원문 텍스트만으로 상당히 신뢰성 있게 잡아낼
  수 있다. 이걸 AI 파이프라인 앞단(Human Review Queue 투입 전)에 배치하면, LLM이 실수로
  conflict를 놓치거나 임의로 하나를 골라도 **독립적인 두 번째 검증 신호**가 남는다.
- 증명하지 않는 것: 이 탐지기가 모든 conflict 유형을 잡는다는 것은 아니다(source_discrepancy,
  자기모순은 여전히 놓침 — 각각 D3/A11이 담당). 또한 문장이 아주 길거나 수치가 복잡한 경우
  (범위값, 조건부 수치 등)에 대한 강건성은 N=7 범위 안에서만 확인했다.

## 남은 한계 (더 개발하지 않고 기록만)

- 임계값(`BIGRAM_OVERLAP_THRESHOLD = 0.25`)은 TC-05 1건에 맞춰 정한 값이라 다른 도메인/
  문서 스타일에서도 그대로 적용될지는 검증 안 됨.
- `%`/`원` 외의 단위(개월, 회, 배 등)는 다루지 않음 — 의도적 축소.
