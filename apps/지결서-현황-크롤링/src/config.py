import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Set base path
BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent.parent.parent  # {domain}/apps/{project}/ → ROOT

# Ensure .env is loaded
load_dotenv(find_dotenv())

# Set logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("laundrygo_gw")

def _get_required_env(key):
    val = os.getenv(key)
    if val is None:
        logger.error(f"CRITICAL: Environment variable '{key}' is missing in .env.")
        sys.exit(1)
    return val

# Environment Variables
LAUNDRYGO_GW_URL = _get_required_env("LAUNDRYGO_GW_URL")
LAUNDRYGO_GW_ID = _get_required_env("LAUNDRYGO_GW_ID")
LAUNDRYGO_GW_PW = _get_required_env("LAUNDRYGO_GW_PW")

# Google Sheets specific variables
SPREADSHEET_ID = _get_required_env("SPREADSHEET_ID")
SERVICE_ACCOUNT_FILE = Path(_get_required_env("GOOGLE_SHEETS_CREDENTIALS"))

if not SERVICE_ACCOUNT_FILE.exists():
    logger.error(f"CRITICAL: Service account json missing at {SERVICE_ACCOUNT_FILE}")
    sys.exit(1)

# App Paths
OUTPUT_DIR = BASE_DIR / "output"
ARCHIVE_DIR = BASE_DIR / "archive"

# Ensure dirs exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

# ── 아카이브 포맷 표준: YYYY-MM-DD(요일) ──
KOREAN_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]

def get_archive_dir() -> Path:
    """당일 아카이브 디렉토리 경로 반환 및 자동 생성."""
    import datetime
    now = datetime.datetime.now()
    weekday = KOREAN_WEEKDAYS[now.weekday()]
    archive_dir = ARCHIVE_DIR / f"{now.strftime('%Y-%m-%d')}({weekday})"
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir
