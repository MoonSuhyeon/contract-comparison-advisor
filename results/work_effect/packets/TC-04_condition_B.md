# TC-04 — 조건 B (AI 결과 제공)

> AI가 낸 결과를 검토·확인해서 최종 비교표를 완성하세요.
> 원문(상담/계약/상품 자료)도 함께 첨부하니 필요할 때만 참고하세요(참고할 때마다 근거확인 카운트에 1 추가로 기록).

## AI 결과 (structured pipeline 출력)

### changes
- **premium**: 130000 → 115000 (decrease) | 근거: "월 보험료 115,000원" [product_B/product_brochure_p2]
- **coverage_items.cancer_diagnosis**: 30000000 → 20000000 (scope_narrowed) | 근거: "암 진단비 2,000만원 (최초 1회 지급)." [product_B/coverage_list]

### unchanged_items
- **coverage_items.cancer_diagnosis**: 30000000 → 20000000 | 근거: "암 진단비 2,000만원 (최초 1회 지급)." [product_B/coverage_list]

### unknowns (0건)

### conflicts (1건)
- {'item': 'coverage_items.cancer_diagnosis', 'type': 'source_discrepancy', 'old': 30000000, 'new': None, 'sources': [{'source_id': 'contract_A', 'source_location': 'coverage_list', 'evidence': '30000000'}, {'source_id': 'product_B', 'source_location': 'coverage_list', 'evidence': '암 진단비 2,000만원 (최초 1회 지급).'}], 'description': '기존 계약은 암 진단비가 3,000만원인데 신규 상품에서는 2,000만원으로 줄어들었다.', 'judgment': None}

---

## 원문 (필요할 때만 참고)

- customer: 40대, 기존 계약 6년 유지

### 상담 내용
- [msg_04_01] customer: 보험료만 좀 낮추고 싶은 거지, 암 보장 같은 건 그대로 유지되면 좋겠는데요.
- [msg_04_02] agent: 네 물론이죠. 지금 상품 월 130,000원인데, 신규 상품으로 옮기시면 115,000원으로 낮아지고요, 암 보장은 그대로예요. 걱정 안 하셔도 됩니다.
- [msg_04_03] customer: 아 다행이네요. 그럼 보험료만 낮아지는 거고 나머지는 똑같은 거죠?
- [msg_04_04] agent: 네 맞습니다. 보험료 부분만 신경 쓰시면 될 것 같아요.

### 기존 계약 (contract_A / OO생명 평생보장)
- **premium**: 130000
- **coverage_items**:
  - **cancer_diagnosis**: 30000000

### 신규 상품 (product_B / OO생명 평생보장 리뉴얼)
- **product_brochure_p2**: 월 보험료 115,000원
- **coverage_list**: 암 진단비 2,000만원 (최초 1회 지급).

## 작성란

| 항목 | AI 결과 그대로 수용 | 수정함(사유) | 최종 old→new |
|---|---|---|---|
| | | | |

불리할 수 있는 변화로 최종 확정한 항목:

AI 결과를 의심해서 원문을 다시 확인한 횟수: ___ 회 (각 확인마다 무엇을 확인했는지 아래에 기록)
