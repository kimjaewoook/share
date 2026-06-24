# Project: 발주품목-검토 (에버원 예외 보정)

## Architecture
- `src/procurement_engine.py`: 핵심 발주 로직 엔진. `_round_to_unit` 함수 및 `generate_procurement_plan` 루프 내 계산식 포함.
- `ai/_config/rules/harness_PO_에버원.md`: 에버원 전용 발주 보정 룰셋 명세서.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | 에버원 로직 구현 | `procurement_engine.py`내 에버원 강제 파렛트화 및 13파렛트 안전재고, `harness_PO_에버원.md` 룰 현행화 | none | PLANNED |

## Interface Contracts
### `_round_to_unit` ↔ `generate_procurement_plan`
- **Before**: `def _round_to_unit(po_qty, box_qty, plt_total):`
- **After**: `def _round_to_unit(po_qty, box_qty, plt_total, is_everone=False):`
  - 에버원일 경우(`is_everone=True`), `po_qty % plt_total`이 0 초과 시 잔여 비율과 상관없이 무조건 `plt_total`의 배수로 올림 (`math.ceil(po_qty / plt_total) * plt_total`).
  - 에버원의 기존 '홀수 파렛트 짝수 보정' 규칙이 있으므로, 무조건 올림 이후 도출된 파렛트 단위수가 홀수이면 한 번 더 `+1` 파렛트 분량(`plt_total`)을 추가하여 짝수 파렛트로 보정.

### 3HGR0003, 3HGR0004 재고 차감 로직
- `generate_procurement_plan`의 재고 계산 시:
  - `is_everone_13plt_target = mc in ["3HGR0003", "3HGR0004"]`
  - 해당 품목이면 `remaining` 변수에서 `(13 * plt_total)`을 차감.
  - 음수가 되더라도 그대로 두거나 최소 0 이상으로 설정(이 부분은 엔진의 기존 로직을 따름, 기본은 차감).
  - 기존 비율 기반 `safety = lt_demand * 0.2`는 유지함.

## Code Layout
- 메인 스크립트: `/Users/kimjaewoook/ai/laundrygo/apps/발주품목-검토/src/procurement_engine.py`
- 정책 문서: `/Users/kimjaewoook/ai/_config/rules/harness_PO_에버원.md`
