# Phase 2 — 평가기(evaluate.py)를 N=7에 적용하며 발견한 것들

목적: baseline(Phase 3)으로 넘어가기 전에, evaluate.py 자체가 정확히 채점하는지를 여러
케이스에 걸쳐 검증한다. AI의 오류와 평가기의 버그를 섞지 않기 위해, 각 케이스마다 (1) AI가
실제로 무엇을 냈는지 (2) 평가기가 그것을 어떻게 판정했는지 (3) 그 판정이 맞는지를 구분해서
기록한다.

---

## TC-01 (Recall/Weighted Recall 중심)

`results/tc01_iteration_log.md` 참고. v2 채택. B4 규칙이 "delta_type은 맞지만 배열이 틀린"
경우를 정확히 자동 검출함을 확인(Recall 3/4). 평가기 버그 없음.

## TC-03 (Unknown/Precision 중심)

**AI 실행 결과**: premium 변화(95,000→88,000)는 정확히 추출했으나 `source_id`를 `contract_A`로
오귀속(실제로는 `product_B`). 추가로 신규 상품에 없는 면책조항 2건을 `unchanged_items`로
잘못 만들어냄(old=new로 동일 값을 넣어 "변화 없음"을 주장 — 실제로는 신규 상품 자료가
불완전(partial)해서 unknown이어야 하는 항목). 다만 같은 항목들에 대해 올바른 `unknowns`
항목도 별도로 2건 생성함(모순적으로 두 가지를 동시에 주장).

**1차 실행에서 드러난 평가기 버그 2건과 수정**:
1. 콘솔 UTF-8 인코딩 미설정으로 크래시 → `sys.stdout.reconfigure(encoding="utf-8")` 추가.
2. B1이 "완전히 지어낸 것"과 "출처를 잘못 표기했지만 내용은 실존하는 것"을 구분하지 못함
   → `ground_status()`로 분리(grounded/wrong_source/not_found), wrong_source는 HUMAN-QUEUE로.

**매칭 설계의 한계 발견과 수정**: 1차 키(source_id+source_location) 매칭이 출처 오귀속 때문에
실패해서 자동 Recall이 0/1로 나옴 → M1/M2/M3 매칭 신뢰도 계층 도입(`03_평가설계.md` §2-4,
`schema/validation_rules.md` §0). M2(값 기반 후보, 같은 카테고리 내 old/new 일치)는 자동
점수에 반영하지 않고 HUMAN-QUEUE로만 표시하도록 구현.

**정확한 기록(과장하거나 축소하지 않음)**: TC-03에서 AI는 premium 변경을 추출했으나 source_id를
오귀속했다. 1차 매칭 기준으로는 GT와 매칭되지 않아 자동 Recall 0으로 판정되었으며, 값 기반
2차 매칭(M2)에서 동일 후보가 확인되어 출처 오귀속과 내용 누락을 분리할 필요가 확인되었다. 이와
별개로 신규 상품에 없는 면책조항 정보를 "변화 없음"으로 지어낸 것은 real 환각에 해당하며,
같은 항목에 대해 정확한 unknown 판단도 동시에 존재해 AI가 내부적으로 일관되지 않은 응답을
냈다는 것도 함께 기록한다.

수정 후 재검증 결과: TC-01 회귀 없음(Recall 3/4 그대로), TC-03의 premium은 M2/HUMAN-QUEUE로
정확히 재분류됨.

---

## TC-04 (Recall/Conflict/Evidence/Precision 중심)

**AI 실행 결과**: premium은 정확. `coverage_items.cancer_diagnosis`(3,000만→2,000만)를
`changes`(delta_type: `scope_narrowed`)와 `unchanged_items`(delta_type: `unchanged`) **양쪽에
동시에** 출력해 자기모순을 일으킴. `delta_type`도 의미상 오용 — 순수 금액 감소인데
`scope_narrowed`(TC-11류 "범위 축소"와 혼동)를 붙임. `conflicts`에는 source_discrepancy를
올바르게 생성(설계사 발화 "그대로" vs 데이터 축소).

**평가기 버그 발견·수정**: `D1`/`D2`가 `conflict` 객체에 `match_key()`를 그대로 적용하고
있었는데, `conflict`는 최상위에 `source_id`/`source_location`이 없고 `sources[]` 하위 배열에만
있다. 그래서 `match_key(conflict)`가 항상 `(None, None)`이 되어 **모든 source_discrepancy가
무조건 D1 위반으로 오판정**되고 있었다. `sources[]` 각 항목의 키 집합과 비교하도록 수정.

**재검증 결과**: D1 오탐 사라짐. A8(같은 매칭키가 changes/unchanged_items 양쪽에 존재)과
B4가 실제 자기모순을 정확히 잡음. Recall은 2/2=1.0으로 나오는데, 이는 cancer_diagnosis가
`changes` 쪽에서 이미 정상 매칭되어 카운트됐고, `unchanged_items` 쪽 중복 항목은 recall_hits를
추가로 깎지 않으면서 별도로 AUTO-FAIL(A8, B4)만 쌓이는 구조이기 때문이다 — 의도한 설계이나,
"B4 = Recall 위반"이라는 메시지 문구가 이 경우 전체 Recall 수치와는 안 맞아 보일 수 있다는
점을 기록해둔다(수정하지 않고 관찰만 기록).

## TC-05 (Conflict 중심)

**1차 실행**: 모델이 `conflicts[0].new`에 "35%"(둘 중 한 문서의 값)를 넣으려다 스키마 검증에
3회 연속 실패해서 `llm_extractor.py`가 그냥 크래시함. 이 프로젝트 목적(AI 오류 관찰)에 맞지
않으므로, 최종 시도 후에도 무효면 `_schema_valid: false`로 표시해 그대로 저장하도록 수정.

**2차 실행(재시도, 독립적인 새 샘플링)**: 이번엔 스키마는 통과했지만 **더 심각한 실패**가
나왔다 — `conflicts`를 아예 만들지 않고, 두 문서(40%/35%) 중 **35%를 조용히 골라 changes에
단일 확정값으로 제출**함. TC-05가 정확히 막으려던 실패 유형이 실제로 재현됨.

**평가기의 진짜 결함 발견**: 기존 규칙(D1/D2)은 AI가 "이미 만든" conflicts 항목의 내부
정합성만 검사했다. AI가 conflict 자체를 놓치고 조용히 단일값으로 확정해버리는 경우를 잡는
규칙이 아예 없었다 — B1(환각 검사)은 그 값이 실제 원문에 있으므로 통과하고, GT changes/
unchanged_items에도 안 걸려서 애매한 HUMAN-QUEUE(B2)로만 남아 "이게 심각한 오류"라는 신호가
없었다. **새 규칙 D3(Conflict Recall) 추가**: GT의 conflicts/source_discrepancies 각 항목의
sources[] 키 집합을 AI의 conflicts와 대조해서, 커버되지 않으면 (a) 한쪽 값을 임의 확정한
경우와 (b) 아예 언급이 없는 경우를 구분해 AUTO-FAIL 처리.

**재검증**: TC-04(회귀 확인, D3는 발동 안 함 — AI가 conflict를 정상적으로 감지했으므로 정상),
TC-05(D3가 정확히 발동: "GT상 conflict인데 AI가 감지하지 못하고 한쪽 값으로 임의 확정함").
사소한 중복: 같은 항목에 D3(AUTO-FAIL)와 B2(HUMAN-QUEUE)가 동시에 뜬다 — 틀린 건 아니지만
리포트가 약간 중복되며, 지금은 고치지 않고 관찰만 기록.

## TC-10 (Precision/환각방지 중심)

**결과**: 완전 클린 패스(Recall 1/1, Precision 위반 0, Evidence 100%). 모델이 "무사고 할인
특약" 질문에 이끌리지 않고 `confirmed_absent`를 정확히 사용했고, 그 근거(완전한 특약 목록
텍스트)도 정확히 인용했다. 이번 프로젝트가 가장 강하게 내세우는 "환각 방지"를 가장 순수하게
겨냥한 케이스가 실제로 깨끗하게 통과한 것은 그 자체로 의미 있는 실측 근거다. 평가기 버그 없음.

## TC-11 (B항목 Recall/Weighted Recall 중심)

**AI 실행 결과**: GT의 단일 항목(coverage_scope_cerebro — 금액은 동일, 진단기준만 축소)을 AI가
"금액 unchanged"와 "진단기준 scope_narrowed" **두 개의 별도 항목**으로 쪼갬. 둘 다 같은
매칭 키(product_B, coverage_list)를 가짐.

**평가기 버그(심각) 발견·수정**: 같은 GT 항목이 서로 다른 두 AI 항목에 중복 매칭되면서 **Recall이
3/2 = 1.5로 나오는, 100%를 초과하는 불가능한 수치**가 나왔다. `consumed_gt_ids` 집합으로 같은
GT 항목이 한 번만 카운트되도록 수정 → Recall 2/2 = 1.0으로 정상화.

**알려진 잔여 한계(지금은 고치지 않고 기록만)**: 어떤 AI 항목이 그 GT 매칭을 "차지"하는지가
배열 순서에 의존한다 — 이번엔 우연히 (의미상 안 맞는) "금액 unchanged" 항목이 먼저 처리되어
매칭을 차지하고, 실제로 GT와 내용이 더 가까운 "진단기준 scope_narrowed" 항목이 중복으로
밀려났다. 두 항목 모두 리포트에는 남으므로(하나는 정상 매칭, 하나는 DUP-MATCH로) 정보 손실은
없지만, 어느 쪽이 "진짜" 매칭인지 값 유사도로 고르는 로직은 아직 없다. 완벽한 의미 매칭은
이 평가기의 범위를 넘어선다고 보고 지금은 보류.

## TC-15 (복합 케이스, 6축 종합)

**AI 실행 결과 요약**: premium/뇌심혈관삭제/상해장해축소 3건은 정확히 매칭·채점됨(source_id/
location이 모두 하나의 문서 `product_summary_brochure`로 몰려있음에도 old/new 값 기반
교차검증으로 잘 구분됨). 반면 다음 2가지 실제 오류를 새로 발견:
- `exclusion_clause.cancer`를 `delta_type: "unchanged"`, `new: null`로 출력 — TC-15 설계
  문서가 정확히 예견했던 실패("면책조항을 신규에도 그대로 있다고 임의 확정")가 실제로
  재현됨. **A11 규칙 신설**로 자동 검출(old!=new인데 unchanged라고 주장하면 AUTO-FAIL).
  같은 패턴이 TC-04에서도 별도로 발견됨(A8과는 독립적으로 A11도 발동).
- `coverage_amount_accident_disability`에서 설계사의 "그대로예요" 발화와 실제 축소(1,000만→
  500만)의 불일치를 전혀 감지하지 못하고 conflicts 없이 조용히 changes로만 확정 — D3가
  정확히 잡음(TC-05와 같은 유형의 실패가 다른 케이스에서도 재현됨).

**평가기의 두 가지 더 근본적인 한계 발견 (지금 고치지 않고 보고)**:

1. **텍스트값 paraphrase에 대한 관용도 없음**: `coverage_scope_cancer` 항목에서 AI는 old를
   원문과 정확히 동일하게, new도 핵심 의미("침습암만 해당")는 정확히 추출했다. 하지만 GT의
   new는 "침습암만 해당 (경계성종양·상피내암 제외)"로 더 길게 서술되어 있어 **정확한 문자열
   일치가 안 되고**, M1도 M2도 실패해서 실제로는 맞는 답이 HUMAN-QUEUE(B2, "GT 누락 후보")로
   내려갔다. TC-15의 Recall 3/4는 이 1건 때문에 실제보다 낮게 나온 것일 수 있다.
2. **unknowns 카테고리는 source_location 관례가 A항목과 근본적으로 다르다**: A항목은
   source_location이 실제 문서 키(`coverage_list` 등)라 안정적으로 매칭되지만, unknowns는
   GT가 `"enrollment_date field"`처럼 사람이 쓴 서술적 위치명을 쓰는 경우가 많아, AI가 그
   정확한 문구를 맞힐 방법이 없다(AI는 `source_location: null`로 냄). 그 결과 AI가 개념적으로
   맞는 unknown 항목(enrollment_date)도 매칭 실패 위험이 있고, 애초에 **"GT의 unknown 항목을
   AI가 빠짐없이 냈는가"를 채점하는 Unknown Recall 규칙 자체가 아직 없다**(Conflict Recall인
   D3에 대응하는 게 unknowns 쪽엔 없음). 실제로 TC-15 GT는 unknown 3개(exclusion_clause_cancer,
   enrollment_date, existing_contract_dissolution_impact)를 기대하는데 AI는 1개(enrollment_date)
   만 냈고, 이걸 놓쳤다는 게 지금 점수에 전혀 반영되지 않는다.

이 두 가지는 단순 버그 수정이 아니라 매칭 전략 자체에 대한 결정이 필요해서, 구현 전에 보고한다.

## 결정 (30분 제한 고려)

- **D4(Unknown Recall) 추가함**: D3와 대칭이며 명확한 평가 누락이었다. `source_id` + `item`
  이름의 느슨한 겹침(정규화 후 부분 문자열 포함)으로 매칭하고, `source_location`은 강제하지
  않는다(GT의 unknowns는 서술형 위치 문구가 많아서). `confirmed_absent`는 이 규칙 대상에서
  제외한다(성격이 다름). 재검증 결과: TC-11의 `parent_stroke_type`, TC-15의
  `exclusion_clause_cancer` 누락을 정확히 검출. 다른 6개 케이스 회귀 없음.
- **paraphrase 퍼지 매칭은 보류함**: 임계값 설정 근거가 부족하고 오탐 위험(의미가 다른데
  비슷한 문자열을 같다고 오판)이 있어 이번 MVP 범위에 넣지 않는다. **평가 한계로 명시**: 핵심
  의미가 동일하더라도 표현이 다른 paraphrase는 문자열 기반 매칭에서 미매칭으로 판정될 수
  있다. 해당 사례(TC-15의 `coverage_scope_cancer`)는 Human Review 대상으로 남긴다.

## Human Review 시연 (TC-05) — 검증 중 발견한 마지막 잔여 한계

TC-05의 D3(Conflict Recall) 위반을 사람이 직접 수정(`results/corrected/TC-05.json`: changes에서
surrender_value_at_10y를 빼고 conflicts로 재분류)한 뒤, "이제 D3가 안 뜰 것"이라는 예상을
실제로 evaluate.py에 돌려서 검증했다(임시 교체 후 원본 복원, 새 코드 없이 기존 도구 재사용).

예상대로 D3는 사라졌지만, **예상 못 했던 D2가 새로 발동**했다: premium 항목이 우연히 conflict와
같은 문서(product_summary_brochure)를 근거로 삼고 있어서, D2가 "같은 사실의 중복 확정"과 "같은
문서를 인용하는 무관한 두 항목"을 구분하지 못하고 오탐을 낸 것. 지금은 고치지 않고 기록만
남긴다 — 지적하신 대로 지금부터는 평가기를 더 완벽하게 만들려 하지 않는다.

## Phase 2 종합

N=7 전체 실행 완료. 평가기 버그 7건 발견·수정(인코딩 크래시, B1 오분류, M1/M2/M3 도입, D1/D2
키 버그, 중복매칭 캡, D3 신설, D4 신설, A11 신설 — 세다 보면 7개 이상이지만 핵심은 "여러
케이스를 실제로 돌리지 않았으면 하나도 못 찾았을 것들"이라는 점). 실제 AI 오류 6개 유형 확인
(배열 라우팅, 자기모순, conflict 감지 실패 2회 재현, unchanged 위장, 항목 분할). TC-10은
클린 패스로 환각 방지 설계가 실제로 작동함을 보여줌. Phase 3(baseline)로 진행 가능.

## Phase 8 — 값-근거 일치(B5) 회귀 테스트 + 재현성 수정 (2026-09-16)

회귀 테스트로 교정본(`results/corrected/TC-05.json`)의 premium `new`값을 90,000→999,999로
의도적으로 바꾸고 evidence 문장("월 보험료 90,000원.")은 그대로 둔 뒤 evaluate.py를 돌려봤는데,
이 값 위조를 잡아내지 못한다는 걸 확인했다.

**원인**: B1(`ground_status`)은 "evidence 문장이 원문에 실존하는가"만 검사한다. "선언한
old/new 값이 그 evidence 문장이 실제로 말하는 수치와 일치하는가"는 완전히 다른 검사인데,
이 검사가 아예 없었다. 문장이 진짜인 것과, 그 문장으로 뒷받침한다고 주장하는 값이 실제로
맞는 것은 서로 다른 주장이다.

**수정**: `extract_grounded_numbers()`(evidence에서 %/원/만원 수치를 추출, "만원"은 ×10000
환산)와 `value_to_number_str()`(old/new를 비교 가능한 정규화 숫자 문자열로 변환)을 추가하고,
`value_evidence_mismatch()`로 "evidence에 수치가 있는데 old/new 어느 쪽과도 안 맞으면 위반"인
**B5** 규칙을 신설했다. evidence에 수치가 아예 없는 서술형 항목(예: "목록에 없음")은 검사
대상에서 제외한다 — 이 규칙은 값 위조만 잡지, 서술형 evidence의 진위는 B1이 담당한다.

**회귀 검증 (fixture 3종, 수정 전/후 대조)**:

| Fixture | 수정 전 (커밋 `016fa15` 시점 evaluate.py) | 수정 후 (B5 포함) |
|---|---|---|
| 정상 — `results/structured/TC-01.json` | AUTO-FAIL 1건(B4, 기존 이슈) | 동일 — B5로 인한 신규 오탐 없음 |
| 실제 conflict — `results/corrected/TC-05.json` | (아래 "재현성 버그" 참고) | AUTO-FAIL 1건(D2, 기존 잔여 한계 — 그대로 유지, 이번엔 안 건드림) |
| 값 위조 — `results/regression_fixtures/TC-05_corrupted_value.json`(premium.new=999999, evidence는 그대로) | `ground_status`가 `grounded` 반환 → **위조 미검출** | **B5가 AUTO-FAIL로 정확히 검출**: "evidence 문장은 실존하지만 그 문장이 말하는 수치와 선언한 old/new(100000->999999)가 일치하지 않음" |

N=7 전체(TC-01,03,04,05,10,11,15)를 재실행해 B5가 기존 통과 케이스에 새 오탐을 만들지 않음을
확인함(Precision 전부 기존과 동일하게 1.0 유지, `git diff --stat results/metadata/`로 검증).

**부수적으로 발견한 진짜 재현성 버그**: `results/metadata/TC-05_eval.json`을 다시 만들어보니
기존 저장 결과가 실제로는 원본이 아니라 **교정본을 평가한 결과(D2)**였다. 예전 Human Review
검증 때 원본 자리에 교정본을 임시로 바꿔치기해서 평가한 뒤 "코드는 원복"했지만, **평가 결과
파일은 원복하지 않았던 것** — 그래서 한동안 'TC-05 원본 평가'라는 이름의 파일이 실제로는
교정본의 평가였다. `evaluate.py`에 `ai_output_path` 인자를 추가해 임의 파일을 직접 지정해
평가할 수 있게 고치고(더 이상 임시 바꿔치기 불필요), 출력 파일명도 상위 폴더명을 붙여 구분되게
했다:
- `results/metadata/TC-05_eval.json` — 원본(`results/structured/TC-05.json`) 재평가 →
  이제 정확히 D3(Conflict Recall 위반, AI가 conflict를 놓치고 35%로 임의 확정)가 나옴
- `results/metadata/corrected_TC-05_eval.json` — 교정본 재평가 → D2(기존 잔여 한계)
- `results/metadata/regression_fixtures_TC-05_corrupted_value_eval.json` — 값 위조 fixture → B5

**남은 한계**: B5는 %/원/만원 수치만 다룬다. 기간(개월/회) 등 다른 단위나, 두 자리 이상의 단위
혼용(예: "1,200만원 → 12,000,000원"을 서로 다른 표기로 같이 쓰는 경우)에 대한 강건성은 N=7
범위 안에서만 확인했다 — 확장은 필요해질 때 하기로 한다(지금 무리하게 일반화하지 않음).
