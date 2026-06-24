#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
커머스 통합자동화 — Task 1: 호텔 수건 출고량 조회 (Metabase)

DOM  : React 가상 그리드 — div[role="row"] > div[data-column-id="담당공장"|"신청건수"]
출력 : 터미널 텍스트 (엑셀 다운로드 없음)
"""

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from config import METABASE_URL, YESTERDAY_STR, build_url
from browser_utils import save_error_debug


async def _parse_virtual_grid(page: Page) -> dict[str, int]:
    """Metabase 가상 그리드 파싱 → 팩토리별 수건 출고 건수 집계."""
    results: dict[str, int] = {"성수": 0, "군포": 0}

    rows = page.locator('div[role="row"]')
    row_count = await rows.count()

    if row_count == 0:
        print("    ⚠️ div[role='row'] 요소가 없습니다.")
        await save_error_debug(page, "metabase_no_rows")
        return results

    print(f"    ℹ️ div[role='row'] {row_count}개 발견")

    parsed = 0
    for i in range(row_count):
        row = rows.nth(i)
        factory_cell = row.locator('[data-column-id="담당공장"]')
        count_cell = row.locator('[data-column-id="신청건수"]')

        if await factory_cell.count() == 0 or await count_cell.count() == 0:
            continue

        factory_text = (await factory_cell.inner_text()).strip()
        count_text = (await count_cell.inner_text()).strip().replace(",", "")

        if not count_text:
            continue

        try:
            count_val = int(count_text)
        except (ValueError, TypeError):
            continue

        if count_val == 0:
            continue

        if "성수" in factory_text:
            results["성수"] += count_val
            parsed += 1
        elif "군포" in factory_text:
            results["군포"] += count_val
            parsed += 1

    print(f"    ℹ️ 유효 데이터 행: {parsed}건")
    return results


async def run_task_metabase(page: Page) -> dict[str, int]:
    """Task 1 실행."""
    print("\n" + "=" * 60)
    print("📋 Task 1: 호텔 수건 출고량 조회 (Metabase)")
    print("=" * 60)
    print(f"  📅 조회 기간: {YESTERDAY_STR}")

    url = build_url(
        METABASE_URL, "metabase_hotel_towel",
        startDate=YESTERDAY_STR, endDate=YESTERDAY_STR,
    )
    try:
        await page.goto(url, wait_until="networkidle", timeout=30_000)
        await page.wait_for_timeout(3000)
    except PlaywrightTimeoutError:
        print("  ❌ Metabase 페이지 접속 타임아웃")
        await save_error_debug(page, "metabase_load")
        return {"성수": 0, "군포": 0}

    # 로그인 상태 확인
    current_url = page.url.lower()
    login_keywords = ["login", "auth", "sign-in", "signin", "accounts.google"]
    if any(kw in current_url for kw in login_keywords):
        print("\n  🔑 Metabase 로그인이 필요합니다!")
        print("     브라우저에서 로그인한 뒤, Playwright Inspector에서 ▶ Resume 을 누르세요.\n")
        await page.pause()
        await page.goto(url, wait_until="networkidle", timeout=30_000)
        await page.wait_for_timeout(3000)

    # 가상 그리드 렌더링 대기
    try:
        await page.wait_for_selector('div[role="row"]', timeout=15_000)
        await page.wait_for_timeout(1500)
    except PlaywrightTimeoutError:
        no_result = (
            await page.get_by_text("결과 없음").count()
            + await page.get_by_text("No results").count()
        )
        if no_result > 0:
            print("  ℹ️ 조회 결과 없음 (0건)")
            return {"성수": 0, "군포": 0}
        print("  ❌ 그리드 렌더링 타임아웃")
        await save_error_debug(page, "metabase_table_parse")
        return {"성수": 0, "군포": 0}

    try:
        results = await _parse_virtual_grid(page)
    except Exception as e:
        print(f"  ❌ 그리드 파싱 실패: {e}")
        await save_error_debug(page, "metabase_table_parse")
        results = {"성수": 0, "군포": 0}

    ss = results.get("성수", 0)
    gp = results.get("군포", 0)
    print(f"\n  🏨 호텔수건 출고량 ─ 성수팩토리: {ss}개, 군포팩토리: {gp}개")
    return results
