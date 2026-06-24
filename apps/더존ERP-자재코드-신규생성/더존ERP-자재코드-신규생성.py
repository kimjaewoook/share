"""
더존ERP 자재코드 신규생성 매크로
- 마스터 구글시트 '발주관리_단가테이블'에서 데이터를 읽어
- 더존ERP 품목등록 화면에 자동 키인
"""
import sys
import os
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv(Path(__file__).resolve().parents[2].parent / ".env")

from pynput.keyboard import Key, Controller, Listener
import gspread
from google.oauth2.service_account import Credentials

keyboard = Controller()
running = True

MASTER_SHEET_ID = "1BStqRHhmz6vIuR-S110BjeAhYyrkp_tkisAQLw6TkAo"


def on_press(key):
    global running
    if key == Key.esc:
        print("\n[🛑 중단] ESC 키가 입력되어 매크로를 종료합니다.")
        running = False
        return False


def clipboard_copy(text):
    """macOS 클립보드에 텍스트 복사"""
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)


def paste():
    """Ctrl+V 붙여넣기"""
    keyboard.press(Key.ctrl)
    keyboard.press("v")
    keyboard.release("v")
    keyboard.release(Key.ctrl)
    time.sleep(0.15)


def press_enter(times=1, delay=0.1):
    """엔터 입력"""
    for _ in range(times):
        if not running:
            break
        keyboard.press(Key.enter)
        keyboard.release(Key.enter)
        time.sleep(delay)


def type_text(text, delay=0.05):
    """텍스트 직접 타이핑 (OS 레벨)"""
    if not running:
        return
    keyboard.type(text)
    time.sleep(delay)


def fetch_items():
    """구글 시트에서 미등록 품목 가져오기"""
    print("[📡] 구글 시트에서 데이터 로딩 중...")
    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_SHEETS_CREDENTIALS"),
        scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    gc = gspread.authorize(creds)
    wb = gc.open_by_key(MASTER_SHEET_ID)
    ws = wb.worksheet("발주관리_단가테이블")
    all_values = ws.get_all_values()

    headers = all_values[1]  # Row 2 = 실제 헤더
    data = []
    for row in all_values[2:]:
        while len(row) < len(headers):
            row.append("")
        data.append(dict(zip(headers, row)))

    # 필터: 코드 2/3/4/5 시작, 더존입력완료=공백
    items = []
    for d in data:
        code = d.get("자재코드(구매)", "").strip()
        done = d.get("더존입력완료", "").strip()

        if not code or code[0] not in ("2", "3", "4", "5"):
            continue
        if done != "":
            continue

        items.append({
            "자재코드(구매)": code,
            "자재명": d.get("자재명", "").strip(),
            "공급업체명(정식)": d.get("공급업체명(정식)", "").strip(),
        })

    return items


def run_macro(items):
    """매크로 실행"""
    total = len(items)

    print(f"\n{'=' * 50}")
    print(f"  자재코드 신규생성 매크로")
    print(f"  대상: {total}건")
    print(f"  5초 뒤 키입력 시작 — ERP 화면에 커서를 위치시키세요")
    print(f"  종료: ESC 키")
    print(f"{'=' * 50}")

    # 5초 대기 (커서 위치 준비 시간)
    for i in range(5, 0, -1):
        if not running:
            return
        print(f"  {i}초...", flush=True)
        time.sleep(1)

    # ESC 리스너 시작
    listener = Listener(on_press=on_press)
    listener.start()

    for idx, item in enumerate(items, 1):
        if not running:
            break

        code = item["자재코드(구매)"]
        name = item["자재명"]
        supplier = item["공급업체명(정식)"]

        print(f"\n[{idx}/{total}] {code} | {name} | {supplier}")

        # 1. 자재코드(구매) 붙여넣기 → 엔터
        if not running: break
        clipboard_copy(code)
        time.sleep(0.1)
        paste()
        time.sleep(0.1)
        press_enter(1, 0.3)

        # 2. 자재명 붙여넣기 → 엔터
        if not running: break
        clipboard_copy(name)
        time.sleep(0.1)
        paste()
        time.sleep(0.1)
        press_enter(1, 0.3)

        # 3. 공급업체명(정식) 붙여넣기 → 엔터
        if not running: break
        clipboard_copy(supplier)
        time.sleep(0.1)
        paste()
        time.sleep(0.1)
        press_enter(1, 0.3)

        # 4. 아래방향키 2회 → 엔터 (드롭다운 항목 선택)
        if not running: break
        time.sleep(0.5)
        keyboard.press(Key.down)
        keyboard.release(Key.down)
        time.sleep(0.2)
        keyboard.press(Key.down)
        keyboard.release(Key.down)
        time.sleep(0.1)
        press_enter(1, 0.5)

        # 5. 아래방향키 2회 → 엔터 (드롭다운 항목 선택)
        if not running: break
        time.sleep(0.5)
        keyboard.press(Key.down)
        keyboard.release(Key.down)
        time.sleep(0.2)
        keyboard.press(Key.down)
        keyboard.release(Key.down)
        time.sleep(0.1)
        press_enter(1, 0.5)

        # 6. "EA" 입력 → 엔터 31회
        if not running: break
        type_text("EA")
        time.sleep(0.1)
        press_enter(31, 0.05)

        print(f"  ✅ 완료")
        time.sleep(0.5)  # 다음 자재코드 진입 전 대기

    listener.stop()

    if running:
        print(f"\n{'=' * 50}")
        print(f"  🎉 전체 {total}건 입력 완료!")
        print(f"{'=' * 50}")
    else:
        print(f"\n  ⚠️ {idx-1}/{total}건 완료 후 중단됨")


def main():
    items = fetch_items()

    if not items:
        print("\n[✅] 입력 대상이 없습니다. (모두 등록 완료)")
        return

    print(f"\n[📋] 입력 대상 목록 ({len(items)}건):")
    print(f"{'─' * 70}")
    for i, item in enumerate(items, 1):
        print(f"  {i:>3}. {item['자재코드(구매)']:<18} {item['자재명']:<35} {item['공급업체명(정식)']}")
    print(f"{'─' * 70}")

    confirm = input(f"\n위 {len(items)}건을 ERP에 입력합니다.\n  1. 실행\n  2. 취소\n선택: ")
    if confirm.strip() != "1":
        print("[취소됨]")
        return

    run_macro(items)


if __name__ == "__main__":
    main()
