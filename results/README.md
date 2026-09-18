# results/ 폴더 구조 — Original / Corrected / Evaluation 식별자

2차 피드백(2026-09-18): "원본·교정본·평가 결과가 구분되도록 실행 식별자나 파일명을
정리해 주시면 다른 동료가 훨씬 쉽게 재현할 수 있습니다." 이 문서는 그 대응이다.

## 폴더별 의미

| 폴더 | 내용 | 만드는 방법 |
|---|---|---|
| `structured/` | **Original** — LLM이 실제로 생성한 구조화 출력. `src/llm_extractor.py TC-XX`로 생성 | `TC-XX.json` |
| `corrected/` | **Corrected** — 사람이 원본을 직접 수정·확정한 결과 (현재 TC-05만 존재) | 수기 편집 |
| `regression_fixtures/` | 실제 모델 호출 없이 손으로 만든 **합성 fixture** — 평가기(evaluate.py) 자체의 버그를 재현·검증하기 위한 것. 실제 AI 출력이 아니다 | 수기 작성, `_fixture_note` 필드에 목적 명시 |
| `metadata/` | **Evaluation** — `src/evaluate.py`가 위 세 종류 중 하나를 평가한 결과 | 아래 파일명 규칙 참고 |

## `metadata/`의 파일명이 곧 "무엇을 평가했는지"를 말한다

`evaluate.py <CASE_ID> [ai_output_path]`를 실행하면:

- **두 번째 인자를 생략**하면 `results/structured/<CASE_ID>.json`(Original)을 평가하고,
  결과를 `metadata/<CASE_ID>_eval.json`으로 저장한다.
- **두 번째 인자로 다른 경로**(예: `results/corrected/TC-05.json`)를 주면, 그 파일의
  **상위 폴더명을 파일명 앞에 붙여** `metadata/<상위폴더>_<원본파일명>_eval.json`으로
  저장한다. 그래서 같은 `TC-05.json`이라는 이름이라도 evaluation 결과가 절대 서로
  덮어쓰지 않는다.

| 평가 대상 | 명령 | 저장되는 evaluation 파일 |
|---|---|---|
| Original (TC-05) | `evaluate.py TC-05` | `metadata/TC-05_eval.json` |
| Corrected (TC-05) | `evaluate.py TC-05 results/corrected/TC-05.json` | `metadata/corrected_TC-05_eval.json` |
| Regression fixture | `evaluate.py TC-05 results/regression_fixtures/D2_true_positive_same_item.json` | `metadata/regression_fixtures_D2_true_positive_same_item_eval.json` |

이 규칙 자체는 Phase 8(`results/evaluator_validation_log.md` 참고, 2026-09-16)에서
원본/교정본 평가 결과가 파일명 충돌로 뒤섞였던 재현성 버그를 고치면서 이미 도입했다. 이
README는 새로 만든 것이 아니라, 이미 있던 규칙을 팀이 바로 알아볼 수 있게 문서화한 것이다.

## 기타

- `structured/TC-01_v1.json` — TC-01의 첫 번째 prompt 버전 결과물. 현재 채택된 버전은
  `TC-01.json`(v2)이며, v1은 `results/tc01_iteration_log.md`에 기록된 반복 개선 과정의
  증거로 남겨둔 것이다.
- 평가기 자체의 결함 9건 + D1/D2 항목 식별 버그 수정 기록은 `evaluator_validation_log.md`,
  naive/structured/third-baseline 비교는 `naive_vs_structured_recall_reanalysis.md`,
  `instructed_freeform_human_review.md`를 참고.
