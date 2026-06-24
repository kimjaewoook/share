#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
커머스 통합자동화 — 브라우저 유틸리티 (browser_utils.py)
Playwright persistent context, 세션 구움, 에러 캡처, 다운로드 대기
"""

from pathlib import Path
from typing import Callable, Awaitable

from playwright.async_api import (
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from config import BROWSER_PROFILE_DIR, INPUT_DIR, OUTPUT_DIR

_SESSION_MARKER = BROWSER_PROFILE_DIR / ".session_ready"


async def create_browser_context(pw: Playwright) -> BrowserContext:
    """Playwright persistent context 생성.

    downloads_path = INPUT_DIR → 다운로드 파일은 source/ 에 저장
    """
    context = await pw.chromium.launch_persistent_context(
        user_data_dir=str(BROWSER_PROFILE_DIR),
        headless=False,
        channel="chrome",
        accept_downloads=True,
        downloads_path=str(INPUT_DIR),
        viewport={"width": 1920, "height": 1080},
        locale="ko-KR",
        timezone_id="Asia/Seoul",
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
        ignore_default_args=["--enable-automation"],
    )
    return context


def is_first_run() -> bool:
    return not _SESSION_MARKER.exists()


def mark_session_ready() -> None:
    _SESSION_MARKER.write_text("ok", encoding="utf-8")


async def bake_session(page: Page) -> None:
    """최초 실행: 사용자 수동 로그인 대기."""
    print("\n" + "=" * 60)
    print("🍪 최초 실행 — 세션 구움(Session Baking) 모드")
    print("=" * 60)
    print("""
  지금 열린 Chrome 브라우저에서 아래 사이트들에 수동 로그인해 주세요:
    1) Metabase  (Google 계정)
    2) 런드리고 주문관리
    3) ezstorage (WMS)

  모두 로그인한 뒤, Playwright Inspector 창에서
  초록색 ▶ Resume 버튼을 누르면 자동화가 시작됩니다.
""")
    await page.pause()
    mark_session_ready()
    print("  ✅ 세션 저장 완료! 다음 실행부터는 자동 로그인됩니다.\n")


async def save_error_debug(page: Page, prefix: str = "error") -> None:
    """에러 시 스크린샷 + DOM 저장 (output/ 폴더에)."""
    try:
        screenshot_path = OUTPUT_DIR / f"{prefix}_screenshot.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"  📸 에러 스크린샷 → {screenshot_path.name}")
    except Exception as e:
        print(f"  [경고] 스크린샷 저장 실패: {e}")

    try:
        dom_path = OUTPUT_DIR / f"{prefix}_dom.html"
        content = await page.content()
        dom_path.write_text(content, encoding="utf-8")
        print(f"  📄 에러 DOM → {dom_path.name}")
    except Exception as e:
        print(f"  [경고] DOM 저장 실패: {e}")


async def wait_and_save_download(
    page: Page,
    trigger: Callable[[], Awaitable[None]],
    target_path: Path,
    timeout_ms: int = 60_000,
) -> Path:
    """다운로드 트리거 → 파일 저장."""
    async with page.expect_download(timeout=timeout_ms) as download_info:
        await trigger()
    download = await download_info.value
    await download.save_as(str(target_path))
    return target_path
