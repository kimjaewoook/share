#!/bin/bash
# ──────────────────────────────────────────────
# Laundrygo 지출결의서 상신 봇 — macOS 런처
# ──────────────────────────────────────────────
cd "$(dirname "$0")"

echo "========================================================="
echo "🚀 런드리고 지출결의서 자동화 봇 (Antigravity) 구동 시작..."
echo "========================================================="

# [방어 1] Python3 설치 확인
if ! command -v python3 &> /dev/null; then
    echo ""
    echo "❌ python3 가 설치되어 있지 않습니다."
    echo "   Homebrew: brew install python3"
    echo ""
    read -p "아무 키나 눌러 종료..."
    exit 1
fi

# [방어 2] 메인 스크립트 존재 확인
SCRIPT_NAME="지출결의서-상신.py"
if [ ! -f "$SCRIPT_NAME" ]; then
    echo ""
    echo "❌ '$SCRIPT_NAME' 파일을 찾을 수 없습니다."
    echo "   현재 경로: $(pwd)"
    echo ""
    read -p "아무 키나 눌러 종료..."
    exit 1
fi

# [방어 3] macOS 절전 방지 (caffeinate)
caffeinate -dims &
CAFFEINE_PID=$!

# 메인 스크립트 실행
python3 "$SCRIPT_NAME"
EXIT_CODE=$?

# caffeinate 종료
kill $CAFFEINE_PID 2>/dev/null

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 프로그램이 정상적으로 종료되었습니다."
else
    echo "⚠️ 프로그램이 비정상 종료되었습니다. (종료 코드: $EXIT_CODE)"
fi

echo ""
read -p "아무 키나 눌러 터미널을 닫으세요..."
