#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
커머스 통합자동화 — Task 2: 커머스 출고대상 리스트 다운로드 (런드리고 주문관리)

다운로드 경로: INPUT_DIR (source/ 폴더)
"""

from pathlib import Path

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from config import SCM_URL, SCM_ID, SCM_PW, TODAY_STR, INPUT_DIR, build_url
from browser_utils import save_error_debug, wait_and_save_download

FACTORIES = ["성수", "군포"]


async def _ensure_scm_login(page: Page) -> None:
    """런드리고 주문관리 로그인 확인 + 자동 로그인."""
    target_url = build_url(SCM_URL, "scm_release")
    await page.goto(target_url, wait_until="networkidle", timeout=30_000)
    await page.wait_for_timeout(2000)

    current = page.url.lower()
    if "login" not in current and "sign" not in current:
        print("  ✅ 런드리고 주문관리 세션 유효 — 로그인 생략")
        return

    print("  🔑 런드리고 주문관리 로그인 진행 중...")
    try:
        id_candidates = [
            page.get_by_placeholder("아이디"),
            page.get_by_placeholder("ID"),
            page.locator("input[name='username']").first,
            page.locator("input[name='id']").first,
            page.locator("input[type='text']").first,
        ]
        for loc in id_candidates:
            if await loc.count() > 0:
                await loc.fill(SCM_ID)
                break

        pw_candidates = [
            page.get_by_placeholder("비밀번호"),
            page.get_by_placeholder("Password"),
            page.locator("input[type='password']").first,
        ]
        for loc in pw_candidates:
            if await loc.count() > 0:
                await loc.fill(SCM_PW)
                break

        btn_candidates = [
            page.get_by_role("button", name="로그인"),
            page.get_by_role("button", name="Login"),
            page.locator("button[type='submit']").first,
        ]
        for loc in btn_candidates:
            if await loc.count() > 0:
                await loc.click()
                break

        await page.wait_for_timeout(3000)
        print("  ✅ 런드리고 주문관리 로그인 완료")

    except Exception as e:
        print(f"  ❌ 런드리고 주문관리 로그인 실패: {e}")
        await save_error_debug(page, "주문관리_login")
        raise


async def _select_factory_filter(page: Page, factory_name: str) -> None:
    """공장 라디오 버튼 선택 (4단계 폴백)."""
    for radio in [
        page.get_by_role("radio", name=f"{factory_name}"),
        page.get_by_role("radio", name=f"{factory_name}공장"),
        page.get_by_role("radio", name=f"{factory_name}팩토리"),
    ]:
        try:
            if await radio.count() > 0:
                await radio.click()
                await page.wait_for_timeout(500)
                return
        except Exception:
            continue

    for label in [
        page.get_by_label(f"{factory_name}"),
        page.get_by_label(f"{factory_name}공장"),
    ]:
        try:
            if await label.count() > 0:
                await label.click()
                await page.wait_for_timeout(500)
                return
        except Exception:
            continue

    try:
        radios = page.locator("input[type='radio']")
        for i in range(await radios.count()):
            parent_text = await radios.nth(i).locator("..").inner_text()
            if factory_name in parent_text:
                await radios.nth(i).click()
                await page.wait_for_timeout(500)
                return
    except Exception:
        pass

    try:
        text_el = page.get_by_text(factory_name, exact=False)
        if await text_el.count() > 0:
            await text_el.first.click()
            await page.wait_for_timeout(500)
    except Exception:
        pass


async def _has_data(page: Page) -> bool:
    """조회 결과가 있는지 판별."""
    for txt in ["조회된 데이터가 없습니다", "데이터가 없습니다", "검색 결과가 없습니다", "No data"]:
        if await page.get_by_text(txt).count() > 0:
            return False
    return await page.locator(
        "table tbody tr, .ag-center-cols-container .ag-row, [class*='row'][class*='data']"
    ).count() > 0


async def _download_factory_release(page: Page, factory_name: str) -> Path | None:
    """팩토리별 출고대상 엑셀 다운로드 → source/ 저장."""
    await page.goto(build_url(SCM_URL, "scm_release"), wait_until="networkidle", timeout=30_000)
    await page.wait_for_timeout(2000)

    try:
        await _select_factory_filter(page, factory_name)
    except Exception as e:
        print(f"    ⚠️ {factory_name} 필터 설정 실패: {e}")
        await save_error_debug(page, f"scm_filter_{factory_name}")

    try:
        search_btn = page.get_by_role("button", name="조회")
        if await search_btn.count() == 0:
            search_btn = page.get_by_role("button", name="검색")
        if await search_btn.count() > 0:
            await search_btn.click()
            await page.wait_for_timeout(3000)
    except Exception:
        pass

    if not await _has_data(page):
        print(f"  ℹ️ {factory_name}팩토리 커머스 주문내역 없음")
        return None

    target_path = INPUT_DIR / f"product_release_{factory_name}_{TODAY_STR}.xlsx"
    try:
        download_btn = page.get_by_role("button", name="엑셀 다운로드")
        if await download_btn.count() == 0:
            download_btn = page.get_by_role("button", name="엑셀")
        if await download_btn.count() == 0:
            download_btn = page.get_by_role("button", name="Excel")
        if await download_btn.count() == 0:
            download_btn = page.get_by_role("button", name="다운로드")

        await wait_and_save_download(page, trigger=download_btn.click, target_path=target_path)
        print(f"  📥 {factory_name} 출고대상 → {target_path.name}")
        return target_path

    except PlaywrightTimeoutError:
        print(f"  ❌ {factory_name} 엑셀 다운로드 타임아웃")
        await save_error_debug(page, f"scm_download_{factory_name}")
        return None


async def run_task_scm(page: Page) -> list[Path]:
    """Task 2 실행."""
    print("\n" + "=" * 60)
    print("📋 Task 2: 커머스 출고대상 리스트 다운로드 (런드리고 주문관리)")
    print("=" * 60)

    await _ensure_scm_login(page)

    downloaded: list[Path] = []
    for factory in FACTORIES:
        try:
            result = await _download_factory_release(page, factory)
            if result:
                downloaded.append(result)
        except Exception as e:
            print(f"  ❌ {factory}팩토리 처리 실패: {e}")
            await save_error_debug(page, f"scm_{factory}")

    print(f"\n  📊 다운로드 결과: {len(downloaded)}개 파일")
    return downloaded
