import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
커머스 통합자동화 — 메인 실행 (main.py)

Phase 1: 브라우저 자동화 (Task 1~3)
Phase 2: 데이터 가공 (Task 4)
Phase 3: 슬랙 메시지 생성 (Task 5)
Phase 4: 아카이브
"""

import asyncio
import shutil
import time
import traceback

from playwright.async_api import async_playwright

from config import TODAY_STR, DAY_KR, INPUT_DIR, ARCHIVE_DIR
from browser_utils import create_browser_context, is_first_run, bake_session
from task_metabase import run_task_metabase
from task_scm import run_task_scm
from task_wms import run_task_wms
from task_processor import run_processing
from slack_messenger import generate_slack_file


def _format_elapsed(seconds: float) -> str:
    mins, secs = divmod(int(seconds), 60)
    return f"{mins}분 {secs}초" if mins > 0 else f"{secs}초"


def _archive_source_files() -> None:
    """source/ 내 원본 파일을 archive/YYYY-MM-DD(요일)/ 로 이동."""
    moved = 0
    for f in INPUT_DIR.iterdir():
        if f.name.startswith('.') or f.is_dir():
            continue
        try:
            shutil.move(str(f), str(ARCHIVE_DIR / f.name))
            moved += 1
        except Exception as e:
            print(f"  ⚠️ 아카이브 실패 ({f.name}): {e}")

    if moved > 0:
        print(f"\n  📦 {moved}개 원본 파일 → archive/{ARCHIVE_DIR.name}/")
    else:
        print("\n  ℹ️ 아카이브할 파일 없음")


async def main() -> None:
    """E2E 파이프라인: 크롤링 → 데이터 가공 → 슬랙 메시지 → 아카이브."""
    print("=" * 60)
    print(f"🚀 커머스 통합자동화 시작 — {TODAY_STR}({DAY_KR})")
    print("=" * 60)

    start = time.time()
    towel_results: dict[str, int] = {"성수": 0, "군포": 0}

    # ════════════════════════════════════════════
    # Phase 1: 브라우저 자동화 (Task 1~3)
    # ════════════════════════════════════════════
    async with async_playwright() as pw:
        context = await create_browser_context(pw)
        page = await context.new_page()

        try:
            if is_first_run():
                await bake_session(page)

            # Task 1: 호텔 수건 → 반환값 저장
            towel_results = await run_task_metabase(page)

            # Task 2: 런드리고 주문관리 → source/
            await run_task_scm(page)

            # Task 3: WMS 재고 → source/
            await run_task_wms(page)

        except Exception as e:
            print(f"\n❌ 브라우저 작업 중 치명적 오류: {e}")
            traceback.print_exc()
        finally:
            await context.close()

    # ════════════════════════════════════════════
    # Phase 2: 데이터 가공 (Task 4)
    # ════════════════════════════════════════════
    success = False
    output_path = None
    try:
        success, output_path = run_processing()
    except Exception as e:
        print(f"\n❌ 데이터 가공 실패: {e}")
        traceback.print_exc()

    # ════════════════════════════════════════════
    # Phase 3: 슬랙 메시지 생성 (Task 5)
    # ════════════════════════════════════════════
    if success and output_path and output_path.exists():
        try:
            generate_slack_file(output_path, towel_results)
        except Exception as e:
            print(f"\n⚠️ 슬랙 메시지 생성 실패: {e}")
            traceback.print_exc()

    # ════════════════════════════════════════════
    # Phase 4: 아카이브
    # ════════════════════════════════════════════
    if success:
        _archive_source_files()

    elapsed = _format_elapsed(time.time() - start)
    print(f"\n{'=' * 60}")
    print(f"🏁 전체 작업 완료 — 소요 시간: {elapsed}")
    print(f"{'=' * 60}")

    while True:
        choice = input("\n작업이 완료되었습니다. [1] output 폴더 열기 / [2] 종료 : ")
        if choice == '1':
            import os
            out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
            if os.path.exists(out_dir):
                os.system(f"open '{out_dir}'")
            else:
                print(f"⚠️ output 폴더를 찾을 수 없습니다: {out_dir}")
            break
        elif choice == '2':
            break
        else:
            print("1 또는 2를 입력해주세요.")


if __name__ == "__main__":
    asyncio.run(main())
