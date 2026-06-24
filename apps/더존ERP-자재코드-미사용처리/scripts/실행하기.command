#!/bin/bash
# 실행되는 스크립트의 위치로 이동합니다.
cd "$(dirname "$0")"

# pynput 패키지가 설치되어 있는지 확인하고 없으면 설치합니다.
python3 -c "import pynput" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "초기 설정 중입니다. 필요한 패키지를 설치합니다..."
    pip3 install pynput
fi

# 파이썬 스크립트 실행
python3 "../더존ERP-자재코드-미사용처리.py"

echo ""
echo "프로그램이 종료되었습니다. 창을 닫으셔도 됩니다."
