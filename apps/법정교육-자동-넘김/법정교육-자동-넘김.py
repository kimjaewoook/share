import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import asyncio
import time
from playwright.async_api import async_playwright

# --- 설정 정보 (필요 시 수정) ---
BASE_URL = "https://lifegoesonedu.esafetykorea.or.kr"
NEXT_BUTTON_SELECTOR = "button.next"
CHECK_QUIZ_TEXT = "정답 확인"

async def auto_education():
    async with async_playwright() as p:
        # 브라우저 실행 (탐지 방지를 위해 자동화 표시 제거)
        print("[*] 자동화 탐지 우회 설정을 적용하여 브라우저를 실행합니다...")
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ]
        )
        # 자동화 탐지용 navigator.webdriver 속성 무효화
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # 스크립트 실행 시 navigator.webdriver 속성을 false로 덮어쓰기
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()

        print(f"[*] {BASE_URL} 접속 중...")
        await page.goto(BASE_URL)

        print("\n" + "="*50)
        print(" [ 지침 ]")
        print(" 1. 새로 뜬 브라우저 창에서 직접 로그인을 완료해 주세요.")
        print(" 2. '나의 강의실'로 이동하여 수강할 강의의 '학습하기'를 클릭해 주세요.")
        print(" 3. 강의 플레이어(팝업)가 뜨면 이 스크립트가 자동으로 감지하고 시작합니다.")
        print("="*50 + "\n")

        # 1. 플레이어 팝업창 감지 대기
        player_page = None
        while not player_page:
            for p_page in context.pages:
                # URL에 player가 포함된 팝업창을 찾음
                if "/player" in p_page.url:
                    player_page = p_page
                    break
            if not player_page:
                await asyncio.sleep(2)
        
        print(f"[+] 플레이어 감지 성공! (URL: {player_page.url})")
        print("[*] 지금부터 자동화를 시작합니다. '다음' 버튼과 퀴즈를 감시합니다.")
        await player_page.bring_to_front()

        # 2. 자동화 루프
        while True:
            try:
                # 팝업창 유효성 체크
                if player_page.is_closed():
                    print("[!] 플레이어 창이 닫혔습니다.")
                    break

                # '다음' 버튼 활성화 여부 체크 및 클릭
                next_btn = player_page.locator(NEXT_BUTTON_SELECTOR)
                if await next_btn.is_visible() and await next_btn.is_enabled():
                    print("[>] '다음' 버튼이 활성화되어 클릭합니다.")
                    await next_btn.click()
                    await asyncio.sleep(2) # 클릭 후 대기

                # 퀴즈 감지 및 알려진 정답 자동 선택
                # (24페이지 퀴즈 예시)
                content = await player_page.content()
                if "동성 간에도 발생할 수 있다" in content:
                    # 'O' 버튼 클릭 시도
                    try:
                        print("[!] 24p 퀴즈 감지: 'O' 선택 및 제출")
                        await player_page.click('text="O"')
                        await asyncio.sleep(1)
                        await player_page.click(f'text="{CHECK_QUIZ_TEXT}"')
                        await asyncio.sleep(1)
                        await player_page.click('text="다음"')
                    except:
                        pass

                # 비디오가 종료되었는지 체크 (video tag의 ended 속성)
                video_ended = await player_page.evaluate("() => document.querySelector('video')?.ended")
                if video_ended:
                    print("[V] 영상 종료 감지 -> '다음' 페이지 이동 시도")
                    if await next_btn.is_visible():
                        await next_btn.click()

                # 5초마다 상태 체크
                await asyncio.sleep(5)

            except Exception as e:
                # 브라우저나 페이지가 닫히는 등의 오류 발생 시 종료
                if "Target page, context or browser has been closed" in str(e):
                    print("[!] 브라우저 또는 플레이어 창이 닫혀 프로그램을 종료합니다.")
                    break
                # 기타 일시적인 오류는 출력 후 계속 진행
                print(f"[-] 모니터링 중 알 수 없는 상태 (계속 대기): {e}")
                await asyncio.sleep(5)

def archive_data():
    from datetime import datetime
    import shutil
    
    KOREAN_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]
    now = datetime.now()
    weekday = KOREAN_WEEKDAYS[now.weekday()]
    archive_dir = Path(__file__).resolve().parent / "archive" / f"{now.strftime('%Y-%m-%d')}({weekday})"
    
    input_dir = Path(__file__).resolve().parent / "input"
    output_dir = Path(__file__).resolve().parent / "output"
    
    if not input_dir.exists() and not output_dir.exists():
        return

    archive_dir.mkdir(parents=True, exist_ok=True)
    
    for d in [input_dir, output_dir]:
        if d.exists():
            for item in d.iterdir():
                if item.is_file():
                    dest = archive_dir / item.name
                    if dest.exists():
                        dest = archive_dir / f"{item.stem}_{now.strftime('%H%M%S')}{item.suffix}"
                    shutil.move(str(item), str(dest))
            # Clean up source dir if it was processed
            if d == input_dir:
                for item in d.iterdir():
                    if item.is_file():
                        item.unlink()

if __name__ == "__main__":
    try:
        asyncio.run(auto_education())
    except KeyboardInterrupt:
        print("\n[!] 사용자에 의해 프로그램이 중단되었습니다.")
    finally:
        archive_data()
