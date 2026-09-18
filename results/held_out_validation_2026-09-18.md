# 진짜 held-out 검증 (2026-09-18, 2차 피드백 대응)

2차 피드백: "기존 수정에 사용하지 않은 사례 3~5건을 먼저 정하고 기준을 고정한 뒤
검증하는 것을 권장합니다." 기존에 "held-out"이라고 불렀던 TC-03/05/10/11/15는 사실
`evaluate.py`의 9개 결함(D1~D4, B5 등)을 찾아낼 때 이미 썼던 케이스라 진짜 held-out이
아니었다. 이번엔 결함 수정에 **한 번도 쓰지 않은** TC-02, TC-08, TC-13을 새로 뽑아
Structured와 Third Baseline(동일 지침 + 자유서술)을 같은 기준으로 실행했다.

**선정 이유** (`02_테스트케이스.md` 커버리지 표 기준): TC-02(변화 방향 정확성 — 증가/감소
혼재), TC-08(Recall·Precision·Evidence·Critical 항목 종합), TC-13(고아계약 — Unknown
중심, 기존 계약 정보 자체가 결측). 세 축을 겹치지 않게 커버하도록 골랐다.

## 실행

| Case | Structured (`results/structured/`) | Third Baseline (`results/instructed_freeform/`) |
|---|---|---|
| TC-02 | 12,022 tokens, 12.95s, attempts=2 | 2,813 tokens, 4.56s |
| TC-08 | 11,713 tokens, 8.52s, attempts=2 | 2,785 tokens, 5.17s |
| TC-13 | 5,976 tokens, 6.39s, attempts=1 | 2,999 tokens, 4.62s |

Structured는 `evaluate.py`로 자동 채점, Third Baseline은 스키마가 없는 자유 텍스트라
GT와 사람이 직접 대조했다(기존 `instructed_freeform_human_review.md`와 동일한 방식).

## 결과 — Structured (자동 채점)

| Case | Recall | Precision 위반 | 주요 AUTO-FAIL |
|---|---:|---:|---|
| TC-02 | 2/2 | 2건 | B3×2 — GT상 unchanged인 renewal_period, surrender_value_at_5y를 changes로 과검출 |
| TC-08 | 3/3 | 1건 | B3×1 — GT상 unchanged인 premium을 changes로 과검출 |
| TC-13 | 1/1 | 0건 | **D4×4 — GT가 요구하는 unknown 4개(coverage_amount, renewal_period, surrender_value, existing_contract_dissolution_impact)를 전부 놓침** |

**TC-13에서 새로 발견한 문제**: 이 세 항목의 evidence 문장을 열어보면 AI는 "기존 계약이
고아계약이라 정보를 알 수 없다"는 사실 자체는 정확히 서술했다(`"이 계약은 이 회사 시스템
기준으로는 '고아계약'이다. 시스템에서는...세부 계약 내용은 요약 처리되어 있지 않아 이미
경과 시점에서 확인할 수 없다"`). 문제는 이 내용을 `unknowns[]`가 아니라 `unchanged_items[]`에
`old=None, new=None`으로 넣은 것이다. **"모른다"는 것을 스스로 정확히 알고 있으면서도,
스키마의 잘못된 칸에 적어 결과적으로 "변경 없음"처럼 보이게 만들었다** — 원인은 알고
있었지만 그것이 review 화면에서 사람에게 "확인 필요"가 아니라 "변경없음" 카드로 보였을
것이라는 뜻이다. 기존 7개 케이스에서는 한 번도 이런 유형이 나타나지 않았다.

## 결과 — Third Baseline (사람 대조)

| Case | 변경사항 발견 | 판단 경계 |
|---|---|---|
| TC-02 | 실제 변경 2건(보험료, 암 진단비) 모두 발견, unchanged 2건(갱신주기, 해지환급률) 모두 정확히 "동일"로 서술 — **Structured보다 과검출 없음** | 마지막 문단에서 "고객이 보험료가 상승하지만 보장 범위가 확대된 새 상품에 관심이 있을 가능성" — 판단어 키워드는 아니지만 고객 의도를 추정하는 해석성 문장 |
| TC-08 | 실제 변경 3건 모두 발견, unchanged(보험료) 1건도 정확히 "변경 없음" — **Structured보다 과검출 없음** | "특히...고객이 우려할 만한 부분입니다" — 판단에 가까운 해석 문장 |
| TC-13 | old 정보가 없다는 사실을 프로즈로 명확히 서술("이 부분은 Unknown으로 남겨야 하며")하고 GT가 말하는 4개 항목 중 3개(coverage_amount, renewal_period, surrender_value)를 프로즈로 짚음. `existing_contract_dissolution_impact`(해지에 따른 불이익 자체를 판단할 근거 없음)는 명시적으로 짚지 않음 | 판단어 없음 |

## 종합 해석

1. **Recall(놓치지 않고 찾았는가)은 이번에도 팽팽했다** — 실제 changes 항목은 Structured·
   Freeform 모두 6/6(TC-02 2개 + TC-08 3개 + TC-13 1개)을 찾았다. 이번 3건만으로는
   "Structured가 더 많이 찾는다"는 근거가 되지 않는다 — 기존 7건 재분석 결과(14/15 동률)와
   같은 패턴이다.
2. **Precision(과검출 안 하는가)은 오히려 Freeform이 나았다** — Structured는 3건에서
   총 3번 unchanged 항목을 changes로 과검출(B3)했지만, Freeform은 같은 3건에서 과검출이
   한 번도 없었다. 표본이 작아 일반화하지 않지만, "구조화가 항상 더 정밀하다"고 주장할 수
   없다는 근거가 하나 더 늘었다.
3. **가장 중요한 새 발견은 TC-13의 Unknown 처리 실패다.** Structured는 스키마상 올바른
   칸(`unknowns[]`)이 있는데도 그걸 안 쓰고 `unchanged_items`에 `old=None`으로 적어
   Human Review 화면에서 "확인 필요" 대신 "변경없음"으로 보이게 만들 뻔했다 — evaluate.py의
   D4 규칙이 자동으로 잡아냈다. 반면 Freeform은 근거 없이 프로즈로나마 "Unknown으로
   남겨야 한다"고 명시했다. 이번 표본에서는 오히려 **구조화되지 않은 서술이 이 특정
   실패를 사람에게 더 잘 드러냈다.**
4. **판단 경계는 이번에도 Structured가 확실히 우위였다.** Freeform은 3건 중 2건(TC-02,
   TC-08)에서 고객의 감정·관심을 추정하는 해석성 문장을 만들어냈다(판단어 키워드 매칭에는
   안 걸리지만 성격은 같다). Structured는 `judgment: null` 스키마 강제 덕분에 3건 모두
   이런 문장이 없었다(E2 텍스트 스캔 0건).

**결론**: 이번 3건의 진짜 held-out 검증도 기존 결론을 뒤집지 않는다 — "Structured가 더
정확하다"가 아니라 "Structured는 검증 가능성과 판단 경계를 기계적으로 강제한다"이다.
다만 TC-13에서 드러난 새 실패 유형(맞는 이유를 알면서 틀린 칸에 적는 것)은 기존 7건
범위에서는 확인되지 않았던 것으로, Human Review UX가 `unchanged_items`도 근거 문장을
사람이 읽도록 강제해야 한다는 §12 다음 계획에 직접적인 근거를 추가한다.

## 한계

- N=3으로 매우 작다. 통계적 결론이 아니라 "기존 7건에서 안 보이던 실패 유형이 있다"는
  사례 증거로만 쓴다.
- Third Baseline은 사람이 직접 프로즈를 읽고 대조한 것이라 이번 검토자(작성자 본인)의
  주관이 섞일 수 있다 — 자동 채점이 아니다.
- Human Review 실험(A/B, N=7)처럼 사람이 이 3건을 실제로 검토·수정하는 세션은 진행하지
  않았다 — 이번엔 AI 출력 자체의 품질만 비교했다.
