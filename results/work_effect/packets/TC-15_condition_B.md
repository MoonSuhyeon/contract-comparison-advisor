# TC-15 — 조건 B (AI 결과 제공)

> AI가 낸 결과를 검토·확인해서 최종 비교표를 완성하세요.
> 원문(상담/계약/상품 자료)도 함께 첨부하니 필요할 때만 참고하세요(참고할 때마다 근거확인 카운트에 1 추가로 기록).

## AI 결과 (structured pipeline 출력)

### changes
- **premium**: 118000 → 96000 (decrease) | 근거: "월 보험료 96,000원." [product_B/product_summary_brochure]
- **coverage_items.cancer_diagnosis.diagnosis_scope**: 암(경계성종양, 상피내암 포함) → 침습암만 해당 (scope_narrowed) | 근거: "암 진단비 3,000만원 (경계성종양·상피내암 제외, 침습암만 해당)." [product_B/product_summary_brochure]
- **coverage_items.accident_disability**: 10000000 → 5000000 (decrease) | 근거: "상해장해 보장금액 500만원." [product_B/product_summary_brochure]
- **coverage_items.cerebro_cardiac_diagnosis**: 15000000 → None (removed) | 근거: "뇌혈관질환·급성심근경색 특약: 목록에 없음." [product_B/product_summary_brochure]

### unchanged_items
- **exclusion_clause.cancer**: 가입 후 90일 면책 → None | 근거: "가입 후 90일 면책" [contract_A/contract_A]

### unknowns (1건)
- {'item': 'enrollment_date', 'old': None, 'new': None, 'status': 'unknown', 'evidence': None, 'source_id': 'contract_A', 'source_location': None, 'reason': '고객이 정확한 가입일자를 기억하지 못함.', 'judgment': None}

### conflicts (0건)

---

## 원문 (필요할 때만 참고)

- customer: 50대, 가족 중 암 병력 있음, 정확한 기존 계약 가입일자를 기억하지 못함, 예산에 민감함

### 상담 내용
- [msg_15_01] customer: 저희 어머니가 암 투병을 하셔서, 저도 암 관련 보장은 좀 꼼꼼히 보고 싶어요.
- [msg_15_02] agent: 네, 확인해드릴게요. 그리고 요즘 보험료 부담도 있으실 텐데 그 부분도 같이 봐드리겠습니다.
- [msg_15_03] customer: 이 계약 정확히 언제 가입했는지도 가물가물한데, 꽤 됐죠 아마?
- [msg_15_04] agent: 시스템에는 가입일자가 따로 안 뜨네요. 정확히는 확인이 더 필요할 것 같습니다.
- [msg_15_05] customer: 그리고 상해 관련 보장은 그대로 유지되는 거 맞죠?
- [msg_15_06] agent: 네, 상해 관련 보장은 그대로예요, 걱정 안 하셔도 됩니다. 아, 그리고 보험료는 118,000원에서 96,000원으로 낮아집니다.
- [msg_15_07] customer: 좋네요. 그럼 면책기간 같은 것도 지금이랑 똑같은 거죠?
- [msg_15_08] agent: 그 부분은 제가 지금 갖고 있는 요약 안내서에는 안 나와 있어서, 별도로 확인해서 알려드리겠습니다.

### 기존 계약 (contract_A / OO생명 가족건강보장)
- **premium**: 118000
- **enrollment_date**: None
- **coverage_items**:
  - **cerebro_cardiac_diagnosis**: 15000000
  - **accident_disability**: 10000000
  - **cancer_diagnosis**:
    - **amount**: 30000000
    - **diagnosis_scope**: 암(경계성종양, 상피내암 포함)
- **exclusion_clause**:
  - **cancer**: 가입 후 90일 면책

### 신규 상품 (product_B / OO생명 가족건강보장 리뉴얼)
- **product_summary_brochure**: 월 보험료 96,000원. 상해장해 보장금액 500만원. 암 진단비 3,000만원 (경계성종양·상피내암 제외, 침습암만 해당). 뇌혈관질환·급성심근경색 특약: 목록에 없음. (본 문서의 보장 항목 목록은 완전하게 기재되어 있으나, 면책조항 등 세부 약관 내용은 포함하지 않습니다.)

## 작성란

| 항목 | AI 결과 그대로 수용 | 수정함(사유) | 최종 old→new |
|---|---|---|---|
| | | | |

불리할 수 있는 변화로 최종 확정한 항목:

AI 결과를 의심해서 원문을 다시 확인한 횟수: ___ 회 (각 확인마다 무엇을 확인했는지 아래에 기록)
