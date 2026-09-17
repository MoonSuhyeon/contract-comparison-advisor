# TC-11 — 조건 B (AI 결과 제공)

> AI가 낸 결과를 검토·확인해서 최종 비교표를 완성하세요.
> 원문(상담/계약/상품 자료)도 함께 첨부하니 필요할 때만 참고하세요(참고할 때마다 근거확인 카운트에 1 추가로 기록).

## AI 결과 (structured pipeline 출력)

### changes
- **premium**: 105000 → 89000 (decrease) | 근거: "월 보험료 89,000원." [product_B/product_brochure_p2]
- **coverage_items.cerebro_diagnosis.amount**: 15000000 → 15000000 (unchanged) | 근거: "뇌혈관질환 진단비 1,500만원." [product_B/coverage_list]
- **coverage_items.cerebro_diagnosis.diagnosis_scope**: 뇌졸중(뇌경색, 뇌출혈 등 뇌혈관질환 포함) → 허혈성 뇌졸중(뇌경색)으로 진단 확정된 경우에 한함. 뇌출혈 등 출혈성 뇌졸중은 보장 대상에서 제외됨. (scope_narrowed) | 근거: "진단 기준: 허혈성 뇌졸중(뇌경색)으로 진단 확정된 경우에 한함. 뇌출혈 등 출혈성 뇌졸중은 보장 대상에서 제외됨." [product_B/coverage_list]

### unchanged_items

### unknowns (0건)

### conflicts (1건)
- {'item': 'coverage_items.cerebro_diagnosis.amount', 'type': 'source_discrepancy', 'sources': [{'source_id': 'contract_A', 'source_location': 'coverage_list', 'evidence': '15000000'}, {'source_id': 'product_B', 'source_location': 'coverage_list', 'evidence': '1,500만원.'}], 'description': '보험금액은 변경 없지만, 진단 기준이 다르다. 보험상품에서 보장대상의 범위가 좁아졌다.', 'judgment': None}

---

## 원문 (필요할 때만 참고)

- customer: 40대, 부모님이 뇌졸중 이력 있음

### 상담 내용
- [msg_11_01] customer: 저희 부모님이 예전에 뇌졸중을 앓으셔서, 저도 뇌 쪽 보장은 좀 신경 쓰이더라고요.
- [msg_11_02] agent: 아 그러시군요. 그럼 지금 갖고 계신 보장부터 확인해드릴게요.
- [msg_11_03] customer: 네, 그리고 보험료도 좀 줄었으면 좋겠어요.
- [msg_11_04] agent: 확인해보니 보험료는 105,000원에서 신규 상품으로 옮기시면 89,000원으로 낮아지고요, 뇌 관련 보장금액은 1,500만원으로 지금이랑 동일하게 유지됩니다.
- [msg_11_05] customer: 오 그럼 보험료만 낮아지고 나머지는 똑같은 거네요, 다행이다.
- [msg_11_06] agent: 네 맞습니다. 자세한 건 정리해서 안내드릴게요.

### 기존 계약 (contract_A / OO생명 뇌심혈관보장)
- **premium**: 105000
- **coverage_items**:
  - **cerebro_diagnosis**:
    - **amount**: 15000000
    - **diagnosis_scope**: 뇌졸중(뇌경색, 뇌출혈 등 뇌혈관질환 포함)

### 신규 상품 (product_B / OO생명 뇌심혈관보장 리뉴얼)
- **product_brochure_p2**: 월 보험료 89,000원.
- **coverage_list**: 뇌혈관질환 진단비 1,500만원. 진단 기준: 허혈성 뇌졸중(뇌경색)으로 진단 확정된 경우에 한함. 뇌출혈 등 출혈성 뇌졸중은 보장 대상에서 제외됨.

## 작성란

| 항목 | AI 결과 그대로 수용 | 수정함(사유) | 최종 old→new |
|---|---|---|---|
| | | | |

불리할 수 있는 변화로 최종 확정한 항목:

AI 결과를 의심해서 원문을 다시 확인한 횟수: ___ 회 (각 확인마다 무엇을 확인했는지 아래에 기록)
