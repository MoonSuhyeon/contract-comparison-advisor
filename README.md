# Contract Comparison Advisor

## 문제정의

기존 보험계약을 신규 상품으로 바꿀 때, 보장·지급조건·갱신·환급금처럼 눈에 잘 띄지 않는
조건의 변화를 놓치면 고객에게 불리한 결과로 이어질 수 있습니다. 금융위원회도 GA(법인보험대리점)의
이러한 "중요사항 비교 미고지"를 반복되는 불완전판매 문제로 지적한 바 있습니다.

따라서 이 프로젝트에서는 기존 계약과 신규 계약의 차이를 AI가 먼저 찾아주고, 설계사가
그 결과를 확인·수정할 수 있도록 하는 계약 비교 프로세스를 만들었습니다.

규제·통계 근거는 [`01_문제정의.md`](01_문제정의.md)에서 확인할 수 있습니다.

## 해결방법

기존에는 설계사가 기존 계약과 신규 계약을 직접 비교하며 변경사항을 찾아야 했습니다. 이를
AI가 먼저 비교하고 사람이 검토하는 방식으로 바꿨습니다.

```
기존 계약 + 신규 계약 + 고객 상담
                ↓
        AI가 계약 차이 비교
                ↓
   변경사항 · 근거 · 고객 니즈 추출
                ↓
       Unknown · Conflict 분리
                ↓
       사람이 확인·수정·확정
```

AI는 다음 정보를 구조화해 제공합니다.

- **changes** — 기존·신규 계약에서 달라진 항목
- **unchanged_items** — 변경되지 않은 항목
- **evidence** — 변경사항을 확인할 수 있는 원문 근거
- **customer_needs / linked_need_id** — 고객이 중요하게 말한 내용과 관련된 계약 변화
- **unknowns** — AI가 확정하지 못한 정보
- **conflicts** — 계약서나 출처 간 충돌하는 정보

이를 통해 설계사는 계약서 전체를 처음부터 비교하기보다, AI가 찾아낸 차이와 근거를 중심으로
확인하고 수정하는 방식으로 계약 비교 업무를 수행할 수 있습니다. 최종 판단은 항상 사람이
하도록 역할을 나눴습니다 — AI가 비교·고지 의무를 대신하면 안 된다는 `01_문제정의.md`의
문제의식과 같은 이유입니다.

### AI 결과가 실제로 검증 가능한지도 함께 확인했습니다

테스트 케이스 15개(Ground Truth 포함)를 설계하고, 그중 7개를 structured 파이프라인과
naive 프롬프트로 각각 실행해 비교했습니다.

변화를 찾아내는 능력 자체에서는 두 방식의 큰 차이가 없었지만, structured 방식에서는
변경사항·근거·충돌·미확인 정보를 각각 구조화해 사람이 확인할 수 있도록 만들었습니다.
또한 평가기(`src/evaluate.py`) 자체도 검증하는 과정에서 9건의 버그를 찾아 수정했습니다.

Ground Truth가 없는 실제 신규 계약에서도 활용할 수 있도록, LLM이나 Ground Truth에
의존하지 않고 원문 간 충돌을 탐지하는 `conflict_detector.py`와 사람이 결과를 확인·수정하는
검토 화면(`src/review_app.py`)도 구현했습니다.

### 이 프로세스가 실제 작업량을 줄이는지도 자기실험으로 확인했습니다

검토 화면을 만드는 데서 그치지 않고, 실험자 1인이 7개 케이스를 "AI 없이 직접 작성(조건 A)"과
"AI 초안 검토·수정(조건 B)" 두 방식으로 모두 처리하는 14세션을 실행했습니다(2026-09-18).
AI 초안이 있을 때 작업시간이 평균 75.6% 줄었습니다. 다만 이건 실험자 1인의 자기실험
(N=7)에서 측정한 시간 결과이지, "AI가 사람보다 더 잘한다"는 주장은 아닙니다 — conflict를
사람이 놓친 사례 등 함께 발견한 한계는 `05_업무효과검증_설계.md` §7과
`results/work_effect/trial_log.md`에 그대로 기록했습니다.

자세한 비교 결과와 평가기 버그 9건, GT 없이 수행한 conflict 탐지, 세 번째 baseline 검증,
14세션 업무 효과 실험 전체 기록은 [`06_종합정리.md`](06_종합정리.md),
[`04_검증결과.md`](04_검증결과.md), [`05_업무효과검증_설계.md`](05_업무효과검증_설계.md),
[`results/evaluator_validation_log.md`](results/evaluator_validation_log.md),
[`results/work_effect/trial_log.md`](results/work_effect/trial_log.md)에서 확인할 수
있습니다.

## 실행 방법

### 0. 준비물
- Python 3.10 이상
- OpenAI API 키 (구조화 파이프라인·naive baseline 모두 `gpt-4o-mini` 사용, `.env`로만 주입 — 키를 코드나 커밋에 직접 넣지 않음)

### 1. 설치
```bash
git clone https://github.com/MoonSuhyeon/contract-comparison-advisor.git
cd contract-comparison-advisor

python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS/Linux

cp .env.example .env
# .env를 열어서 OPENAI_API_KEY=sk-... 채우기
```

### 2. 실행 가능한 테스트 케이스
전체 15개(`data/tc01~15_data.json`) 중 실제로 실행·평가까지 완료한 건 **7개**입니다:
`TC-01 TC-03 TC-04 TC-05 TC-10 TC-11 TC-15` (나머지 8개는 설계·GT만 완성된 상태 — 이유는
[`06_종합정리.md`](06_종합정리.md) §5 참고).

### 3. 케이스 1개 실행 (예: TC-01)
```bash
# 구조화 파이프라인: 시스템 프롬프트 + JSON 스키마 강제 + 재시도
.venv/Scripts/python src/llm_extractor.py TC-01
# -> results/structured/TC-01.json

# naive baseline: 스키마 없이 자유 텍스트 (비교 기준)
.venv/Scripts/python src/naive_baseline.py TC-01
# -> results/baseline/TC-01.txt

# 구조화 결과를 Ground Truth와 자동 대조 채점 (Recall/Precision/Evidence/Unknown/Conflict/Boundary)
.venv/Scripts/python src/evaluate.py TC-01
# -> 콘솔 출력 + results/metadata/TC-01_eval.json
```

### 4. 실행 완료된 7건 한 번에 재현
```bash
for tc in TC-01 TC-03 TC-04 TC-05 TC-10 TC-11 TC-15; do
  .venv/Scripts/python src/llm_extractor.py "$tc"
  .venv/Scripts/python src/naive_baseline.py "$tc"
  .venv/Scripts/python src/evaluate.py "$tc"
done
```
(bash 기준. Windows PowerShell에서는 `foreach ($tc in "TC-01","TC-03","TC-04","TC-05","TC-10","TC-11","TC-15") { ... }` 형태로 바꿔서 실행)

### 5. 특정 파일을 지정해서 평가 (원본/교정본/회귀 fixture 재현)
```bash
.venv/Scripts/python src/evaluate.py TC-05                                              # 원본
.venv/Scripts/python src/evaluate.py TC-05 results/corrected/TC-05.json                 # 사람이 교정한 버전
.venv/Scripts/python src/evaluate.py TC-05 results/regression_fixtures/TC-05_corrupted_value.json  # 값 위조 회귀 fixture
```

### 6. GT 없는 Conflict 탐지 (LLM·GT 미사용)
```bash
.venv/Scripts/python src/conflict_detector.py TC-05
# -> results/conflict_detection/TC-05.json
```

### 7. 세 번째 baseline (지침 동일 + 자유서술)
```bash
.venv/Scripts/python src/instructed_freeform_baseline.py TC-05
# -> results/instructed_freeform/TC-05.txt
```

### 8. 업무 효과 검토 UI (Streamlit)
```bash
.venv/Scripts/python -m streamlit run src/review_app.py
```
AI가 만든 비교 초안(실행 완료된 7개 케이스 전부: TC-01·TC-03·TC-04·TC-05·TC-10·TC-11·TC-15)을
화면에서 직접 확인·수정·추가해 최종 결과를 확정하는 검토 도구입니다. Ground Truth는 이
화면에 절대 노출되지 않고, "최종 확정"을 누르면 소요 시간과 수정·추가 항목 수가
`results/work_effect/app_logs/`에 자동 기록됩니다(`05_업무효과검증_설계.md` §8에서 정의한
검토 화면의 구현체). 이 UI로 2026-09-18에 7개 케이스 × 2조건(AI 없이 직접 작성 / AI 초안
검토) = 14세션을 실제로 실행했고, 결과는 `results/work_effect/trial_log.md`에 있습니다.

### 9. 결과 확인
| 무엇을 보려면 | 어디를 보면 되는가 |
|---|---|
| 구조화 파이프라인이 실제로 낸 JSON | `results/structured/TC-XX.json` |
| naive baseline이 낸 자유 텍스트 | `results/baseline/TC-XX.txt` |
| 자동 채점 결과(Recall/Precision 등 수치 + 위반 목록) | `results/metadata/TC-XX_eval.json` |
| naive 7건을 사람이 직접 대조한 정성 평가 | `results/naive_baseline_human_review.md` |
| 평가기(`evaluate.py`) 자체를 개발하며 발견한 버그·한계 전체 | `results/evaluator_validation_log.md` |
| Human Review로 사람이 직접 수정한 사례(TC-05) | `results/corrected/TC-05.json` |
| GT 없이 문서만으로 탐지한 conflict 후보 + Human Review | `results/conflict_detection/TC-05.json`, `results/conflict_detector_log.md` |
| 세 번째 baseline(지침 동일+자유서술) 3방향 비교 | `results/instructed_freeform_human_review.md` |
| 검토 UI에서 "최종 확정"으로 저장한 세션별 원본 로그 | `results/work_effect/app_logs/TC-XX_조건_실행ID.json` |
| 14세션 집계·GT 대조·해석(작업시간 75.6%↓, 오확정 방지 0/3) | `results/work_effect/trial_log.md` |

## 폴더 구조

```
contract-comparison-advisor/
├── 01_문제정의.md              # 문제 정의 + 규제 근거
├── 02_테스트케이스.md          # 15개 테스트 케이스 설계
├── 03_평가설계.md              # 평가 규칙·실행범위 확정 이력
├── 04_검증결과.md              # 검증 요약(버그·baseline·한계)
├── 05_업무효과검증_설계.md      # 업무 효과 검증 설계 + 14세션 실행 결과
├── 06_종합정리.md               # 종합정리
├── requirements.txt
├── .env.example
├── prompt/
│   ├── system_prompt.md               # 구조화 파이프라인 시스템 프롬프트
│   └── instructed_freeform_prompt.md  # 세 번째 baseline용 지침
├── schema/
│   ├── output_schema.json            # Output JSON Schema
│   └── validation_rules.md           # 자동 평가 규칙(A~E)
├── src/
│   ├── llm_extractor.py                    # 구조화 파이프라인 실행
│   ├── naive_baseline.py                   # naive baseline 실행
│   ├── instructed_freeform_baseline.py     # 세 번째 baseline 실행
│   ├── evaluate.py                         # GT 대조 자동 평가기
│   ├── conflict_detector.py                # GT 없는 conflict 탐지
│   └── review_app.py                       # 업무 효과 검토 UI(Streamlit)
├── data/
│   └── tc01~15_data.json             # 테스트 케이스 + Ground Truth
└── results/
    ├── structured/TC-XX.json                     # 구조화 파이프라인 출력
    ├── baseline/TC-XX.txt                        # naive baseline 출력
    ├── instructed_freeform/TC-XX.txt             # 세 번째 baseline 출력
    ├── metadata/TC-XX_eval.json                  # 자동 채점 결과
    ├── corrected/TC-05.json                      # Human Review 수정본
    ├── regression_fixtures/TC-05_corrupted_value.json  # 회귀 테스트 fixture
    ├── conflict_detection/TC-XX.json             # GT 없는 conflict 탐지 결과
    ├── naive_baseline_human_review.md            # naive 사람 대조 평가
    ├── instructed_freeform_human_review.md       # 3방향 비교
    ├── conflict_detector_log.md                  # conflict 탐지기 검증 기록
    ├── evaluator_validation_log.md               # 평가기 버그·한계 기록
    ├── tc01_iteration_log.md                     # TC-01 반복 개선 기록
    └── work_effect/
        ├── trial_log.md                          # 14세션 집계·GT 대조·해석
        └── app_logs/TC-XX_조건_실행ID.json         # 세션별 원본 로그(자동 기록)
```

## 스코프와 한계

15개로 설계한 테스트 케이스 중 **7개만 실제 실행**했습니다(세 번째 baseline은 그중 held-out
5건만). evaluate.py에는 알려진 잔여 버그가 있고(같은 문서를 인용하는 무관한 항목을 중복
확정으로 오판하는 D2), 표현이 다르지만 의미가 같은 경우(paraphrase)에 대한 매칭은 의도적으로
구현하지 않았습니다. 세 번째 baseline 비교는 5건·1회 샘플링 결과라 일반화하지 않습니다.

**구조화 파이프라인 결과는 완전히 재현되지 않습니다**: `temperature=0`을 적용해도 LLM
출력의 완전한 결정성은 보장되지 않았습니다 — 같은 케이스를 다시 실행하면 conflict 검출
여부, unknown/confirmed_absent 분류 등이 달라지는 경우를 실제로 관찰했습니다. 이 문서와
`results/structured/`의 수치는 특정 시점 실행 결과의 기록이며, 재실행하면 달라질 수
있습니다.

**업무 효과 실험(14세션)은 현업 검증이 아닙니다**: 실험자 1인(Ground Truth를 아는 사람,
실제 설계사 아님)이 진행한 자기실험(N=7)입니다. 원래 설계한 "1차·2차 세션 사이 최소 하루
간격"은 마감 제약으로 지키지 못하고 같은 날 이어서 진행해, 연습 효과를 배제하지 못합니다.
또한 작업시간이 75.6% 줄어든 결과가 나왔지만, 그 절감이 "AI 결과를 검증 없이 수용해서"
나왔을 가능성이 있습니다 — conflict·source_discrepancy 3개 케이스 중 조건 B에서 사람이
능동적으로 잡아낸 건 0건이었습니다. 이 결과를 "AI 보조로 업무시간을 X% 단축할 수 있다"로
일반화하지 않습니다.

전부 [`06_종합정리.md`](06_종합정리.md) §5, [`04_검증결과.md`](04_검증결과.md) §7,
[`05_업무효과검증_설계.md`](05_업무효과검증_설계.md) §7~§9에 기록되어 있습니다.
