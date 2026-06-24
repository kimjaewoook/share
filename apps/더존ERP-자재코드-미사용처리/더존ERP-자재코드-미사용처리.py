import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import time
from pynput.keyboard import Key, Controller, Listener

keyboard = Controller()
running = True

def on_press(key):
    global running
    if key == Key.esc:
        print("\n[안내] ESC 키가 입력되어 매크로를 종료합니다.")
        running = False
        return False  # 리스너 종료

def press_key(key, times=1, delay=0.2):
    global running
    for _ in range(times):
        if not running:
            break
        
        # 문자열인 경우와 Key 객체인 경우를 구분해서 입력
        keyboard.press(key)
        keyboard.release(key)
        print(f"[{time.strftime('%X')}] '{key}' 입력됨")
        
        # 지정된 대기 시간만큼 대기
        time.sleep(delay)

def main():
    print("=" * 40)
    print("자재코드 미사용처리 매크로가 실행되었습니다.")
    print("3초 뒤에 키입력이 시작됩니다...")
    print("종료하시려면 언제든지 'ESC' 키를 누르세요.")
    print("=" * 40)
    
    # 3초 대기
    time.sleep(3)
    
    # ESC 키 감지를 위한 리스너 시작
    listener = Listener(on_press=on_press)
    listener.start()

    print("\n[안내] 미사용처리 매크로 시작됨 동작 중...")
    
    # 동작 무한 반복
    while running:
        # 1. 탭 1회 입력 (0.2초 대기)
        if running: press_key(Key.tab, 1, 0.1)
        
        # 2. 엔터 9회 입력 (0.2초 대기)
        if running: press_key(Key.enter, 9, 0.1)
        
        # 3. 아래 화살표 한번 입력 (0.2초 대기)
        if running: press_key(Key.down, 1, 0.2)
        
        # 4. 위 화살표 한번 입력 (0.2초 대기)
        if running: press_key(Key.up, 1, 0.2)
        
        # 5. 엔터 한번 입력 (0.5초 대기)
        if running: press_key(Key.enter, 1, 0.2)
        
        # 6. 엔터 24회 입력 (0.2초 대기)
        if running: press_key(Key.enter, 24, 0.1)

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
    main()
    archive_data()
