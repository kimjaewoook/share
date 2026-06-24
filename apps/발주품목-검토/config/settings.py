import os
from pathlib import Path
from dotenv import load_dotenv

# 루트 .env 경로 설정 및 로드
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR.parent.parent.parent / ".env" # ai/.env
load_dotenv(dotenv_path=ENV_PATH)

# 마스터 스프레드시트 ID
MASTER_PO_SPREADSHEET_ID = os.getenv("MASTER_PO_SPREADSHEET_ID")
if not MASTER_PO_SPREADSHEET_ID:
    raise ValueError("환경 변수 MASTER_PO_SPREADSHEET_ID 가 설정되지 않았습니다. ai/.env 파일을 확인해주세요.")

# Google API 인증 정보 경로
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

# 엑셀 출력 경로
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# 시트 이름 설정 (L1: 모든 Range를 A1:ZZ로 통일하여 열 누락 방지)
SHEET_RANGES = {
    "자재요청서": "'자재요청서_신청확인'!A1:ZZ",
    "단가테이블": "'발주관리_단가테이블'!A1:ZZ",
    "PO_LIST": "'발주관리_PO List'!A1:ZZ",
    "재고현황": "'장현석_재고현황'!A1:ZZ",
    "예상시점": "'재고소진예상시점'!A1:ZZ",
    "공급업체": "'공급업체관리'!A1:ZZ",
    "자재코드": "'자재코드 관리_자재코드 목록'!A1:ZZ",
}
