#!/bin/bash
# 발주품목검토 파이썬 스크립트 실행 런처

# 스크립트가 위치한 디렉토리로 이동
cd "$(dirname "$0")"

# 공통 환경변수 로드 (.env 파일이 존재하는 경우)
ENV_PATH="../../.env"
if [ -f "$ENV_PATH" ]; then
    export $(grep -v '^#' "$ENV_PATH" | xargs)
fi

echo "🚀 발주품목검토 자동화 스크립트를 실행합니다..."
python3 발주품목-검토.py

echo ""
echo "✅ 실행이 완료되었습니다. 창을 닫으셔도 됩니다."
read -p "Press enter to continue..."
