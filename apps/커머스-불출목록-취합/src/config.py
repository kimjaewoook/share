#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
커머스 통합자동화 — 설정 (config.py)
환경변수 로드, URL 관리, 경로·날짜 상수 중앙 통제
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

from dotenv import load_dotenv, find_dotenv

# ──────────────────────────── 환경변수 로드 ────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(find_dotenv())

# ──────────────────────────── 필수 환경변수 검증 ────────────────────────────
_REQUIRED_KEYS = [
    "METABASE_URL",
    "LAUNDRYGO_ORDER_URL",
    "LAUNDRYGO_ORDER_ID",
    "LAUNDRYGO_ORDER_PW",
    "WMS_EZSTORAGE_URL",
    "WMS_EZSTORAGE_ID",
    "WMS_EZSTORAGE_PW",
]

for _key in _REQUIRED_KEYS:
    if os.getenv(_key) is None:
        sys.exit(
            f"[Error] 환경변수 '{_key}' 누락 — "
            f"'.env' 파일을 확인하세요."
        )

# ──────────────────────────── 환경변수 바인딩 ────────────────────────────
METABASE_URL: str = os.getenv("METABASE_URL")
SCM_URL: str = os.getenv("LAUNDRYGO_ORDER_URL")
SCM_ID: str = os.getenv("LAUNDRYGO_ORDER_ID")
SCM_PW: str = os.getenv("LAUNDRYGO_ORDER_PW")
WMS_URL: str = os.getenv("WMS_EZSTORAGE_URL")
WMS_ID: str = os.getenv("WMS_EZSTORAGE_ID")
WMS_PW: str = os.getenv("WMS_EZSTORAGE_PW")

# ──────────────────────────── URL 경로 관리 ────────────────────────────
URL_PATHS: dict[str, str] = {
    "metabase_hotel_towel": "/question/4756",
    "scm_release": "/lg_groupware/react/product-order-management/release",
    "wms_inventory": "/stock-list",
}

WMS_STOCK_PARAMS = "tab=0&page=1&page-size=50"


def build_url(base: str, path_key: str, **params: str) -> str:
    """Base URL과 경로 키를 결합하여 전체 URL 생성."""
    url = urljoin(base.rstrip("/") + "/", URL_PATHS[path_key].lstrip("/"))
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url += f"?{query}"
    return url


# ──────────────────────────── 날짜 상수 ────────────────────────────
_NOW = datetime.now()
_DAY_MAP = ["월", "화", "수", "목", "금", "토", "일"]

TODAY_STR = _NOW.strftime("%Y-%m-%d")          # 2026-03-29
TODAY_COMPACT = _NOW.strftime("%Y%m%d")        # 20260329
DAY_KR = _DAY_MAP[_NOW.weekday()]             # 일
YESTERDAY_STR = (_NOW - timedelta(days=1)).strftime("%Y-%m-%d")

# ──────────────────────────── 경로 상수 ────────────────────────────
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
ARCHIVE_DIR = BASE_DIR / "archive" / f"{TODAY_STR}({DAY_KR})"
TEMPLATES_DIR = BASE_DIR / "templates"
BROWSER_PROFILE_DIR = BASE_DIR / ".playwright_profile"

for _dir in (INPUT_DIR, OUTPUT_DIR, ARCHIVE_DIR, TEMPLATES_DIR, BROWSER_PROFILE_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
