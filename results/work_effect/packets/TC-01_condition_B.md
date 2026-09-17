# TC-01 — 조건 B (AI 결과 제공)

> AI가 낸 결과를 검토·확인해서 최종 비교표를 완성하세요.
> 원문(상담/계약/상품 자료)도 함께 첨부하니 필요할 때만 참고하세요(참고할 때마다 근거확인 카운트에 1 추가로 기록).

## AI 결과 (structured pipeline 출력)

### changes
- **premium**: 150000 → 110000 (decrease) | 근거: "월 보험료 110,000원" [product_B/product_brochure_p3]
- **renewal_period**: 10년 → 5년 (shortened) | 근거: "갱신주기 5년." [product_B/renewal_clause]
- **surrender_value_at_10y**: 62% → 31% (decrease) | 근거: "10년납 기준 해지환급률 31%." [product_B/surrender_value_table]

### unchanged_items
- **coverage_items.cancer_diagnosis**: 30000000 → 30000000 | 근거: "암 진단비 3,000만원 (최초 1회 지급)." [product_B/coverage_list]
- **coverage_items.cerebro_cardiac_diagnosis**: 15000000 → None | 근거: "뇌혈관질환·급성심근경색 진단비 특약: 목록에 없음." [product_B/coverage_list]

### unknowns (0건)

### conflicts (0건)

---

## 원문 (필요할 때만 참고)

- customer: 40대, 자녀 2명, 기존 계약 10년 유지

### 상담 내용
- [msg_01_01] customer: 안녕하세요, 예전에 가입한 보험이 있는데 요즘 보험료가 너무 부담돼서요. 좀 줄일 수 있는 방법 없을까요?
- [msg_01_02] agent: 네 고객님, 확인해보겠습니다. 지금 OO생명 종합보장 상품 10년째 유지하고 계시네요. 월 150,000원 내고 계시고요.
- [msg_01_03] customer: 네 맞아요. 이게 좀 오래됐는데, 이거 계속 갖고 있어야 하나 싶기도 하고.
- [msg_01_04] agent: 요즘 나온 △△화재 건강파트너라는 상품이 있는데, 이걸로 옮기시면 월 110,000원으로 조정됩니다.
- [msg_01_05] customer: 오 그럼 좀 낮아지는 거네요. 근데 보장 내용은 똑같은 거예요?
- [msg_01_06] agent: 잠시만요, 자료 다시 확인해보겠습니다. ...음, 제가 갱신주기를 잘못 봤네요. 다시 볼게요.
- [msg_01_07] agent: 네 확인했습니다. 암 진단비는 동일하게 3,000만원으로 유지되고요, 나머지 조건은 상품안내서 기준으로 정리해서 다시 말씀드릴게요.
- [msg_01_08] customer: 음... 그래도 이게 뭐가 더 좋은 건지 잘 모르겠어요. 그냥 뭐가 바뀌는지 정확하게 정리해서 알려주실 수 있어요?
- [msg_01_09] agent: 네, 정리해서 다시 안내드리겠습니다.

### 기존 계약 (contract_A / OO생명 종합보장)
- **premium**: 150000
- **coverage_items**:
  - **cancer_diagnosis**: 30000000
  - **cerebro_cardiac_diagnosis**: 15000000
- **renewal_period**: 10년
- **surrender_value_at_10y**: 62%

### 신규 상품 (product_B / △△화재 건강파트너)
- **product_brochure_p3**: 월 보험료 110,000원
- **coverage_list**: 암 진단비 3,000만원 (최초 1회 지급). 뇌혈관질환·급성심근경색 진단비 특약: 목록에 없음.
- **renewal_clause**: 갱신주기 5년.
- **surrender_value_table**: 10년납 기준 해지환급률 31%.

## 작성란

| 항목 | AI 결과 그대로 수용 | 수정함(사유) | 최종 old→new |
|---|---|---|---|
| | | | |

불리할 수 있는 변화로 최종 확정한 항목:

AI 결과를 의심해서 원문을 다시 확인한 횟수: ___ 회 (각 확인마다 무엇을 확인했는지 아래에 기록)
