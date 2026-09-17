# 출력 스키마 검증 규칙 (실행용 확정본)

기준: `03_평가설계.md` §1, `schema/output_schema.json`. 여기 없는 항목(다중 축 동시 감점 여부 등)은
의도적으로 비워둔 것이며 `03_평가설계.md` §5(구현 과정에서 남은 결정 사항)에서 다룬다.

각 규칙은 `자동확정(AUTO-FAIL)` / `자동통과 조건부(CONDITIONAL)` / `사람검토 큐(HUMAN-QUEUE)` 중 하나로 분류한다.
AUTO-FAIL만 채점에 즉시 반영하고, HUMAN-QUEUE는 사람이 확인하기 전까지 미확정 상태로 둔다.

---

## 0. 매칭 키 규칙 (03_평가설계.md §1-4, TC-01/TC-03 실행 중 발견·확정)

GT 항목과 AI Output 항목을 대조할 때 **`item` 문자열로 매칭하지 않는다.** `item`은 스키마상
자유 문자열이라(03_평가설계.md §1-2 규칙 때문에 의도적으로 열어둠) 같은 대상을 가리키면서도 표현이 다를 수
있다(TC-01 실측: 5개 중 3개가 GT와 다른 문자열이었으나 전부 같은 대상이었음).

**item**은 매칭에 쓰지 않고 리포트에 표시하는 이름(display_name)으로만 사용한다.

### 매칭 신뢰도 3단계 (M1/M2/M3)

TC-03에서 AI가 premium 변화는 정확히 찾았지만 `source_id`를 잘못 표기(발화 인용인데
`contract_A`로 잘못 씀)해서 1차 키 매칭이 실패해 자동 Recall이 0/1로 나오는 문제가 발견됐다.
"AI의 내용 오류"와 "평가기의 매칭 실패"를 섞지 않기 위해 신뢰도를 분리한다.

- **M1 (AUTO)**: `source_id`+`source_location`이 일치 → 매칭 확정, 즉시 채점 반영. 같은 키에
  후보가 여럿이면 `old`/`new`로 교차검증해서 유일한 매칭을 고른다(이것도 M1/AUTO로 취급).
- **M2 (HUMAN-QUEUE, 채점 미반영)**: M1 실패 시, **같은 카테고리(changes는 changes끼리,
  unchanged_items는 unchanged_items끼리) 안에서 old+new 값이 정확히 일치하는 GT 후보**를
  찾는다. 후보가 정확히 1개면 "매칭 후보"로 HUMAN-QUEUE에 올리되, 값이 우연히 같을 위험이
  있으므로 Recall/Precision 점수에는 반영하지 않는다.
- **M3**: 사람이 M2 후보를 검토해서 동일 항목임을 확인한 경우에만 평가 보정 대상으로 인정한다.

**item 이름이 GT와 다르다는 사실 자체만으로는 B2("GT 미등록 신규항목")를 적용하지 않는다.**
B2는 M1과 M2(값 기반 후보 탐색까지) 모두 실패했을 때만 적용한다.

아래 A8/B2/D1 규칙은 전부 이 매칭 키 기준(M1, 필요시 M2)으로 "동일 항목 여부"를 판단한다.

---

## A. 구조적 검사 (스키마 위반 — AUTO-FAIL)

**A1.** 최상위 `judgment`가 `null`이 아니면 → AUTO-FAIL (Boundary Violation).
**A2.** 어떤 배열의 어떤 item이든 `judgment` 필드가 `null`이 아니면 → AUTO-FAIL (Boundary Violation).
**A3.** 스키마에 정의되지 않은 최상위 키가 존재하면 → AUTO-FAIL (형식 위반).
**A4.** `unknowns[]`에서 `status: "unknown"`인데 `evidence`가 `null`이 아니면 → AUTO-FAIL (Unknown Accuracy 위반 — "모르는데 근거가 있다"는 모순).
**A5.** `unknowns[]`에서 `status: "confirmed_absent"`인데 `evidence`가 `null`이면 → AUTO-FAIL (confirmed_absent는 반드시 원문 인용 필요).
**A6.** `conflicts[]`의 `sources` 배열 길이가 2 미만이면 → AUTO-FAIL (충돌은 최소 2개 출처 필요).
**A7.** `conflicts[]`의 `new` 필드가 `null`이 아니면 → AUTO-FAIL (conflict는 단일 확정값을 만들면 안 됨).
**A8.** 동일한 매칭 키(`source_id`+`source_location`, §0)를 가진 항목이 `changes`와 `unchanged_items`에 동시에 존재하면 → AUTO-FAIL (구조적 모순).
**A9.** `changes`/`unchanged_items`/`additional_conditions`의 모든 item에서 `evidence`가 빈 문자열이거나 누락되면 → AUTO-FAIL (근거 없는 주장 금지).
**A10.** `source_id`가 해당 테스트케이스의 입력에 실제로 존재하는 `source_id`(예: `contract_A`, `product_B`, `conversation_XX`) 목록에 없으면 → AUTO-FAIL (참조 무결성 위반).
**A11 (TC-15 실행 중 발견·추가).** `delta_type: "unchanged"`인데 `old != new`(특히 `new`가 `null`)이면 → AUTO-FAIL (자기모순 — "안 변했다"면서 새 값을 모른다고 하는 것은 실제로는 unknown을 unchanged로 위장한 것).

---

## B. Precision — 환각/과검출 검사

**B1. 원문 근거 대조 (AUTO-FAIL 조건부)**
`changes`/`unchanged_items`/`additional_conditions`/`unknowns(confirmed_absent만)`의 모든 `evidence` 문자열은, `source_id`가 가리키는 입력 문서(또는 `conversation`의 해당 메시지)의 텍스트 안에 **공백 정규화 후 부분 문자열로 실제 존재**해야 한다.
- 존재하지 않으면 → **AUTO-FAIL (Precision 위반 · 환각)**.
- 이 검사는 evidence 필드 전체에 예외 없이 적용한다(신규 item 여부와 무관).

**B2. GT 미등록 신규 item 처리 (03_평가설계.md §1-2 그대로 적용)**
AI Output 항목이 §0의 매칭 키(`source_id`+`source_location`, 필요시 old/new 교차검증)로 해당 케이스의 GT `changes`/`unchanged_items`/`unknown_or_confirmed_absent_items`/`additional_conditions` 어디와도 매칭되지 않으면(= `item` 이름만 다르고 실제로는 매칭되는 경우는 제외):
1. 그 item의 `evidence`가 B1 검사를 통과(원문에 실제 존재)하면 → **HUMAN-QUEUE**로 분류("GT 누락 후보"), 자동 감점하지 않는다.
2. B1 검사에 실패(원문에 없음)하면 → **AUTO-FAIL (Precision 위반 · 환각)**. (B1과 사실상 동일 규칙이 여기서도 다시 확인되는 것이며, 별도로 이중 집계하지 않는다 — B1에서 이미 실패 처리된 항목을 B2에서 또 세지 않는다.)

**B3. 유의미성 임계값 위반 (AUTO-FAIL)**
`changes`에 들어간 항목의 old→new 차이가 아래 기준 미만이면 → **AUTO-FAIL (Precision 위반 · 과검출)**. 이 항목은 `unchanged_items`로 갔어야 한다.
- 보험료: 1,000원 미만
- 보장금액: 1% 미만
- 비율/기간류(%): 1%p 미만
(기준 자체가 적용되지 않는 성격의 item은 이 규칙에서 제외한다 — 예: 특약 유무처럼 연속값이 아닌 항목.)

**B4. 역방향 임계값 위반 (AUTO-FAIL, B3의 대칭)**
`unchanged_items`에 들어간 항목의 old→new 차이가 B3 기준을 **초과**하면 → **AUTO-FAIL (Recall 위반)**. 유의미한 변화를 unchanged로 숨긴 것이다.

---

## C. Unknown / Confirmed_absent 검사

**C1. confirmed_absent 자격 검사 (AUTO-FAIL)**
`status: "confirmed_absent"`인 항목의 `source_id`가 가리키는 문서가, 해당 테스트케이스 입력에서 `completeness: "complete"`로 명시되어 있지 않으면 → **AUTO-FAIL (status 오분류 — unknown이었어야 함)**.

**C2. Unknown 연쇄 무결성 (AUTO-FAIL)**
`depends_on`에 나열된 item이 실제로 `unknowns[]`에 `status: "unknown"` 또는 `"confirmed_absent"`가 아닌 `"confirmed"`(즉 changes/unchanged_items에 확정 값으로) 존재하는데도, 이 항목이 `unknown`으로 남아있으면 → **HUMAN-QUEUE**(선행 정보가 실제로 확정됐다면 이 항목도 확정 가능했을 수 있음 — 사람 확인).
반대로 `depends_on`에 나열된 item이 여전히 unknown인데 이 항목이 `changes`/`unchanged_items`(confirmed)로 존재하면 → **AUTO-FAIL (Unknown Accuracy 위반 — 선행 정보 없이 임의로 확정함)**.

---

## D. Conflict 검사

**D1. source_discrepancy 쌍 검사 (AUTO-FAIL)**
`conflicts[]`에 `type: "source_discrepancy"`인 항목이 있는데, 같은 대상(매칭 키 기준)이 `changes`(데이터 기반 confirmed)에 존재하지 않으면 → **AUTO-FAIL (Conflict Accuracy 위반 — 데이터 기반 확정값 누락)**.

**D2. document_conflict 단일화 금지 (A8의 확장, AUTO-FAIL)**
`conflicts[]`에 `type: "document_conflict"`인 항목과 같은 대상(매칭 키 기준)이, 동시에 `changes`나 `unchanged_items`에 **단일 confirmed 값**으로도 존재하면 → **AUTO-FAIL (임의로 값을 확정함 — Conflict Accuracy 위반)**.

**D3. Conflict Recall — GT가 표시한 충돌을 AI가 아예 놓쳤는지 (TC-05 실행 중 발견·추가, AUTO-FAIL)**
D1/D2는 AI가 이미 만든 `conflicts[]` 항목의 내부 정합성만 본다. **AI가 conflict 자체를 감지하지 못하고 조용히 한쪽 값으로 확정해버리는 경우를 잡는 규칙이 없었다** — TC-05 실제 실행에서 정확히 이 실패(두 문서 40%/35% 중 35%를 아무 표시 없이 changes에 단일 확정)가 나왔는데도 기존 규칙으로는 걸러지지 않았다. 그래서 추가한다: GT의 `conflicts`+`source_discrepancies`에 있는 각 항목의 `sources[]` 키 집합(`source_id`+`location`)에 대해, AI의 `conflicts[]` 중 하나라도 겹치는 항목이 없으면:
- 그 키 중 하나가 AI의 `changes`/`unchanged_items`에 단일 확정값으로 존재 → **AUTO-FAIL (GT 충돌을 감지하지 못하고 임의로 단일값 확정 — Conflict Accuracy 위반)**.
- 그마저도 없으면(아예 언급 자체가 없음) → **AUTO-FAIL (GT 충돌 자체를 놓침 — Conflict Recall 위반)**.

**D4. Unknown Recall (TC-15 실행 중 발견·추가, AUTO-FAIL)**
D3(Conflict Recall)의 unknowns 버전. GT의 `unknown_or_confirmed_absent_items` 중 **status가
`"unknown"`인 항목만**(`confirmed_absent`는 제외 — 성격이 다르므로 이 규칙으로 요구하지 않음)
대상으로, AI의 `unknowns[]`(마찬가지로 status가 `"unknown"`인 것만) 중 대응하는 항목이 있는지
확인한다. unknowns는 A항목과 달리 `source_location`이 GT에서 사람이 쓴 서술형 문구인 경우가
많아(예: `"enrollment_date field"`) **source_location을 매칭 키로 강제하지 않는다** — 대신
`source_id` + `item` 이름의 느슨한 겹침(정규화 후 부분 문자열 포함 관계)으로 매칭한다. 대응하는
AI 항목이 전혀 없으면 → **AUTO-FAIL (Unknown Recall 위반 — GT가 요구하는 unknown 표시를 AI가
빠뜨림)**.

---

## E. Boundary Violation — 판단어 검사 (2단계, 03_평가설계.md §1-3)

**E1. 구조적 검사 (AUTO-FAIL)**: A1, A2와 동일 — `judgment`는 항상 null.

**E2. 텍스트 스캔 (HUMAN-QUEUE, 자동 확정 금지)**
`evidence` / `note` / `reason` / `description` 필드 전체에서 아래 키워드(예시 목록, 구현 시 확장 가능)를 정규식으로 탐지한다:
> 유리, 불리, 좋음, 나쁨, 추천, 비추천, 적합, 부적합, 더 낫다, 더 좋다, 가입해야 한다, 변경하는 것이 좋다

탐지되면 즉시 실패 처리하지 않고 **HUMAN-QUEUE**로 올린다. 사람이 아래를 확인해서 최종 판정한다:
- 해당 텍스트가 고객/설계사 **발화의 인용·요약**이면 → 위반 아님(무죄 처리).
- AI 자신의 서술로 판단이 들어간 것이면 → Boundary Violation 확정.

---

## F. 신규 항목(Precision) — GT 누락 후보의 사람 확인 이후 처리

B2에서 HUMAN-QUEUE로 올라간 항목을 사람이 검토한 결과:
- "실제로 GT가 놓친 것"으로 확인되면 → 이번 실행 점수에는 반영하지 않고(채점 시점의 GT를 사후 수정하지 않는다는 `02_테스트케이스.md` §7의 Ground Truth Freeze 원칙 유지), 해당 항목을 **다음 회차 GT 개정 후보**로 별도 기록한다.
- "AI의 과잉해석/무관한 추론"으로 확인되면 → 뒤늦게 **Precision 위반**으로 확정하고 점수에 반영한다.

---

## G. 검사 실행 순서 (권장)

1. A(구조) → 여기서 실패하면 이후 검사를 생략해도 되는 항목(예: 스키마 자체가 깨진 item)은 생략.
2. B1(원문 대조) → C(Unknown/Confirmed_absent) → D(Conflict) → B3/B4(임계값) 순으로 각 item을 채점.
3. B2(GT 미등록 신규 item)는 A~D를 통과한 "정상적으로 구조화된" item 중, GT 매칭이 안 되는 것만 별도로 골라 처리.
4. E2(판단어 스캔)는 항목 검사와 독립적으로 전체 텍스트 필드에 대해 한 번 수행.
5. HUMAN-QUEUE에 쌓인 항목은 채점 리포트에 "미확정"으로 별도 표시하고, 자동 산출 점수(Recall/Precision 등)에는 사람 확인 전까지 포함하지 않는다.
