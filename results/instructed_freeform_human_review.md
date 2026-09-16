# 세 번째 baseline: "지침 동일 + 자유서술" 사람 평가 (Phase 10)

`src/instructed_freeform_baseline.py`로 structured와 **동일한 근거·충돌·판단경계 지침**
(`prompt/instructed_freeform_prompt.md`)을 주되 스키마/함수호출 강제 없이 자유 텍스트로 받은
결과를, naive·structured와 같은 5개 held-out 케이스(TC-03, 05, 10, 11, 15)로 비교했다.

**held-out 선정 이유**: 프롬프트를 실제로 수정한 것은 TC-01뿐이었다(v1→v2, 배열
라우팅 버그 수정). TC-01/04는 튜닝·평가기 버그 발견에 쓰였으므로 제외하고, unknown(TC-03)·
conflict(TC-05)·confirmed_absent/정밀도(TC-10)·B항목 recall(TC-11)·복합 실패(TC-15) 5개 축을
그대로 커버하는 나머지 5건을 그대로 썼다 — 새로 고른 것이지 유리한 것만 고른 게 아니다.

✅=충족 / ❌=실패 / △=부분적 / N/A=해당 없음. naive 열은 `results/naive_baseline_human_review.md`
값을 그대로 가져옴(같은 사람, 같은 기준, 같은 GT 대조).

## TC-03 (unknown 처리)

| 기준 | Naive | Instructed-freeform | Structured(자동채점) |
|---|---|---|---|
| ①변경사항 발견 | ✅ | ✅ 95,000→88,000 정확 | Recall 0/1 (M2 tier — source_id 오귀속, 자동점수 미반영, HUMAN-QUEUE) |
| ②방향·값 정확 | ✅ | ✅ | 값 자체는 맞음(M2로 확인됨) |
| ③근거 명시 | ❌ | △ 출처 라벨은 있으나 원문 그대로의 인용은 약함 | Evidence 100% 원문 존재 |
| ④추론 안 함 | ✅ | ✅ "세부 내용 불완전, 확인 필요"로 정직하게 처리 | 환각 0건 |
| ⑤충돌 보존 | N/A | N/A | N/A |
| ⑥유불리 미판단 | ❌ | ✅ 평가어 없음 | E2 0건 |

## TC-05 (document conflict)

| 기준 | Naive | Instructed-freeform | Structured(자동채점) |
|---|---|---|---|
| ①변경사항 발견 | ✅ | ✅ | Recall 1/1 |
| ②방향·값 정확 | △ 두 값 다 언급했으나 충돌 인식 못함 | ✅ **"상태: Conflict"로 명시적 분류, 40%/35% 모두 보존** | (이번 실제 실행에서는 AI가 35%로 임의 확정 → D3 AUTO-FAIL, `results/structured/TC-05.json`) |
| ③근거 명시 | △ | ✅ 두 문서 원문 그대로 인용("10년 시점 해지환급률 약 40%." / "...35%로 한다.") | Evidence 100% |
| ④추론 안 함 | N/A | ✅ | — |
| ⑤충돌 보존 | ❌ 순차적 사실처럼 오인 | ✅ **성공** | ❌ 이번 실행에서 놓침(D3) — Human Review로 사람이 수정 |
| ⑥유불리 미판단 | ❌ "더 유리할 수 있습니다" | ✅ | E2 0건 |

**주의**: 이 케이스는 instructed-freeform이 structured의 실제 출력보다 conflict를 더 잘
처리한 유일한 사례다. 다만 이건 LLM 샘플링 1회 결과이지 "스키마가 없는 게 낫다"는 결론이
아니다 — structured도 다른 샘플링에서는 conflict를 정확히 잡을 수 있고, instructed-freeform도
다른 샘플링에서는 놓칠 수 있다. 이 결과가 보여주는 건 "conflict 처리 성공은 스키마보다
**지침 자체(§3의 명시적 판단 순서)**에 더 크게 의존한다"는 가설이지, 확정된 결론이 아니다.

## TC-10 (confirmed_absent)

| 기준 | Naive | Instructed-freeform | Structured(자동채점) |
|---|---|---|---|
| ①변경사항 발견 | ✅ | ✅ 90,000→82,000 정확 | Recall 1/1 |
| ②방향·값 정확 | ✅ | ✅ | ✅ |
| ③근거 명시 | △ | ✅ full_feature_list 원문 그대로 인용, completeness 언급 | Evidence 100% |
| ④추론 안 함 | ❌ 기존계약에 "무사고할인 없음"을 원문에 없는데 추정 | ✅ **"기존 계약에서는... 확인 가능하지 않음"으로 정직하게 처리 — naive의 환각을 재현하지 않음** | 환각 0건 |
| ⑤충돌 보존 | N/A | N/A | N/A |
| ⑥유불리 미판단 | ✅ | ✅ | E2 0건 |

## TC-11 (보장금액 동일·진단기준 축소, 니즈 연결)

| 기준 | Naive | Instructed-freeform | Structured(자동채점) |
|---|---|---|---|
| ①변경사항 발견 | ✅ B항목까지 포착 | ✅ 진단기준 축소까지 정확히 포착 | Recall 2/2 |
| ②방향·값 정확 | ✅ | ✅ | ✅ |
| ③근거 명시 | △ | △ 출처 라벨은 있으나 부분 인용 | Evidence 100% |
| ④추론 안 함 | N/A | N/A | — |
| ⑤충돌 보존 | N/A | N/A | N/A |
| ⑥유불리 미판단 | ❌ "기존 계약이 더 포괄적" 명시 비교 | △ "이 점은 손해를 볼 수 있는 부분입니다" — naive보다는 약하지만 여전히 평가적 프레이밍 | E2 0건 |

## TC-15 (복합 케이스: Critical 삭제 + source_discrepancy + 다중 unknown)

| 기준 | Naive | Instructed-freeform | Structured(자동채점) |
|---|---|---|---|
| ①변경사항 발견 | **❌ Critical 항목(뇌심혈관 삭제) 완전 누락, 가입일자 B항목도 누락** | **✅ Critical 항목(특약 삭제) 캐치**: "다른 특약(뇌혈관질환·급성심근경색)은 목록에 없다는 점이 확인되어 삭제된 것으로 판단" / △ enrollment_date·existing_contract_dissolution_impact(연쇄 unknown 2건)는 언급 없음 — 부분 성공 | Recall 3/4 (B4: 1건 배치 오류로 기록됨) |
| ②방향·값 정확 | ✅(잡은 것에 한해) | ✅ 잡은 항목들은 정확 | ✅(잡은 항목) |
| ③근거 명시 | ❌ | △ 출처 라벨 있음, 부분 인용 | Evidence 100% |
| ④추론 안 함 | ✅ | ✅ 면책조항을 확정 대신 unknown으로 정직하게 처리 | A11/D4로 자기모순·unknown누락 자동검출 |
| ⑤충돌 보존 | ❌ 상해보장 관련 설계사 오안내 전혀 지적 안 함 | △ **"그대로입니다"라고 답변했으나... 명시된 바 없어 주의 필요"로 의심은 제기하지만, 데이터 기반 축소(1,000만→500만)를 확정하지 못함 — GT가 요구하는 "확정+불일치 별도표시" 중 확정 쪽을 놓침** | ❌ 실제 실행에서 D3 위반(이 유형도 놓침, `results/evaluator_validation_log.md` TC-15 절 참고) |
| ⑥유불리 미판단 | △ 약한 평가적 프레이밍 | △ "고객의 니즈에 부합하지 않는 변경사항입니다" — 니즈 매칭 서술이지만 다소 평가적 | E2 0건 |

## 종합

**가장 중요한 발견**: TC-05(conflict 명시적 분류)와 TC-10(환각 안 함)에서 instructed-freeform은
naive의 실패를 반복하지 않았고, TC-15에서는 naive가 완전히 놓친 Critical 항목(특약 삭제)까지
잡아냈다. 즉 **naive가 실패했던 지점의 상당 부분은 "스키마가 없어서"가 아니라 "지침(근거 인용
규칙, conflict/unknown 판단 순서, 판단경계 금지)이 없어서"였을 가능성이 크다.**

**스키마가 여전히 추가로 기여하는 부분**: (a) 자동 채점 가능성 — naive/instructed-freeform은
사람이 매번 원문과 대조해서 읽어야 하지만, structured는 `evaluate.py`로 기계적·재현 가능하게
채점된다(이번 5건도 사람이 직접 다 읽어야 했다). (b) 필드 단위 강제 — instructed-freeform도
지침을 어느 정도 잘 따르지만 매 항목마다 원문 그대로의 인용, source_id, source_location을
빠짐없이 채우는 것까지는 강제되지 않는다(③근거명시에서 naive보다는 낫지만 structured의
"Evidence 100%"만큼 일관되지는 않음). (c) TC-11/15의 ⑥에서 보듯, 스키마의 `judgment: null`
강제 + E2 텍스트 스캔이 있는 structured 쪽이 판단경계 준수에서 여전히 더 일관적이다.

**과장하지 않을 것**: 5건, 1회 샘플링 결과다. 특히 TC-05는 instructed-freeform이 이례적으로
잘한 경우라 일반화하면 안 된다. "지침이 핵심이고 스키마는 부가적"이라고 단정하기보다는,
"이번 5건에서는 지침의 기여가 관찰 가능한 수준으로 컸고, 스키마의 추가 기여는 주로 자동
검증 가능성과 필드 일관성 쪽에서 나타났다"고 표현하는 게 정확하다.
