#!/bin/bash

# 카톡_발주메세지_생성.command
# 터미널에서 실행될 때 현재 경로를 ai 폴더 기준으로 맞춥니다.

# 스크립트가 위치한 디렉토리로 이동
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 파이썬 스크립트 실행
python3 카톡-발주메세지-생성.py
