# TC-03 — 조건 B (AI 결과 제공)

> AI가 낸 결과를 검토·확인해서 최종 비교표를 완성하세요.
> 원문(상담/계약/상품 자료)도 함께 첨부하니 필요할 때만 참고하세요(참고할 때마다 근거확인 카운트에 1 추가로 기록).

## AI 결과 (structured pipeline 출력)

### changes
- **premium**: 95000 → 88000 (decrease) | 근거: "보험료는 지금 95,000원에서 신규 상품은 88,000원으로 조정됩니다." [contract_A/msg_03_06]

### unchanged_items
- **exclusion_clause.suicide**: 가입 후 1년 이내 면책 → 가입 후 1년 이내 면책 | 근거: "가입 후 1년 이내 면책" [contract_A/existing_contract.fields.exclusion_clause.suicide]
- **exclusion_clause.specific_disease**: 90일 면책기간 → 90일 면책기간 | 근거: "90일 면책기간" [contract_A/existing_contract.fields.exclusion_clause.specific_disease]

### unknowns (2건)
- {'item': 'exclusion_clause', 'reason': '신규 상품 관련 면책기간 정보가 문서에 명시되어 있지 않음', 'status': 'unknown', 'evidence': None, 'source_id': 'product_B', 'source_location': 'product_brochure_p1', 'judgment': None}
- {'item': 'exclusion_clause.suicide', 'reason': '신규 상품의 면책 관련 정보 부족', 'status': 'unknown', 'evidence': None, 'source_id': 'product_B', 'source_location': 'product_brochure_p1', 'judgment': None}

### conflicts (0건)

---

## 원문 (필요할 때만 참고)

- customer: 50대, 기존 계약 8년 유지

### 상담 내용
- [msg_03_01] customer: 제가 예전에 가입할 때 자살이나 특정 질병 관련해서 면책기간 있다고 들었던 거 같은데, 이번에 새로 나온 상품도 그런 게 있나요?
- [msg_03_02] agent: 아, 확인해보겠습니다. 지금 갖고 계신 상품은 자살 관련해서 가입 후 1년 이내 면책이고, 특정 질병은 90일 면책기간이 있으시네요.
- [msg_03_03] customer: 네, 그거요. 새 상품도 똑같은가요?
- [msg_03_04] agent: 음... 제가 지금 갖고 있는 신규 상품 안내서에는 면책 관련 내용이 따로 안 나와 있네요. 아마 비슷하지 않을까 싶은데, 정확하게는 확인이 필요할 것 같습니다.
- [msg_03_05] customer: 음 그건 좀 확인해주셔야 할 것 같은데요. 그리고 보험료는 얼마나 차이 나요?
- [msg_03_06] agent: 보험료는 지금 95,000원에서 신규 상품은 88,000원으로 조정됩니다.

### 기존 계약 (contract_A / OO생명 든든플랜)
- **premium**: 95000
- **exclusion_clause**:
  - **suicide**: 가입 후 1년 이내 면책
  - **specific_disease**: 90일 면책기간

### 신규 상품 (product_B / OO생명 든든플랜 리뉴얼)
- **product_brochure_p1**: 월 보험료 88,000원. (본 안내서는 상품 주요 특징 요약본이며, 면책조항 등 세부 약관 내용은 포함하지 않습니다.)

## 작성란

| 항목 | AI 결과 그대로 수용 | 수정함(사유) | 최종 old→new |
|---|---|---|---|
| | | | |

불리할 수 있는 변화로 최종 확정한 항목:

AI 결과를 의심해서 원문을 다시 확인한 횟수: ___ 회 (각 확인마다 무엇을 확인했는지 아래에 기록)
