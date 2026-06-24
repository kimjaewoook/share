@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:: 배치 파일이 위치한 폴더를 기준으로 경로 설정
pushd "%~dp0"

echo =========================================================
echo 🚀 런드리고 지출결의서 자동화 봇 구동을 시작합니다...
echo =========================================================
echo.

:: 가상환경 활성화
if not exist "venv\Scripts\activate.bat" (
    echo ❌ 가상환경(venv)이 발견되지 않았습니다.
    echo    먼저 '초기설정.bat'을 실행해 주세요.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

:: 봇 실행
python main.py

echo.
echo =========================================================
echo 봇 작업이 종료되었습니다. 아무 키나 누르면 창이 닫힙니다.
echo =========================================================

popd
pause
