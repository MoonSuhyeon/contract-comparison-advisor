# Contract Comparison Advisor

## 문제정의

기존 보험계약을 신규 상품으로 바꿀 때, 보장·지급조건·갱신·환급금처럼 눈에 잘 띄지 않는
조건의 변화를 놓치면 고객에게 불리한 결과로 이어질 수 있습니다. 금융위원회도 GA(법인보험대리점)의
이러한 "중요사항 비교 미고지"를 반복되는 불완전판매 문제로 지적한 바 있습니다.

따라서 이 프로젝트에서는 단순히 "AI가 계약을 잘 비교하는가"에 그치지 않고, **AI의 출력을
어떻게 검증하고, 실패를 사람이 확인할 수 있는 데이터로 남길 것인가**에 초점을 맞췄습니다.

규제·통계 근거는 [`01_문제정의.md`](01_문제정의.md) 참고.

## 해결방법

AI는 계약 간 차이를 찾아 근거와 함께 제시하는 역할까지만 맡고, 최종 판단은 사람이 하도록
역할을 나눴습니다. 이를 검증하기 위해 테스트 케이스 15개(Ground Truth 포함)를 설계하고,
그중 7개를 구조화 파이프라인과 naive 프롬프트로 각각 실행해 비교했습니다. 이 과정에서는
AI 결과뿐 아니라 평가기(`src/evaluate.py`) 자체의 오류도 점검해 9건의 버그를 찾아
수정했습니다.

검증 결과, naive와 structured는 **변화를 찾아내는 능력 자체에서는 큰 차이가 없었지만**,
근거를 명시하고 출처 간 충돌을 보존하며 판단 범위를 지키는 부분에서는 차이가 나타났습니다.
특히 structured의 오류는 평가기가 자동으로 감지해 사람의 검토 대상으로 넘길 수 있었던 반면,
naive의 오류는 원문을 다시 대조해야 확인할 수 있었습니다.

자세한 비교 결과와 평가기 버그 9건, GT 없이 수행한 conflict 탐지 및 세 번째 baseline
검증은 [`06_종합정리.md`](06_종합정리.md), [`04_검증결과.md`](04_검증결과.md),
[`results/evaluator_validation_log.md`](results/evaluator_validation_log.md)에서
확인할 수 있습니다.

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
AI가 만든 비교 초안(TC-01)을 화면에서 직접 확인·수정·추가해 최종 결과를 확정하는 검토
도구입니다. Ground Truth는 이 화면에 절대 노출되지 않고, "최종 확정"을 누르면 소요 시간과
수정·추가 항목 수가 `results/work_effect/app_logs/`에 자동 기록됩니다(`05_업무효과검증_설계.md`
§8에서 정의한 검토 화면의 구현체).

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
| 검토 UI에서 "최종 확정"으로 저장한 소요시간·수정량 로그 | `results/work_effect/app_logs/TC-XX_조건_실행ID.json` |

## 폴더 구조

```
contract-comparison-advisor/
├── 01_문제정의.md              # 문제 정의 + 규제 근거
├── 02_테스트케이스.md          # 15개 테스트 케이스 설계
├── 03_평가설계.md              # 평가 규칙·실행범위 확정 이력
├── 04_검증결과.md              # 검증 요약(버그·baseline·한계)
├── 05_업무효과검증_설계.md      # 업무 효과 검증 설계(실행 전)
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
    └── tc01_iteration_log.md                     # TC-01 반복 개선 기록
```

## 스코프와 한계

15개로 설계한 테스트 케이스 중 **7개만 실제 실행**했습니다(세 번째 baseline은 그중 held-out
5건만). evaluate.py에는 알려진 잔여 버그가 있고(같은 문서를 인용하는 무관한 항목을 중복
확정으로 오판하는 D2), 표현이 다르지만 의미가 같은 경우(paraphrase)에 대한 매칭은 의도적으로
구현하지 않았습니다. 세 번째 baseline 비교는 5건·1회 샘플링 결과라 일반화하지 않습니다. 전부
[`06_종합정리.md`](06_종합정리.md) §5와 [`04_검증결과.md`](04_검증결과.md) §7에
기록되어 있습니다.
