@echo off
chcp 65001 >nul
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   ★ 커머스 통합자동화 — 초기 세팅 시작
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

:: 파이썬 설치 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 🚨 Python이 설치되어 있지 않거나 PATH에 등록되지 않았습니다.
    echo    python.org 에서 Python을 설치하고 "Add Python to PATH"를 체크하세요.
    echo.
    pause
    exit /b 1
)

echo ✅ Python 확인 완료
python --version
echo.

:: pip 업그레이드
echo 📦 pip 업그레이드 중...
python -m pip install --upgrade pip
echo.

:: 필수 패키지 설치
echo 📦 필수 패키지 설치 중 (requirements.txt)...
python -m pip install -r "%~dp0requirements.txt"
echo.

:: Playwright 브라우저 설치
echo 🌐 Playwright 크롬 브라우저 설치 중...
python -m playwright install chromium
echo.

echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   ✅ 초기 세팅 완료!
echo   이제 run.bat 을 더블클릭하여 실행하세요.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
pause
