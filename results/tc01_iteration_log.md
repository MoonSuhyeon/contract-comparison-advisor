# TC-01 v1 → v2 반복 기록

Phase 1(AI 기능 구현)에서 실제로 발견한 첫 번째 구조적 오류와 그 수정 과정. `PLAN.md` Phase 5에서
"실제 오류 발견 → 개선 → Before/After" 사례로 재사용한다.

## v1 (모델: gpt-4o-mini, 1회 시도, 스키마 검증 통과)

원문/GT 대조 결과:

| 항목 | GT | v1 delta 값 | v1이 넣은 배열 | 배열 정확? |
|---|---|---|---|---|
| premium | decrease | decrease | changes | ✅ |
| coverage_amount_cancer | unchanged | unchanged | **changes** | ❌ (unchanged_items여야 함) |
| coverage_amount_cerebro_cardiac | removed | removed | **unchanged_items** | ❌ (changes여야 함) |
| renewal_period | shortened | shortened | **unchanged_items** | ❌ (changes여야 함) |
| surrender_value | decrease | decrease | **unchanged_items** | ❌ (changes여야 함) |

**핵심 발견**: 4개 항목 모두 `old`/`new`/방향(당시 필드명 `change`)/evidence 값은 100% 정확했다.
그런데 4개 중 3개가 정반대 배열에 들어갔다. 즉 **비교·추출 능력은 정상, 최상위 배열 라우팅만
실패**했다.

**원인 가설**: 항목 내부 필드명이 `change`이고 최상위 배열명이 `changes`라서, 모델이 "이 항목에
`change` 필드가 있으니 `changes` 배열에 넣자"는 식으로 배열 선택 기준을 필드 존재 여부와
혼동했을 가능성이 높다(필드 값 자체가 아니라 필드 이름의 문자열 유사성에 이끌린 오류).

## 결정: A안(강화판) 채택, B안(단일 배열 comparisons) 보류

B안(changes/unchanged_items를 comparisons 하나로 합치고 delta 값으로 사후 분리)이 이 실패
유형을 구조적으로 원천 차단하지만, 이미 확정된 평가 설계(`03_설계.md` §3: changes=
Recall 분모, unchanged_items=Precision 과검출 체크포인트)를 함께 흔든다. 첫 실측 오류 1건으로
확정된 평가 설계까지 바꾸는 건 성급하다고 판단해 보류한다. 대신:

1. 필드명 `change` → `delta_type`으로 변경 (`schema/output_schema.json`, `examples/expected_outputs_by_case.json`) — 배열명과의 문자열 충돌 제거. GT 파일(`data/tc0X_data.json`)의 `change` 필드는 그대로 둔다(GT는 건드리지 않는다는 원칙 유지) — 평가기 구현 시 `delta_type`(AI Output) ↔ `change`(GT)를 코드에서 매핑한다.
2. `prompt/system_prompt.md` §5-1 신설: "배열 배치는 오직 delta_type 값으로만 결정한다"는 명시적 규칙 + 제출 전 5단계 자체검사 절차 추가.
3. TC-01 재실행(v2)해서 배열 라우팅이 실제로 고쳐지는지 확인. 안 고쳐지면 그때 B안 재검토.

## v2 결과 (채택, 최종)

| 항목 | GT | v2 delta_type | v2가 넣은 배열 | 배열 정확? |
|---|---|---|---|---|
| premium | decrease | decrease | changes | ✅ |
| coverage_amount_cancer | unchanged | unchanged | unchanged_items | ✅ |
| coverage_amount_cerebro_cardiac | removed | removed | **unchanged_items** | ❌ (changes여야 함) |
| renewal_period | shortened | shortened | changes | ✅ |
| surrender_value | decrease | decrease | changes | ✅ |

4개 실질 변화 중 3개(premium, renewal_period, surrender_value)의 배열 라우팅이 정확해졌다.
delta_type 필드명 변경 + 5-1 명시 규칙 + 제출 전 자체검사 절차가 실제로 효과가 있었다.

**잔여 오류 1건**: `delta_type: "removed"`인 뇌심혈관 항목이 여전히 `unchanged_items`에 남았다.
방금 추가한 5-1 규칙("delta_type != unchanged면 반드시 changes")을 직접 위반한 사례다.

**원인은 확정하지 않고 가설로만 남긴다**: removed와 confirmed_absent의 의미적 유사성이 배열
라우팅에 영향을 미쳤을 가능성이 있으나, TC-01 한 건만으로 원인을 단정할 수 없다.

## 결정: v2를 채택하고 v3는 만들지 않는다

이유:
1. 프롬프트 보강의 효과는 이미 실측으로 확인됐다(4개 중 3개 해결). 여기서 "removed vs
   confirmed_absent 구분"을 한 줄 더 추가해 v3를 만드는 것은 "프롬프트를 계속 수정하면
   해결된다"는 가정을 검증하는 별도의 실험이 되며, 이번 프로젝트의 핵심 질문(AI 오류를 어떻게
   발견·통제하는가)에서 벗어난다.
2. 오류가 완전히 없어질 때까지 프롬프트를 계속 고치는 것은 지적 정직성 측면에서도 바람직하지
   않다 — "몇 번 수정했는지"가 아니라 "남은 오류를 어떻게 감지하고 처리하는가"가 이 프로젝트의
   메시지다.
3. 이 잔여 오류(유의미한 변화가 unchanged_items에 들어감)는 정확히 `schema/validation_rules.md`의
   **B4(unchanged_items 안에 GT 기준 유의미한 변화가 있으면 자동 Recall 위반)**가 잡도록 설계된
   패턴이다. 스키마 검증 통과 → 평가기의 Recall 위반 탐지로 이어지는 흐름을 실제로 보여줄 수
   있는 좋은 실증 사례로 그대로 남긴다.

**다음**: Phase 2(evaluate.py)에서 이 TC-01 v2 결과를 GT와 대조해, B4가 실제로 이 오류를
자동으로 잡아내는지 확인한다.

