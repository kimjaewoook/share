#!/bin/bash
# 런드리고 그룹웨어 웹 자동화 및 Slack 메시지 추출 실행 파일

echo "=================================================="
echo "    Laundrygo Groupware Crawler Tracking Agent    "
echo "=================================================="
echo ""

# 스크립트의 실행 경로 동적 획득
cd "$(dirname "$0")"

# 스크립트 실행
python3 "지결서-현황-크롤링.py"

read -p "아무 키나 누르면 터미널이 종료됩니다..." -n 1 -r
exit 0
