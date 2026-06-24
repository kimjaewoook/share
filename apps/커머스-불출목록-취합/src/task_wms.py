#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
커머스 통합자동화 — Task 3: WMS 재고 다운로드 (ezstorage)

8단계 파이프라인: 로그인 → 센터 선택 → 조회 → SVG 엑셀 → 확인 → 범위 선택 → 다운로드
다운로드 경로: INPUT_DIR (source/ 폴더)
"""

from pathlib import Path

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from config import WMS_URL, WMS_ID, WMS_PW, TODAY_STR, INPUT_DIR, URL_PATHS, WMS_STOCK_PARAMS
from browser_utils import save_error_debug, wait_and_save_download


def _build_wms_url(path: str, params: str = "") -> str:
    base = WMS_URL.rstrip("/")
    url = f"{base}/{path.lstrip('/')}"
    if params:
        url += f"?{params}"
    return url


async def _force_login(page: Page) -> None:
    """ezstorage 로그인 파이프라인."""
    login_url = _build_wms_url("/login")
    print(f"  🔑 ezstorage 로그인 확인 중...")

    await page.goto(login_url, wait_until="networkidle", timeout=30_000)
    await page.wait_for_timeout(2000)

    current = page.url.lower()
    if "/login" not in current and "/sign" not in current:
        print("  ✅ ezstorage 세션 유효 — 로그인 생략")
        return

    print("  🔑 ezstorage 로그인 진행 중...")

    id_filled = False
    for loc in [
        page.locator("input[type='email']").first,
        page.locator("input[placeholder*='이메일']").first,
        page.locator("input[placeholder*='email' i]").first,
        page.locator("input[name='email']").first,
        page.locator("input[type='text']").first,
    ]:
        try:
            if await loc.count() > 0:
                await loc.fill(WMS_ID)
                id_filled = True
                break
        except Exception:
            continue
    if not id_filled:
        await save_error_debug(page, "wms_login_id_field")
        raise RuntimeError("ezstorage ID 입력란 미발견")

    pw_filled = False
    for loc in [
        page.locator("input[type='password']").first,
        page.locator("input[placeholder*='비밀번호']").first,
    ]:
        try:
            if await loc.count() > 0:
                await loc.fill(WMS_PW)
                pw_filled = True
                break
        except Exception:
            continue
    if not pw_filled:
        await save_error_debug(page, "wms_login_pw_field")
        raise RuntimeError("ezstorage PW 입력란 미발견")

    for btn in [
        page.get_by_role("button", name="로그인"),
        page.get_by_role("button", name="Login"),
        page.locator("button[type='submit']").first,
    ]:
        try:
            if await btn.count() > 0:
                await btn.click()
                break
        except Exception:
            continue

    await page.wait_for_load_state("networkidle", timeout=15_000)
    await page.wait_for_timeout(2000)

    if "/login" in page.url.lower():
        await save_error_debug(page, "wms_login_failed")
        raise RuntimeError("ezstorage 로그인 실패")

    print("  ✅ ezstorage 로그인 완료")


async def _run_query_and_download(page: Page, target_path: Path) -> Path:
    """8단계 조회 + 다운로드 파이프라인."""

    # Step 1: 센터 드롭다운 열기
    print("    [1/8] 센터 드롭다운 열기...")
    for loc in [
        page.get_by_label("센터", exact=True),
        page.get_by_role("combobox", name="센터"),
        page.locator("select").filter(has_text="센터"),
    ]:
        try:
            if await loc.count() > 0:
                await loc.first.click()
                await page.wait_for_timeout(800)
                break
        except Exception:
            continue
    else:
        await save_error_debug(page, "wms_step1_dropdown")
        raise RuntimeError("[Step 1] 센터 드롭다운 미발견")

    # Step 2: 군포센터 선택
    print("    [2/8] 군포센터 선택...")
    for loc in [
        page.get_by_role("option", name="군포센터"),
        page.get_by_text("군포센터", exact=True),
        page.get_by_text("군포", exact=False).first,
    ]:
        try:
            if await loc.count() > 0:
                await loc.first.click()
                await page.wait_for_timeout(500)
                break
        except Exception:
            continue
    else:
        await save_error_debug(page, "wms_step2_option")
        raise RuntimeError("[Step 2] 군포센터 옵션 미발견")

    # Step 3: 조회 버튼
    print("    [3/8] 조회 버튼 클릭...")
    search_btn = page.get_by_role("button", name="조회")
    if await search_btn.count() == 0:
        search_btn = page.get_by_role("button", name="검색")
    if await search_btn.count() == 0:
        await save_error_debug(page, "wms_step3_search")
        raise RuntimeError("[Step 3] 조회 버튼 미발견")
    await search_btn.click()

    # Step 4: 데이터 로딩 대기
    print("    [4/8] 데이터 로딩 대기...")
    await page.wait_for_load_state("networkidle", timeout=30_000)
    await page.wait_for_timeout(2000)
    try:
        no_data = page.get_by_text("조회 내용이 없습니다")
        if await no_data.count() > 0:
            await no_data.wait_for(state="hidden", timeout=10_000)
    except PlaywrightTimeoutError:
        pass
    print("    ✅ 데이터 로딩 완료")

    # Step 5: 엑셀 SVG 아이콘 클릭
    print("    [5/8] 엑셀 다운로드 아이콘 클릭...")
    for loc in [
        page.locator("svg[data-name*='엑셀다운로드']"),
        page.locator("svg[id*='엑셀다운로드']"),
        page.locator("svg[data-name*='엑셀']"),
        page.locator("[aria-label*='엑셀']"),
        page.get_by_role("button", name="엑셀 다운로드"),
        page.get_by_role("button", name="엑셀"),
    ]:
        try:
            if await loc.count() > 0:
                await loc.first.click()
                await page.wait_for_timeout(1000)
                break
        except Exception:
            continue
    else:
        await save_error_debug(page, "wms_step5_excel_svg")
        raise RuntimeError("[Step 5] 엑셀 SVG 미발견")

    # Step 6: 1차 확인 모달 OK
    print("    [6/8] 1차 확인 모달 OK...")
    await page.wait_for_timeout(1000)
    for loc in [
        page.get_by_test_id("confirm-modal-ok"),
        page.get_by_role("button", name="확인"),
        page.get_by_role("button", name="OK"),
    ]:
        try:
            if await loc.count() > 0:
                await loc.first.click()
                await page.wait_for_timeout(1000)
                break
        except Exception:
            continue
    else:
        await save_error_debug(page, "wms_step6_confirm")
        raise RuntimeError("[Step 6] 확인 모달 OK 미발견")

    # Step 7: 범위 선택 — 전체 내용 다운로드
    print("    [7/8] '전체 내용 다운로드' 선택...")
    await page.wait_for_timeout(800)
    for loc in [
        page.get_by_text("전체 내용 다운로드", exact=True),
        page.get_by_text("전체 내용", exact=False),
        page.get_by_role("radio", name="전체 내용 다운로드"),
    ]:
        try:
            if await loc.count() > 0:
                await loc.first.click()
                await page.wait_for_timeout(500)
                break
        except Exception:
            continue
    else:
        await save_error_debug(page, "wms_step7_range")
        raise RuntimeError("[Step 7] 전체 내용 다운로드 옵션 미발견")

    # Step 8: 최종 다운로드
    print("    [8/8] 최종 다운로드 실행...")
    download_btn = page.get_by_role("button", name="다운로드", exact=True)
    if await download_btn.count() == 0:
        download_btn = page.get_by_role("button", name="내려받기")
    if await download_btn.count() == 0:
        await save_error_debug(page, "wms_step8_download_btn")
        raise RuntimeError("[Step 8] 다운로드 버튼 미발견")

    saved = await wait_and_save_download(
        page, trigger=download_btn.click, target_path=target_path, timeout_ms=120_000,
    )
    return saved


async def run_task_wms(page: Page) -> Path | None:
    """Task 3 실행."""
    print("\n" + "=" * 60)
    print("📋 Task 3: WMS 창고 전체 재고 조회 (ezstorage)")
    print("=" * 60)

    await _force_login(page)

    inventory_url = _build_wms_url(URL_PATHS["wms_inventory"], WMS_STOCK_PARAMS)
    target_path = INPUT_DIR / f"wms_inventory_{TODAY_STR}.xlsx"

    try:
        print(f"  📦 재고 페이지 이동...")
        await page.goto(inventory_url, wait_until="networkidle", timeout=30_000)
        await page.wait_for_timeout(3000)

        saved = await _run_query_and_download(page, target_path)
        print(f"  📥 WMS 재고 → {saved.name}")
        return saved

    except PlaywrightTimeoutError as e:
        print(f"  ❌ WMS 타임아웃: {e}")
        await save_error_debug(page, "wms_timeout")
        return None
    except RuntimeError as e:
        print(f"  ❌ WMS 파이프라인 중단: {e}")
        return None
    except Exception as e:
        print(f"  ❌ WMS 처리 실패: {e}")
        await save_error_debug(page, "wms_error")
        return None
