# Contract Comparison Advisor

기존 보험계약을 신규 상품으로 전환할 때 놓치기 쉬운 조건 변화(보장·지급조건·갱신·환급금)를
AI가 근거와 함께 빠짐없이 찾아내고, AI의 판단 범위(Extract/Compare/Flag/Unknown/Evidence)와
사람의 판단 범위(Judge/Explain/Confirm/Record)를 분리해서 검증하는 프로젝트입니다.

핵심 질문은 "AI가 계약을 잘 비교하는가"가 아니라 **"AI의 출력을 어떻게 검증하고, 실패를
데이터로 남기고, 사람이 개입할 수 있게 만드는가"**입니다.

## 배경

금융위원회 2025-01-22 공식 발표(원문 확인)는 GA(법인보험대리점)의 "기존-신규계약 중요사항
비교 미고지"를 반복되는 불완전판매 문제로 지목했습니다. 이 프로젝트는 그 문제의 한 조각을
AI로 보완할 수 있는지 실험합니다. 자세한 배경과 근거는 [`C6_문제정의_최종.md`](C6_문제정의_최종.md)
참고.

## 무엇을 실제로 했는가

1. 15개 테스트 케이스(정상 + 의도적 실패 유도 케이스)를 설계하고 정답(Ground Truth)까지 작성
2. 시스템 프롬프트 + JSON 출력 스키마 + 자동 검증 규칙(Recall/Precision/Evidence/Unknown/
   Conflict/Boundary Violation)을 확정
3. 그중 7개를 실제 LLM(gpt-4o-mini)으로 돌리고, 같은 7개를 스키마 없는 naive 프롬프트로도
   돌려서 비교
4. 자체 제작한 평가기(`src/evaluate.py`)를 실행하며 평가기 자체의 버그 7건을 발견·수정
5. AI가 실제로 놓친 사례(문서 간 충돌) 하나를 사람이 직접 검토·수정하는 Human-in-the-loop을
   시연

## 핵심 발견

Naive와 Structured의 단순 "변경사항 발견" 능력 차이는 크지 않았습니다. 차이는 **근거 명시,
출처 충돌 보존, 판단 경계 준수**에서 뚜렷했습니다. 그리고 가장 중요한 발견: Structured도
conflict를 종종 놓쳤지만, **그 실패를 평가기가 자동으로 감지해 Human Review로 넘길 수 있었던
반면, naive의 실패는 사람이 원문을 전부 대조해야만 드러났습니다.**

상세 비교표와 근거는 [`06_종합정리.md`](06_종합정리.md), 평가기 개발 중 발견한 버그와 한계는
[`results/evaluator_validation_log.md`](results/evaluator_validation_log.md)에 전부 기록되어
있습니다 — 실패와 한계를 숨기지 않는 것이 이 프로젝트의 원칙입니다.

## 실행 방법

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux

cp .env.example .env   # OPENAI_API_KEY 채우기

.venv/Scripts/python src/llm_extractor.py TC-01      # 구조화 파이프라인
.venv/Scripts/python src/naive_baseline.py TC-01     # naive baseline
.venv/Scripts/python src/evaluate.py TC-01           # 구조화 결과 자동 채점
```

## 폴더 구조

```
C6_문제정의_최종.md         문제 정의 + 규제 근거
C6_설계_확정본.md            테스트 설계·평가 규칙 확정 이력 (발견 → 수정 → 재확정 기록)
PLAN.md                     Phase별 작업 계획과 진행 상황
06_종합정리.md                최종 정리 (5개 항목)
prompt/system_prompt.md      구조화 파이프라인 시스템 프롬프트
schema/output_schema.json    공통 Output JSON Schema
schema/validation_rules.md   자동 평가 규칙 (M1~M3 매칭, A~E 검증)
src/llm_extractor.py         구조화 파이프라인 실행
src/naive_baseline.py        naive baseline 실행
src/evaluate.py              GT 대조 자동 평가기
data/tc01~15_data.json       15개 테스트 케이스 (시나리오 + Ground Truth)
results/                     실행 결과, 평가 로그, Human Review 시연
```

## 스코프와 한계 (숨기지 않음)

15개로 설계한 테스트 케이스 중 **7개만 실제 실행**했습니다. evaluate.py에는 알려진 잔여
버그가 있고(같은 문서를 인용하는 무관한 항목을 중복 확정으로 오판하는 경우), 표현이 다르지만
의미가 같은 경우(paraphrase)에 대한 매칭은 의도적으로 구현하지 않았습니다. 전부
[`06_종합정리.md`](06_종합정리.md) 5번 항목과 [`results/evaluator_validation_log.md`](results/evaluator_validation_log.md)에 기록되어 있습니다.
