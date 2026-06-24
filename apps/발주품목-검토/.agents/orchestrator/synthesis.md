## Consensus
- **_round_to_unit 함수 수정**: `po_qty, box_qty, plt_total` 매개변수에 `is_everone=False` 추가. `is_everone`이 True일 경우, `plt_total`의 50% 비율 조건과 관계없이 무조건 파렛트로 올림 처리하며, 홀수 파렛트일 경우 1 파렛트를 더해 무조건 짝수 파렛트가 되도록 함. (R1)
- **가용재고 차감 로직 추가**: `generate_procurement_plan` 루프 내(Line 346 부근 `remaining` 값 세팅 직후), `vendor_name`에 "에버원"이 포함되고 `mc`가 "3HGR0003" 또는 "3HGR0004"일 때, `remaining -= (13 * plt_total)`을 실행. (R2)
- **정책 문서 업데이트**: `harness_PO_에버원.md`에 위의 R1(짝수 파렛트 강제 올림) 및 R2(13파렛트 안전재고 선차감) 룰을 명문화하여 추가함.

## Resolved Conflicts
- 3명의 Explorer 모두 동일한 위치와 로직에 동의하여 충돌 사항 없음.

## Dissenting Views
- 없음

## Gaps
- `remaining -= (13 * plt_total)` 시 음수가 발생하더라도 `po_qty` 산식 상 자동으로 발주 수량에 부족분으로 합산되므로 부작용은 없을 것으로 확인됨.
