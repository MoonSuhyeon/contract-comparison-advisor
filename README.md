# Contract Comparison Advisor

## 문제정의

기존 보험계약을 신규 상품으로 전환할 때, 보장·지급조건·갱신·환급금 같은 눈에 잘 안 띄는
조건 변화를 놓치면 고객이 손해를 볼 수 있습니다. 금융위원회도 GA(법인보험대리점)의 이런
"중요사항 비교 미고지"를 반복되는 불완전판매 문제로 지목한 바 있습니다(근거:
[`C6_문제정의_최종.md`](C6_문제정의_최종.md)). 이 프로젝트가 묻는 질문은 "AI가 계약을 잘
비교하는가"가 아니라 "AI의 출력을 어떻게 검증하고, 실패를 사람이 개입 가능한 데이터로
남기는가"입니다.

## 해결방법

AI는 Extract/Compare/Flag/Unknown/Evidence까지만 하고, 최종 판단(Judge/Explain/Confirm/
Record)은 사람이 하도록 역할을 분리했습니다. 테스트 케이스 15개(Ground Truth 포함)를 설계해
그중 7개를 구조화 파이프라인(프롬프트+JSON 스키마+검증 규칙)과 naive 프롬프트 양쪽으로 실제
실행·비교했고, 자체 평가기(`src/evaluate.py`)로 채점하는 과정에서 평가기 자체의 버그 7건을
발견·수정했으며, AI가 놓친 사례 1건은 사람이 직접 검토·수정하는 Human-in-the-loop까지
시연했습니다.

핵심 발견: naive와 structured의 단순 "변경사항 발견" 능력 차이는 크지 않았지만, 근거 명시·
출처 충돌 보존·판단 경계 준수에서는 뚜렷하게 갈렸습니다. 더 중요한 건, structured도 conflict를
종종 놓쳤지만 그 실패를 평가기가 자동으로 감지해 Human Review로 넘길 수 있었던 반면, naive의
실패는 사람이 원문을 전부 대조해야만 드러났다는 점입니다. 상세 비교표는
[`06_종합정리.md`](06_종합정리.md), 평가기 버그·한계 전체 기록은
[`results/evaluator_validation_log.md`](results/evaluator_validation_log.md) 참고.

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
전체 15개(`data/tc01~15_data.json`) 중 실제로 실행·평가까지 완료한 건 **7개**다:
`TC-01 TC-03 TC-04 TC-05 TC-10 TC-11 TC-15` (나머지 8개는 설계·GT만 완성된 상태 — 이유는
[`06_종합정리.md`](06_종합정리.md) 5번 참고).

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

### 5. 결과 확인
| 무엇을 보려면 | 어디를 보면 되는가 |
|---|---|
| 구조화 파이프라인이 실제로 낸 JSON | `results/structured/TC-XX.json` |
| naive baseline이 낸 자유 텍스트 | `results/baseline/TC-XX.txt` |
| 자동 채점 결과(Recall/Precision 등 수치 + 위반 목록) | `results/metadata/TC-XX_eval.json` |
| naive 7건을 사람이 직접 대조한 정성 평가 | `results/naive_baseline_human_review.md` |
| 평가기(`evaluate.py`) 자체를 개발하며 발견한 버그·한계 전체 | `results/evaluator_validation_log.md` |
| Human Review로 사람이 직접 수정한 사례(TC-05) | `results/corrected/TC-05.json` |

## 폴더 구조

```
contract-comparison-advisor/
├── C6_문제정의_최종.md              # 문제 정의 + 규제 근거 (금융위 발표 원문 확인)
├── C6_설계_확정본.md                 # 테스트 설계·평가 규칙 확정 이력 (발견 → 수정 → 재확정)
├── 06_종합정리.md                     # 최종 정리 (5개 항목)
├── requirements.txt
├── .env.example
├── prompt/
│   └── system_prompt.md              # 구조화 파이프라인 시스템 프롬프트
│                                      # (Extract/Compare/Flag/Unknown/Evidence, judgment 항상 null)
├── schema/
│   ├── output_schema.json            # 공통 Output JSON Schema (changes/unchanged_items/
│   │                                  #  unknowns/conflicts/additional_conditions/customer_needs)
│   └── validation_rules.md           # 자동 평가 규칙 — 매칭 M1~M3, 검증 A~E(Precision/
│                                      #  Unknown/Conflict/Boundary Violation)
├── src/
│   ├── llm_extractor.py              # 구조화 파이프라인 실행 — function calling + jsonschema
│   │                                  #  검증 + 재시도, 실패해도 크래시 대신 무효표시 저장
│   ├── naive_baseline.py             # naive baseline 실행 — 스키마 없는 자유 텍스트 (비교 기준)
│   └── evaluate.py                   # GT 대조 자동 평가기 — Recall/Precision/Evidence/
│                                      #  Unknown/Conflict, AUTO-FAIL/HUMAN-QUEUE 판정
├── data/
│   └── tc01~15_data.json             # 15개 테스트 케이스 (시나리오 + Ground Truth), 7개만 실행
└── results/
    ├── structured/TC-XX.json         # 구조화 파이프라인 실제 출력
    ├── baseline/TC-XX.txt            # naive baseline 실제 출력(자유 텍스트)
    ├── metadata/TC-XX_eval.json      # evaluate.py 채점 결과(수치 + 위반 목록)
    ├── corrected/TC-05.json          # Human Review로 사람이 직접 수정한 사례
    ├── naive_baseline_human_review.md  # naive 7건을 사람이 직접 6개 기준으로 대조 평가
    ├── evaluator_validation_log.md     # evaluate.py 개발 중 발견한 버그·한계 전체 기록
    └── tc01_iteration_log.md           # TC-01 프롬프트 v1→v2 반복 개선 기록
```

## 스코프와 한계 

15개로 설계한 테스트 케이스 중 **7개만 실제 실행**했습니다. evaluate.py에는 알려진 잔여
버그가 있고(같은 문서를 인용하는 무관한 항목을 중복 확정으로 오판하는 경우), 표현이 다르지만
의미가 같은 경우(paraphrase)에 대한 매칭은 의도적으로 구현하지 않았습니다. 전부
[`06_종합정리.md`](06_종합정리.md) 5번 항목과 [`results/evaluator_validation_log.md`](results/evaluator_validation_log.md)에 기록되어 있습니다.
