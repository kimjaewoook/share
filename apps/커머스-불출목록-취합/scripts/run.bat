@echo off
chcp 65001 >nul
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   🚀 커머스 통합자동화 (E2E Pipeline)
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

:: 스크립트 위치로 이동
cd /d "%~dp0"

:: 파이썬 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 🚨 Python이 설치되어 있지 않습니다.
    echo    먼저 setup.bat 을 실행하세요.
    echo.
    pause
    exit /b 1
)

:: main.py 실행
python main.py

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   작업이 완료되었습니다.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo 터미널을 종료하려면 아무 키나 누르세요...
pause >nul
