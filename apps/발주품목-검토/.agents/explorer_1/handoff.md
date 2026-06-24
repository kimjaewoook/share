# 1. Observation
- **`procurement_engine.py` 104-118번 라인**: `_round_to_unit` 함수는 `po_qty`, `box_qty`, `plt_total`을 받아 박스 단위 올림과 파렛트 50% 이상 시 올림을 수행합니다. 현재 에버원에 대한 예외 처리 파라미터는 없습니다.
- **`procurement_engine.py` 342-346번 라인**: `remaining` 변수에 가용재고를 할당하는 로직이 있습니다.
- **`procurement_engine.py` 284번 라인**: `vendor_name` 변수에 공급업체명이 할당됩니다.
- **`harness_PO_에버원.md` 5-7번 라인**: "짝수 파렛트 보정" 규칙이 명시되어 있으나, 무조건 파렛트로 올림한다는 점과 안전재고 13파렛트 차감 룰(3HGR0003, 3HGR0004 대상)은 누락되어 있습니다.

# 2. Logic Chain
1. **요구사항 1 (`_round_to_unit` 수정)**: 해당 함수에 `is_everone=False` 파라미터를 추가합니다. `is_everone=True`이고 `plt_total > 0`일 때, 기존 비율 검사(0.5 이상)를 무시하고 `math.ceil(po_qty / plt_total)`로 무조건 올립니다. 그 후 결과값이 홀수면 +1을 더해 짝수로 만들고 `plt_total`을 곱해 반환합니다.
2. **요구사항 2 (가용재고 차감 적용)**: 메인 루프에서 재고량 조회 직후(약 347번 라인 부근), `if "에버원" in vendor_name and mc in ["3HGR0003", "3HGR0004"]:` 조건을 확인하여 `remaining -= 13 * plt_total`을 수행합니다. 이로 인해 발주 산출 시 기존 재고가 줄어든 것으로 인식되어 발주량이 늘어납니다. 또한 루프 하단(약 400번 라인)의 `_round_to_unit` 호출 시 `is_everone=("에버원" in vendor_name)`를 전달합니다.
3. **요구사항 3 (harness_PO_에버원.md 업데이트)**: "1. 물류 및 알고리즘 예외" 섹션에 R1(무조건 짝수 파렛트 올림), R2(3HGR0003, 3HGR0004 재고 13파렛트 차감) 두 가지 규칙을 명확히 정의하여 추가합니다.

# 3. Caveats
- 재고에서 `13 * plt_total` 차감 시 `remaining` 값이 음수가 될 수 있으나, 후속 발주량 계산 수식 `po_qty = (req_qty + lt_demand + safety) - remaining - pend` 에서 음수가 차감(더해짐)되므로 요구 발주량이 정상적으로 증폭되어 알고리즘상 문제없이 작동할 것입니다.
- `plt_total`은 `box_qty * plt_boxes`로 계산되므로, 해당 자재 마스터에 이 정보가 올바르게 기입되어 있어야 13파렛트 차감이 정상 작동합니다.

# 4. Conclusion
- **코드 수정 방안**:
  1. `_round_to_unit(po_qty, box_qty, plt_total, is_everone=False)`로 서명 변경 후 에버원 전용 무조건 올림 및 홀수 판별 로직(+1) 추가.
  2. `generate_procurement_plan` 내 `remaining` 계산 후, 업체명이 에버원이고 코드가 3HGR0003/4일 때 `remaining -= (13 * plt_total)` 처리.
  3. `_round_to_unit` 호출부 파라미터 업데이트.
- **문서 수정 방안**: `harness_PO_에버원.md`에 R1(무조건 짝수 파렛트 올림), R2(전용 옷걸이 재고 13파렛트 차감) 룰을 명시적으로 추가.

# 5. Verification Method
- 구현 완료 후, 프로젝트의 테스트 명령어(예: `pytest`)를 실행하여 기본 로직이 훼손되지 않았는지 확인합니다.
- 추가로, 에버원(3HGR0003, 3HGR0004) 품목의 테스트 데이터를 주입하여 산출된 `vendor_po_qty`가 짝수 파렛트 수량으로 나오는지, 그리고 기존 가용재고에서 13파렛트(13 * plt_total)만큼이 없는 것으로 간주되어 발주량이 정상적으로 증폭 산출되는지 점검합니다.
