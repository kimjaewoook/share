@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:: 배치 파일이 위치한 폴더를 기준으로 경로 설정
pushd "%~dp0"

echo =========================================================
echo 📦 런드리고 지출결의서 봇 초기 환경 세팅을 시작합니다...
echo =========================================================
echo.

:: 1. 가상환경 생성
echo [1/3] 파이썬 가상환경(venv)을 생성합니다...
python -m venv venv
if errorlevel 1 (
    echo.
    echo ❌ 파이썬 가상환경 생성에 실패했습니다.
    echo    파이썬이 설치되어 있는지, 설치 시 'Add Python to PATH'에 체크했는지 확인해 주세요.
    echo.
    pause
    exit /b 1
)
echo    ✅ 가상환경 생성 완료
echo.

:: 2. 가상환경 활성화 및 라이브러리 설치
echo [2/3] 필수 라이브러리를 설치합니다...
call venv\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ❌ 라이브러리 설치에 실패했습니다. 인터넷 연결을 확인해 주세요.
    echo.
    pause
    exit /b 1
)
echo    ✅ 라이브러리 설치 완료
echo.

:: 3. Playwright 브라우저 바이너리 설치
echo [3/3] Playwright 전용 브라우저를 다운로드합니다... (약 1~2분 소요)
playwright install chromium
if errorlevel 1 (
    echo.
    echo ❌ Playwright 브라우저 설치에 실패했습니다.
    echo.
    pause
    exit /b 1
)
echo    ✅ 브라우저 설치 완료
echo.

echo =========================================================
echo ✅ 모든 초기 설정이 완료되었습니다!
echo    이제 '봇구동.bat' 파일을 더블클릭해서 봇을 실행하세요.
echo =========================================================
echo.

popd
pause
