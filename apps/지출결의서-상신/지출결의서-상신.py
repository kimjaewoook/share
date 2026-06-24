import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import re
import shutil
import urllib.parse
import datetime
import time
from dotenv import load_dotenv, find_dotenv

import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from playwright.sync_api import sync_playwright

# ----------------------------------------------------------------
# Environment 로딩 및 File System 설정
# ----------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(find_dotenv())

BASE_URL = os.getenv("LAUNDRYGO_GW_URL")
END_OF_MONTH_SHEET_URL = os.getenv("END_OF_MONTH_SHEET_URL")
GW_ID = os.getenv("LAUNDRYGO_GW_ID")
GW_PW = os.getenv("LAUNDRYGO_GW_PW")

# 1차 환경변수 방어 로직 (방어막)
if not all([BASE_URL, END_OF_MONTH_SHEET_URL, GW_ID, GW_PW]):
    print("\n❌ 환경 변수 세팅 에러: 최상위 폴더의 `.env` 파일에 필수 값(END_OF_MONTH_SHEET_URL, LAUNDRYGO_GW_ID 등)이 누락되었습니다. 파일을 확인해 주세요.\n")
    sys.exit(1)

PATHS = {
    "login": urllib.parse.urljoin(BASE_URL, "/login?returnUrl=%2Fapp%2Fhome"),
    "new_doc": urllib.parse.urljoin(BASE_URL, "/app/approval/document/new/324/1181")
}

KOREAN_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]

def setup_directories():
    """output 로테이션 + archive 폴더 동적 생성"""
    output_dir = BASE_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    now = datetime.datetime.now()
    weekday = KOREAN_WEEKDAYS[now.weekday()]
    archive_dir = BASE_DIR / "archive" / f"{now.strftime('%Y-%m-%d')}({weekday})"
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    # 데이터 로테이션: output 기존 파일 → archive 이동 (중복 시 타임스탬프 보존)
    for f in output_dir.iterdir():
        if f.is_file():
            dst = archive_dir / f.name
            if dst.exists():
                ts = now.strftime("%H%M%S")
                dst = archive_dir / f"{f.stem}_{ts}{f.suffix}"
            shutil.move(str(f), str(dst))
    
    return output_dir, archive_dir

# ----------------------------------------------------------------
# Data Loading (Zero-Hardcoding)
# ----------------------------------------------------------------
def load_sheet_data():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds = None
    creds_path = Path(os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"))
    token_path = BASE_DIR / "config" / "token.json"

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    gc = gspread.authorize(creds)
    sheet = gc.open_by_url(END_OF_MONTH_SHEET_URL).worksheet("월말 정산업무FORM")
    
    # 지급일자 N6, N18 (문자열 자체 보존 -> re 모듈에 넘기기 위함)
    common_data = {
        "pay_day_raw": str(sheet.acell("N6").value or "").strip(),
        "evidence_date": str(sheet.acell("N18").value or "").strip(),
        "client_name": str(sheet.acell("C4").value or "").strip(),
        "client_code": str(sheet.acell("C5").value or "").strip(),
        "subject": sheet.acell("O6").value or "",
        "bank_name": sheet.acell("O11").value or "",
        "bank_account": sheet.acell("O12").value or "",
        "account_holder": sheet.acell("O13").value or ""
    }

    if not common_data["evidence_date"]:
        print("\n❌ 필수 데이터 누락 에러: 구글 시트의 N18 셀에 증빙일자가 입력되지 않았습니다. 날짜를 입력한 후 다시 실행해 주세요.\n")
        sys.exit(1)

    body_table_raw = sheet.get("B7:J")
    body_table = [row for row in body_table_raw if row and any(cell.strip() for cell in row)]
    common_data["body_table"] = body_table

    all_values = sheet.get_all_values()
    target_rows = []
    
    for row in all_values[19:]:
        if len(row) > 14 and str(row[14]).strip(): # O열 존재 시
            basic_summary_text = str(row[13]).strip()
            
            target_rows.append({
                "basic_summary": basic_summary_text,                             # N열
                "details": str(row[14]).strip(),                                 # O열
                "supply_amount": str(row[15]).strip() if len(row) > 15 else "",  # P열
                "vat": str(row[16]).strip() if len(row) > 16 else "",            # Q열
                "dept_code": str(row[11]).strip() if len(row) > 11 else "",      # L열
            })

    return common_data, target_rows

# ----------------------------------------------------------------
# JQuery UI Datepicker 매핑 컨트롤러
# ----------------------------------------------------------------
def handle_jquery_datepicker(page, date_str):
    """정규식을 활용해 날짜를 추출하고 select / click을 제어합니다."""
    matches = re.findall(r'\d+', date_str)
    if len(matches) >= 3:
        yyyy = matches[0]
        mm = matches[1]
        dd = matches[2]
        
        # jQuery 달력의 월(Month)은 0부터 시작하므로 -1 처리
        month_index = int(mm) - 1
        
        page.locator(".ui-datepicker-year").select_option(value=yyyy)
        page.locator(".ui-datepicker-month").select_option(value=str(month_index))
        # 날짜의 경우 "05"라도 `5`로 인식되게끔 int형 변환 후 포맷팅
        page.locator(f"a.ui-state-default:text-is('{int(dd)}')").click()
    else:
        print(f"⚠️ 달력 날짜 형식을 인식할 수 없습니다: {date_str} (건너뜀)")

# ----------------------------------------------------------------
# HTML 본문 조립 (DEXT5 Editor)
# ----------------------------------------------------------------
def build_body_html(table_data):
    if not table_data:
        return ""

    html_parts = []
    html_parts.append("<p>표제와 같이 세탁용 원부자재 구매 건의 지출결의 품의를 상신하오니, 검토 후 재가 부탁드립니다.<br>구매 내역은 아래와 같습니다.</p>")
    html_parts.append("<br><br>")
    html_parts.append('<p style="text-align: center;">- 아&nbsp;&nbsp;&nbsp;&nbsp;래 -</p>')
    
    html_parts.append('<table border="1" style="border-collapse: collapse; width: 100%; font-size: 10pt; text-align: center;">')
    
    # 헤더 (첫 번째 행)
    header = table_data[0]
    html_parts.append("<tr>")
    for cell in header:
        html_parts.append(f'<th style="background-color: #f2f2f2; padding: 5px;">{cell}</th>')
    html_parts.append("</tr>")
    
    # 데이터 행
    for row in table_data[1:]:
        html_parts.append("<tr>")
        for i in range(len(header)):
            cell_data = row[i] if i < len(row) else ""
            html_parts.append(f'<td style="padding: 5px;">{cell_data}</td>')
        html_parts.append("</tr>")
        
    html_parts.append("</table>")
    
    return "".join(html_parts)

# ----------------------------------------------------------------
# Main Playwright Flow
# ----------------------------------------------------------------
def run_automation():
    if not GW_ID or not GW_PW:
        raise ValueError("❌ 환경 변수(.env)에 LAUNDRYGO_GW_ID 또는 LAUNDRYGO_GW_PW가 설정되어 있지 않습니다.")

    output_dir, archive_dir = setup_directories()
    print("구글 시트 데이터 로딩 중...")
    common_data, target_rows = load_sheet_data()
    
    if not target_rows:
        print("작성할 지출결의서 내역(O열 데이터)이 없습니다.")
        return

    print("=" * 60)
    print("📋 [결재 상신 데이터 미리보기]")
    print("=" * 60)
    print(f"🔹 결의서 제목 : {common_data['subject']}")
    print(f"🔹 공통 지급일자 : {common_data['pay_day_raw']}")
    print(f"🔹 공통 증빙일자 : {common_data['evidence_date']}")
    print(f"🔹 거래처 : {common_data['client_name']} (코드: {common_data['client_code']})")
    print(f"🔹 송금 계좌 : {common_data['bank_name']} / {common_data['bank_account']} / {common_data['account_holder']}")
    print("-" * 60)
    print(f"📑 처리할 지출 내역 (총 {len(target_rows)}건)")
    
    for i, row in enumerate(target_rows):
        print(f"  [{i+1}] 부서: {row['dept_code']} | 공급가: {row['supply_amount']} | 적요: {row['basic_summary']}")
        
    print("=" * 60)
    print("(안내) 3초 후 브라우저 제어를 시작합니다...\n")
    time.sleep(3)

    print("Playwright 웹 제어 시작...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 1. 로그인 (networkidle 절대 배제)
            page.goto(PATHS["login"])
            page.locator("#username").fill(GW_ID)
            page.locator("#password").fill(GW_PW)
            page.locator("#login_submit").click()
            # 1. 홈 화면으로 리다이렉트 될 때까지 대기 (로그인 DB 처리 및 쿠키 발급 시간 확보)
            page.wait_for_url("**/app/home*", timeout=15000)
            # 2. 세션/쿠키가 브라우저에 완전히 안착하도록 1초 추가 하드 슬립
            page.wait_for_timeout(1000)
            
            # 신규 문서 페이지
            page.goto(PATHS["new_doc"])
            page.wait_for_load_state("load")

            # 에디터 본문 주입 (Cross-frame)
            if common_data.get("body_table"):
                body_html = build_body_html(common_data["body_table"])
                
                # 조립된 body_html 주입을 위해 DEXT5 에디터 프레임이 완전 렌더링될 때까지 넉넉히 대기
                page.wait_for_timeout(3000)
                
                try:
                    # 1. 동적 ID를 잡기 위해 'dext_frame_'으로 시작하는 바깥쪽 프레임 타겟팅
                    # 2. 그 내부의 안쪽 iframe 타겟팅
                    # 3. 최종적으로 #dext_body 타겟팅
                    dext_body = page.frame_locator("iframe[id^='dext_frame_']").frame_locator("iframe").locator("#dext_body")
                    
                    # 요소가 DOM에 완전히 붙을 때까지 대기
                    dext_body.wait_for(state="attached", timeout=10000)
                    
                    # HTML 주입
                    dext_body.evaluate("(el, html) => el.innerHTML = html", body_html)
                    print("✅ 본문 에디터(DEXT5) 표 데이터 주입 완료")
                except Exception as e:
                    print(f"⚠️ 에디터 주입 실패: {e}")

            # 2. 기본정보 (제목 & 지급일자)
            page.locator("#subject").fill(common_data["subject"])
            
            pay_day_raw = common_data["pay_day_raw"]
            if pay_day_raw:
                page.locator("#editorForm_9").click()
                handle_jquery_datepicker(page, pay_day_raw)

            # 3. 데이터 시트 행별 반복 주입 루프
            for i, row_data in enumerate(target_rows):
                n = i + 1  
                
                page.locator("#plusRow").click()

                # 증빙일자 달력 제어 (N18 공통)
                page.locator(f"#slipBplTable_{n}_3").click()
                handle_jquery_datepicker(page, common_data["evidence_date"])

                # 필드 주입 및 증빙유형(select) 선택
                # [오타 확인 완] slipBplTableselect{n}_1
                page.locator(f"#slipBplTableselect{n}_1").select_option(label="세금계산서 전자")
                page.locator(f"#slipBplTable_{n}_2").fill(row_data["basic_summary"])
                
                # 금액 탭 타이밍 (자동계산 스크립트 발동 유도)
                page.locator(f"#slipBplTable_{n}_4").fill(row_data["supply_amount"])
                page.keyboard.press("Tab")
                page.wait_for_timeout(500)
                page.locator(f"#slipBplTable_{n}_5").fill(row_data["vat"])
                page.locator(f"#slipBplTable_{n}_8").fill(row_data["details"])
                page.locator(f"#slipBplTable_{n}_9").fill(common_data["bank_name"])
                page.locator(f"#slipBplTable_{n}_10").fill(common_data["bank_account"])
                page.locator(f"#slipBplTable_{n}_11").fill(common_data["account_holder"])

                # 부서 선택 (행별 L열)
                if row_data["dept_code"]:
                    page.locator(f"#slipBplTable_{n}_6").click()
                    page.locator("#popupContent").wait_for(state="visible", timeout=10000)
                    page.locator("#searchtype2").select_option(value="dept_cd")
                    page.locator("#partnerKeyword").fill(row_data["dept_code"])
                    page.locator("#partnerSearchBtn").click()
                    page.wait_for_timeout(1000)
                    page.locator(f"td.code.sorting_1:has-text('{row_data['dept_code']}')").first.click()
                    page.locator("#popupContent").wait_for(state="hidden", timeout=10000)

                # 거래처 선택 (시트 상단 C5 공통)
                if common_data["client_code"]:
                    page.locator(f"#slipBplTable_{n}_7").click()
                    page.locator("#popupContent").wait_for(state="visible", timeout=10000)
                    page.locator("#searchtype2").select_option(value="tr_cd")
                    page.locator("#partnerKeyword").fill(common_data["client_code"])
                    page.locator("#partnerSearchBtn").click()
                    page.wait_for_timeout(1000)
                    page.locator(f"td.code.sorting_1:has-text('{common_data['client_code']}')").first.click()
                    page.locator("#popupContent").wait_for(state="hidden", timeout=10000)

            print("\n✅ 모든 봇 작업이 완료되었습니다! 브라우저 창에서 내용을 확인하고 직접 상신해 주세요.")
            print("종료하려면 이 터미널 창에서 [Enter] 키를 누르세요.")
            input()

        except Exception as e:
            # 예상치 못한 에러에 대비한 강건한 Safety Net
            ts = datetime.datetime.now().strftime("%H%M%S")
            error_html_path = archive_dir / f"error_dom_{ts}.html"
            error_snap_path = archive_dir / f"error_snap_{ts}.png"
            
            with open(str(error_html_path), "w", encoding="utf-8") as f:
                f.write(page.content())
            page.screenshot(path=str(error_snap_path))
            
            print("\n❌ 런타임 에러 발생!")
            print(f"[Log]: {str(e)}")
            print(f"==================================================")
            print(f"재욱님, 에러 화면을 확인해 주세요!")
            print(f"- DOM 스니펫: {error_html_path}")
            print(f"- 스크린샷: {error_snap_path}")
            print(f"==================================================")
            page.pause()

        finally:
            browser.close()

if __name__ == "__main__":
    run_automation()
