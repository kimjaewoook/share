#!/bin/bash

# 설정: 실행하는 스크립트의 디렉토리로 이동
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 커머스 통합자동화 (E2E Pipeline)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 파이썬 확인 후 caffeinate로 슬립 방지하며 실행
if command -v python3 &>/dev/null; then
    caffeinate -i python3 "커머스-불출목록-취합.py"
elif command -v python &>/dev/null; then
    caffeinate -i python "커머스-불출목록-취합.py"
else
    echo "❌ Python이 설치되어 있지 않습니다."
    echo "   brew install python3 으로 설치 후 다시 실행해주세요."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  작업이 완료되었습니다."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "터미널을 종료하려면 아무 키나 누르세요..."
read -n 1 -s
