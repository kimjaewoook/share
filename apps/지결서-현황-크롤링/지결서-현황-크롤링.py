import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import subprocess

# 자가 복구(Self-healing) 로직 도입: 의존성 모듈 자동 설치 및 브라우저 다운로드
try:
    import playwright
    import pandas
    import dotenv
    import gspread
    import gspread_formatting
except ImportError as e:
    print(f"\n\033[33m[Self-Healing] Missing dependency detected ({e}). Automatically installing...\033[0m\n")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright==1.49.1", "pandas==2.2.3", "python-dotenv==1.0.1", "gspread", "gspread-formatting"])
    print("\n\033[33m[Self-Healing] Installing Playwright Chromium browser binary...\033[0m\n")
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    print("\n\033[32m[Self-Healing] Installation complete. Restarting script...\033[0m\n")
    os.execv(sys.executable, [sys.executable] + sys.argv)

from playwright.sync_api import sync_playwright, Page
import pandas as pd
import datetime
from urllib.parse import urljoin
from config import logger, OUTPUT_DIR, ARCHIVE_DIR, LAUNDRYGO_GW_URL, LAUNDRYGO_GW_ID, LAUNDRYGO_GW_PW, get_archive_dir
from browser_utils import save_error_dom, proactive_click, proactive_text_content

# 전역 예외 처리 훅 (글로벌 강제 종료 정책)
def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error(f"Uncaught exception: {exc_type.__name__}: {exc_value}", exc_info=(exc_type, exc_value, exc_traceback))
    sys.exit(1)
sys.excepthook = global_exception_handler
from paths import PATHS
import sys
import os
from google_sheets import GoogleSheetsManager
import re
from urllib.parse import urlsplit

HISTORY_FILE = OUTPUT_DIR / "gw_history.json"

# --- 데이터 정제 유틸리티 ---
def clean_text(text: str) -> str:
    """HTML 태그, 엔티티를 완전히 제거하고 공백 정리"""
    if not isinstance(text, str):
        return ""
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def clean_url(url: str) -> str:
    """URL에서 쿼리 파라미터를 제거하여 고유 주소만 반환"""
    if not isinstance(url, str) or not url:
        return ""
    return url.split("?")[0]

def summarize_comments(text: str, max_len: int = 200) -> str:
    """긴 댓글/상세 내용을 핵심 키워드 위주로 요약"""
    if not isinstance(text, str) or not text:
        return ""
    cleaned = clean_text(text)
    # 금액 키워드 우선 추출
    prices = re.findall(r'[\d,]+원', cleaned)
    if len(cleaned) <= max_len:
        return cleaned
    summary = cleaned[:max_len].rsplit(' ', 1)[0] + "..."
    if prices:
        summary += f" (금액: {', '.join(prices[:3])})"
    return summary

def parse_subject_date(subject: str) -> str:
    """제목에서 (m/d) 형태의 날짜 추출"""
    if not isinstance(subject, str):
        return ""
    m = re.search(r'\((1?[0-9]/[1-3]?[0-9])\)', subject)
    return m.group(1) if m else ""

def parse_vendor_and_amount(subject: str) -> tuple:
    """제목에서 업체명과 금액을 추출. 다양한 오타 패턴 지원."""
    if not isinstance(subject, str):
        return ("", "")
    
    # 구분자로 하이픈 허용, 원 누락 허용, 띄어쓰기 허용
    m = re.search(r'_([^_]+)(?:_|-)\s*([\d,.]+)\s*(?:원)?.*$', subject)
    if m:
        vendor = m.group(1).strip()
        raw_amount = m.group(2).strip()
        
        # 마침표가 천단위 구분자로 쓰였을 경우 처리 (예: 1.000.000)
        if raw_amount.count('.') > 1 or (raw_amount.count('.') == 1 and len(raw_amount.split('.')[-1]) == 3):
            raw_amount = raw_amount.replace('.', '')
            
        # 숫자와 소수점만 추출
        clean_num_str = re.sub(r'[^\d.]', '', raw_amount)
        
        if clean_num_str:
            try:
                # 구글 시트에서 숫자로 인식할 수 있도록 순수 숫자형(int/float) 반환
                if '.' in clean_num_str:
                    amount = float(clean_num_str)
                else:
                    amount = int(clean_num_str)
                return (vendor, amount)
            except ValueError:
                pass
                
        return (vendor, raw_amount)
    return ("", "")

def prepare_for_sheets(df: pd.DataFrame) -> pd.DataFrame:
    """구글 시트 적재를 위한 전처리: 빈 행 제거, 정제, 열 재배치, 불필요 컬럼 제거"""
    df_out = df.copy()
    
    # 0. 제목이 비어있거나 공백인 쓰레기 행 완전 제거
    if 'subject' in df_out.columns:
        df_out = df_out[df_out['subject'].astype(str).str.strip() != '']
        df_out = df_out.dropna(subset=['subject'])
    
    # 1. 모든 텍스트 컬럼 HTML 태그/엔티티 제거
    text_cols = ['subject', 'division', 'current_approver', 'detail_comments']
    for col in text_cols:
        if col in df_out.columns:
            df_out[col] = df_out[col].apply(clean_text)
    
    # 2. URL 쿼리 파라미터 제거
    if 'doc_url' in df_out.columns:
        df_out['doc_url'] = df_out['doc_url'].apply(clean_url)
    
    # 3. 상세 댓글 요약 (200자 제한)
    if 'detail_comments' in df_out.columns:
        df_out['detail_comments'] = df_out['detail_comments'].apply(summarize_comments)
    
    # 3-1. 업체명 / 금액 파싱 및 날짜 추출 (제목에서 추출)
    if 'subject' in df_out.columns:
        parsed = df_out['subject'].apply(parse_vendor_and_amount)
        df_out['vendor_name'] = parsed.apply(lambda x: x[0])
        df_out['subject_date'] = df_out['subject'].apply(parse_subject_date)
        df_out['amount'] = parsed.apply(lambda x: x[1])
    
    # 4. 시스템 전용 컬럼 및 current_stage 제거
    drop_cols = ['href', 'onclick', 'outer_html', 'id', 'current_stage', 'doc_id']
    df_out = df_out.drop(columns=[c for c in drop_cols if c in df_out.columns], errors='ignore')
    
    # 5. 행 정렬: '완료'이면서 대금지급 핵심 댓글이 존재하는 완벽 종결 건을 최하단으로 밀어내기 (시트 맨 밑 위치)
    if 'state' in df_out.columns and 'detail_comments' in df_out.columns:
        is_fully_paid = (df_out['state'] == '완료') & (df_out['detail_comments'].apply(lambda x: bool(str(x).strip()) and str(x).strip() not in ('', 'None', 'nan')))
        df_out['_sort_key'] = is_fully_paid.astype(int)
        # 1차 정렬: 종결건 여부(일반건 0 -> 종결건 1), 2차 정렬: 날짜 내림차순
        df_out = df_out.sort_values(by=['_sort_key', 'date'], ascending=[True, False]).drop(columns=['_sort_key'])

    # 6. 확정된 열 순서로 강제 재배치
    desired_order = ['category', 'division', 'date', 'writer', 'subject', 'vendor_name', 'subject_date', 'amount', 'state', 'current_approver', 'doc_url', 'comments', 'detail_comments']
    existing_order = [c for c in desired_order if c in df_out.columns]
    remaining = [c for c in df_out.columns if c not in existing_order]
    df_out = df_out[existing_order + remaining]
    
    return df_out

def login(page: Page):
    logger.info("런드리고 그룹웨어 시스템에 접속을 시도하고 있습니다...")
    page.goto(LAUNDRYGO_GW_URL)
    try:
        # 로그인 파트 (Proactive Locator 적용, 타임아웃 5초 단축)
        # 아이디 입력
        try:
            page.locator("#username").fill(LAUNDRYGO_GW_ID, timeout=5000)
        except Exception:
            page.get_by_placeholder("계정").fill(LAUNDRYGO_GW_ID, timeout=5000)
            
        # 비밀번호 입력
        try:
            page.locator("#password").fill(LAUNDRYGO_GW_PW, timeout=5000)
        except Exception:
            page.get_by_placeholder("비밀번호").fill(LAUNDRYGO_GW_PW, timeout=5000)
            
        # 폼 제출 (엔터)
        page.keyboard.press("Enter")
        # 메인 홈 UI 진입 확정 대기 (강제 실패 10초)
        page.wait_for_url("**/app/home**", timeout=10000)
    except Exception as e:
        # Fail-Fast 강제 적용: 스냅샷 저장 후 무조건 비정상 종료
        save_error_dom(page, "Login transition failed. Check error_dom.html")
        logger.error(f"Login Exception: {type(e).__name__} - {str(e)}")
        sys.exit(1)

def set_pagination_limit(page: Page):
    try:
        # 단일 핀셋 타겟팅 확정
        select_locator = page.locator('select:has(option[value="80"])').first
        
        # 1. State Check: 드롭다운의 현재 값을 확인 (스마트 스킵)
        current_value = select_locator.input_value(timeout=5000)
        
        if current_value == "80":
            logger.info("(보기 설정이 이미 80개로 맞춰져 있어 쾌속으로 넘어갑니다)")
            return

        # 2. 값 변경
        logger.info("한 페이지에 문서를 80개씩 한눈에 볼 수 있도록 보기 설정을 변경합니다.")
        select_locator.select_option("80", timeout=5000)
        
        # 3. 하드 슬립 대기 전략 (Simple Wait)
        page.wait_for_timeout(3000)
        
    except Exception as e:
        logger.error(f"Could not change pagination limit using specific locator: {type(e).__name__} - {str(e)}")
        sys.exit(1)

def collect_list_data(page: Page, category: str) -> list[dict]:
    logger.info(f"[{category}] 문서 목록에서 전체 기본 데이터 수집을 시작합니다...")
    items_dict = {}
    page_num = 1
    max_pages = 5
    
    while page_num <= max_pages:
        logger.info(f"[{category}] {page_num}번째 페이지의 문서 내역을 가져오고 있습니다...")
        prev_count = len(items_dict)
        
        rows = page.locator("table tbody tr")
        for i in range(rows.count()):
            row = rows.nth(i)
            # Extractor functions according to rules
            doc_date = clean_text(row.locator("td.date.first").inner_text()) if row.locator("td.date.first").count() else ""
            division = clean_text(row.locator("td.division").inner_text()) if row.locator("td.division").count() else ""
            
            subj_loc = row.locator("td.subject span.txt, td.subject a")
            subject = clean_text(subj_loc.first.inner_text()) if subj_loc.count() else ""
            
            state_loc = row.locator("td.state_wrap span.state")
            state = clean_text(state_loc.first.inner_text()) if state_loc.count() else ""
            
            # ── 필터링: division + state 조건 ──
            # 대상 양식: "비용 지출 결의서" (본사)
            target_divisions = ["비용 지출 결의서"]
            if not any(td in division for td in target_divisions):
                continue
            # 대상 상태: "진행중" 또는 "완료"
            if "진행" not in state and "완료" not in state:
                continue
            
            num_loc = row.locator("span.wrap_ic span.num")
            comments = num_loc.first.inner_text() if num_loc.count() else "0"
            
            # 기안자 파싱
            writer = clean_text(row.locator("td.writer span.txt").first.inner_text()) if row.locator("td.writer span.txt").count() else ""
            if category == "기안문서":
                writer = "김재욱"
            
            # The click target
            link_el = row.locator("td.subject a").first
            href = link_el.get_attribute("href") if link_el.count() else ""
            onclick = link_el.get_attribute("onclick") if link_el.count() else ""
            
            # --- 히든 ID 추출 (Hidden Document ID Extraction) ---
            # <tr> 태그 전체의 outerHTML에서 고유 문서 번호를 집요하게 파싱
            raw_html = row.evaluate("el => el.outerHTML")
            id_match = (
                re.search(r'document[/\(=_](\d{4,})', raw_html) or
                re.search(r'data-(?:id|key|docid|num)["\\s]+(\d{4,})', raw_html, re.IGNORECASE) or
                re.search(r'id=["\']?\w*?(\d{4,})', raw_html) or
                re.search(r'onclick[^>]*(\d{4,})', raw_html)
            )
            unique_doc_id = id_match.group(1) if id_match else f"fallback_{category}_{doc_date}_{subject}"
            
            if unique_doc_id.startswith("fallback"):
                pass # logger.warning(f"히든 ID 파싱 실패, Fallback 적용됨: {subject}")
            
            items_dict[unique_doc_id] = {
                "category": category,
                "doc_id": unique_doc_id,
                "date": doc_date.strip(),
                "division": division.strip(),
                "writer": writer,
                "subject": subject.strip(),
                "state": state.strip(),
                "comments": comments.strip(),
                "href": href,
                "onclick": onclick,
                "outer_html": raw_html
            }
            
        current_count = len(items_dict)
        if current_count == prev_count:
            logger.warning(f"[{category}] 더 이상 새로운 문서가 발견되지 않아, 목록 수집을 안전하게 마무리합니다.")
            break
            
        if page_num >= max_pages:
            logger.info(f"[{category}] 안전장치: 최대 수집 가능 페이지 수({max_pages}p)에 도달하여 목록 수집을 강제 완료합니다.")
            break
            
        # Check next page pagination button
        logger.info(f"[{category}] 다음 페이지가 있는지 확인하고 넘어갑니다.")
        next_btn = page.locator(".paginate_button.next:not(.disabled)")
        if next_btn.count() > 0:
            next_btn.first.click()
            page.wait_for_timeout(3000)
            page_num += 1
        else:
            logger.info(f"[{category}] 더 이상 활성화된 '다음' 버튼이 존재하지 않아 수집을 마칩니다.")
            break
            
    return list(items_dict.values())

def extract_detail_data(page: Page) -> dict:
    """현재 열려있는 상세 페이지에서 데이터를 추출한다. (네비게이션 없음)"""
    
    # 상세 페이지 URL 확보 (브라우저 주소창에서 직접 추출)
    doc_url = page.url
    
    # Extract current stage
    current_stage = proactive_text_content(page, ["li.current", "span.current_step", ".approval_line .current"])
    
    # Extract current approver (현재 결재 대기자: 부서명 이름)
    current_approver = ""
    try:
        info_loc = page.locator("li.current div.info").first
        if info_loc.count() > 0:
            dept = info_loc.get_attribute("data-userdeptname") or ""
            name = info_loc.get_attribute("data-username") or ""
            if dept and name:
                current_approver = f"{dept} {name}".strip()
            else:
                # Fallback 경우 (혹시 속성이 다를 경우 텍스트 값 자체를 가져오도록 2차 방어)
                logger.warning("DOM 속성 누락으로 inner_text 대체 추출 발동. DOM 변경을 확인하세요.")
                current_approver = info_loc.inner_text().strip().replace('\n', ' ')
    except Exception as e:
        logger.warning(f"Could not extract current approver: {type(e).__name__}")
    
    # Extract comments (Filtered by target writers and "완료" keyword)
    comments_text = []
    # 지급 처리를 담당하는 핵심 인물 목록 (필요시 이름 추가 가능)
    target_writers = ["이혁희", "임휘랑", "김현식", "조정화", "김주연", "고가현"]  
    
    thread_els = page.locator("li[data-thread]")
    for i in range(thread_els.count()):
        thread = thread_els.nth(i)
        
        # 작성자 이름 추출
        name_loc = thread.locator("div.info span.name")
        writer_name = name_loc.first.inner_text().strip() if name_loc.count() > 0 else ""
        
        # 댓글 내용 추출
        msg_loc = thread.locator("p.message")
        if msg_loc.count() > 0:
            raw_msg = msg_loc.first.evaluate("el => el.innerHTML.replace(/<br\\s*\\/?>/gi, '\\n')")
            import re
            text = re.sub(r'<[^>]+>', '', raw_msg).replace('&nbsp;', ' ').strip()
            
            # 필터링: 내용에 '완료'가 포함되어 있고, 작성자가 타겟 담당자 중 한 명일 때만 수집
            if "완료" in text and any(tw in writer_name for tw in target_writers):
                comments_text.append(text)
        
    return {
        "current_stage": current_stage,
        "current_approver": current_approver,
        "doc_url": doc_url,
        "detail_comments": "\\n---\\n".join(comments_text)
    }

def process_diffs_and_scrape_details(page: Page, items: list[dict]) -> pd.DataFrame:
    df_new = pd.DataFrame(items)
    if df_new.empty:
        return df_new, df_new
        
    # 빈 컬럼 사전 생성: Pandas merge() 동작 시,
    # 우측(df_old)에만 존재하는 컬럼은 '_old' 접미사가 붙지 않고 기존 이름이 유지되는 버그를 방지
    for col in ['current_stage', 'current_approver', 'doc_url', 'detail_comments']:
        if col not in df_new.columns:
            df_new[col] = ""

    try:
        from google_sheets import GoogleSheetsManager
        gs_manager = GoogleSheetsManager()
        logger.info("이전 크롤링 기록을 확인하기 위해, 구글 시트의 기존 데이터를 잠시 불러오고 있습니다...")
        df_old = gs_manager.get_main_sheet_data()
        
        if not df_old.empty:
            for col in ['current_approver', 'detail_comments', 'state', 'comments']:
                if col not in df_old.columns:
                    df_old[col] = ""
        else:
            df_old = pd.DataFrame(columns=df_new.columns)
    except Exception as e:
        logger.error(f"Failed to load Google Sheets data: {e}")
        df_old = pd.DataFrame(columns=df_new.columns)
        
    # --- 복합 키 생성 (composite_key) ---
    # doc_id는 시트에 저장되지 않으므로, '날짜 + 제목 + 작성자'를 고유키로 사용
    df_new['composite_key'] = df_new['date'].astype(str) + "_" + df_new['subject'].astype(str) + "_" + df_new['writer'].astype(str)
    
    if not df_old.empty:
        df_old['composite_key'] = df_old['date'].astype(str) + "_" + df_old['subject'].astype(str) + "_" + df_old['writer'].astype(str)
    else:
        df_old['composite_key'] = pd.Series(dtype='str')
        
    merged = pd.merge(df_new, df_old, on='composite_key', suffixes=('', '_old'), how='left')
    
    # Conditions: ("진행중" or "완료") and (New OR Status changed OR Comment count changed)
    cond_target_states = merged['state'].isin(["진행중", "완료"])
    cond_new = merged['state_old'].isna() | (merged['state_old'] == "")
    cond_status_diff = merged['state'] != merged['state_old']
    cond_comments_diff = merged['comments'].astype(str) != merged['comments_old'].astype(str)
    
    # [추가] 과거 DB에 존재하지만 상세 크롤링을 실패하여 doc_url이 빈 값인 문서 식별 (자동 이어하기용)
    if 'doc_url_old' in merged.columns:
        cond_never_scraped = merged['doc_url_old'].astype(str).str.strip() == ""
        # 진행중인데 현재 결재자가 빈 칸인 경우도 재수집 타겟에 포함 (로직 강화)
        if 'current_approver_old' in merged.columns:
            cond_no_approver = (merged['state'] == '진행중') & (merged['current_approver_old'].astype(str).str.strip() == "")
            cond_never_scraped = cond_never_scraped | cond_no_approver
    else:
        cond_never_scraped = pd.Series(True, index=merged.index)
    
    # [추가] 이미 '완료' 상태이면서 과거 상세 내역에 대금지급 댓글이 존재하는 완벽 종료건은 상세 크롤링 타겟에서 완전 배제
    if 'detail_comments_old' in merged.columns:
        cond_already_fully_paid = (merged['state_old'] == '완료') & merged['detail_comments_old'].apply(lambda x: bool(str(x).strip()) and str(x).strip() not in ('', 'None', 'nan'))
    else:
        cond_already_fully_paid = pd.Series(False, index=merged.index)
    
    target_mask = cond_target_states & (cond_new | cond_status_diff | cond_comments_diff | cond_never_scraped) & (~cond_already_fully_paid)
    
    df_targets = merged[target_mask].copy()
    logger.info(f"기존 기록과 비교해본 결과, 내용이 바뀌었거나 새로 추가되어 상세 조회가 필요한 문서는 딱 {len(df_targets)}건입니다!")
    
    # early return을 제거하여 변경점이 없는 날에도 과거 데이터 복원(fallback) 로직이 정상 실행되도록 수정
    
    # --- Click & Back 방식 ---
    # 인덱스 보존 (절대 매핑용)
    df_targets['original_index'] = df_targets.index
    targets_list = df_targets.to_dict('records')
    detail_results = []
    total_targets = len(targets_list)
    abort_scraping = False
    
    # 카테고리별로 그룹핑
    from collections import defaultdict
    cat_groups = defaultdict(list)
    for t in targets_list:
        cat_groups[t['category']].append(t)
    
    detail_idx = 0
    for cat_name, cat_targets in cat_groups.items():
        if abort_scraping:
            break
            
        # 해당 카테고리의 리스트 페이지로 직접 이동
        list_url = urljoin(LAUNDRYGO_GW_URL, PATHS[cat_name])
        logger.info(f"[{cat_name}] 상세 내역을 파악하기 위해 문서함으로 다시 이동합니다...")
        page.goto(list_url)
        page.locator("td.subject a").first.wait_for(state="visible", timeout=10000)
        set_pagination_limit(page)
        
        # composite_key 기반으로 매칭
        target_keys = {t['composite_key'] for t in cat_targets}
        remaining_targets = target_keys.copy()
        
        page.goto(list_url)
        page.locator("td.subject a").first.wait_for(state="visible", timeout=10000)
        set_pagination_limit(page)
        page.wait_for_timeout(1000)
        
        page_num = 0
        while remaining_targets:
            rows = page.locator("table tbody tr")
            row_count = rows.count()
            
            if row_count == 0:
                logger.warning(f"[{cat_name}] 빈 페이지에 도달했습니다. 수집 불가능한 타겟이 있습니다. ({len(remaining_targets)}개 누락)")
                break
                
            for i in range(row_count):
                if i >= rows.count():
                    logger.warning(f"DOM 렌더링 지연으로 인해 조기 종료: expected {row_count}, actual {rows.count()}")
                    break
                    
                row = rows.nth(i)
                
                # 수집부와 100% 동일하게 키 추출
                doc_date = clean_text(row.locator("td.date.first").inner_text()) if row.locator("td.date.first").count() else ""
                subj_loc = row.locator("td.subject span.txt, td.subject a")
                row_subject = clean_text(subj_loc.first.inner_text()) if subj_loc.count() else ""
                writer = clean_text(row.locator("td.writer span.txt").first.inner_text()) if row.locator("td.writer span.txt").count() else ""
                if cat_name == "기안문서":
                    writer = "김재욱"
                row_key = f"{doc_date}_{row_subject}_{writer}"
                
                if row_key not in remaining_targets:
                    continue
                    
                detail_idx += 1
                logger.info(f"[{detail_idx}/{total_targets}] 새롭게 바뀐 문서 안으로 들어가 결재 진행 상태와 댓글 내용을 확인합니다: '{row_subject}'")
                
                try:
                    # 1. 제목 클릭하여 상세 페이지 진입
                    page.wait_for_timeout(500)
                    rows.nth(i).locator("td.subject a").first.click()
                    page.wait_for_url("**/app/approval/document/**", timeout=10000)
                    page.wait_for_timeout(2000)
                    
                    # 2. 상세 데이터 추출 (현재 열린 페이지에서)
                    res = extract_detail_data(page)
                    
                    # 해당 target 딕셔너리에 결과 병합
                    for t in cat_targets:
                        if t['composite_key'] == row_key and '_updated' not in t:
                            t.update(res)
                            t['_updated'] = True
                            break
                            
                    remaining_targets.remove(row_key)
                    
                    # 3. 리스트로 복귀 (SPA go_back 버그 방어: 명시적 URL 이동)
                    page.goto(list_url)
                    page.locator("td.subject a").first.wait_for(state="visible", timeout=10000)
                    page.wait_for_timeout(2000)
                    set_pagination_limit(page)
                    
                    # 5. 복귀 후 행 목록 갱신 (Session 기반으로 해당 페이지가 자동 복구됨)
                    page.locator("td.subject a").first.wait_for(state="visible", timeout=15000)
                    rows = page.locator("table tbody tr")
                    
                except Exception as e:
                    logger.error(f"상세 페이지 클릭/추출 실패 [{row_subject}]: {type(e).__name__} - {str(e)}")
                    save_error_dom(page, f"detail_click_failed_{row_subject}")
                    logger.warning(f"네트워크 에러 등으로 중단되었습니다. 현재 문서까지의 추출 정보를 부분 저장하고 안전하게 종료합니다.")
                    abort_scraping = True
                    break
            
            if abort_scraping or not remaining_targets:
                break
                
            next_btn = page.locator(".paginate_button.next").first
            if next_btn.count() > 0 and not "disabled" in next_btn.get_attribute("class"):
                logger.info(f"[{cat_name}] 다음 페이지 진입. (남은 타겟: {len(remaining_targets)}개)")
                first_str = ""
                if page.locator("td.subject a").count() > 0:
                    first_str = page.locator("td.subject a").first.inner_text()
                    
                try:
                    with page.expect_response(lambda response: "approval" in response.url and response.status == 200, timeout=10000):
                        next_btn.click()
                except Exception:
                    next_btn.click() # Fallback if expect_response misses
                
                try:
                    page.wait_for_function('''([prev_str]) => {
                        const loc = document.querySelector("td.subject a");
                        return loc && loc.innerText !== prev_str;
                    }''', arg=[first_str], timeout=15000)
                except Exception:
                    pass
                page.wait_for_timeout(4000)
                page.locator("td.subject a").first.wait_for(state="visible", timeout=15000)
                page_num += 1
            else:
                logger.warning(f"[{cat_name}] 마지막 페이지에 도달했습니다. (수집 실패: {len(remaining_targets)}개)")
                break
    
    # 결과 취합
    for t in targets_list:
        detail_results.append(t)
        
    df_final_targets = pd.DataFrame(detail_results)
    
    # Merge back details to original df_new (doc_id 기반 안전 매핑)
    if not df_final_targets.empty:
        # doc_id를 기준으로 안전하게 데이터 삽입
        detail_dict = df_final_targets.drop_duplicates('doc_id').set_index('doc_id').to_dict('index')
        for idx, row in df_new.iterrows():
            d_id = row.get('doc_id')
            if d_id in detail_dict:
                for col in ['current_stage', 'current_approver', 'doc_url', 'detail_comments']:
                    val = detail_dict[d_id].get(col)
                    if pd.notna(val) and str(val).strip() != "":
                        df_new.at[idx, col] = val

    # --- 스킵된 문서들을 위해 과거 DB(시트)에서 상세 정보 가져오기 (Bulletproof Dict 방식) ---
    if not df_old.empty and 'composite_key' in df_old.columns:
        old_dict = df_old.drop_duplicates(subset=['composite_key'], keep='first').set_index('composite_key').to_dict('index')
        
        for col in ['current_approver', 'doc_url', 'detail_comments']:
            if col not in df_new.columns:
                df_new[col] = ""
                
        for idx, row in df_new.iterrows():
            c_key = row.get('composite_key')
            if c_key in old_dict:
                for col in ['current_approver', 'doc_url', 'detail_comments']:
                    val = row.get(col)
                    if pd.isna(val) or str(val).strip() == "":
                        df_new.at[idx, col] = old_dict[c_key].get(col, "")
                            
    # 절대 doc_id를 여기서 drop하지 마라! gw_history에 저장되어야 델타 스킵이 작동한다.
    return df_new, df_final_targets

def generate_slack_messages(df: pd.DataFrame) -> list[tuple]:
    """결재 대기자별로 그룹화된 슬랙 메시지 생성 (approver, message) 튜플 반환"""
    # 진행중/완료 상태를 가져오되, (완료 + 핵심 대금지급 댓글 존재) 완벽 종결 건은 영구 제외 처리 (슬랙 알림 피로도 저감)
    target_docs = df[df['state'].isin(['진행중', '완료'])].copy()
    if 'detail_comments' in target_docs.columns:
        is_fully_paid = (target_docs['state'] == '완료') & (target_docs['detail_comments'].apply(lambda x: bool(str(x).strip()) and str(x).strip() not in ('', 'None', 'nan')))
        target_docs = target_docs[~is_fully_paid]
        
    if target_docs.empty:
        return []
    
    # URL 정제
    if 'doc_url' in target_docs.columns:
        target_docs['doc_url'] = target_docs['doc_url'].apply(clean_url)
    
    target_docs = target_docs.sort_values(by=['date'], ascending=False)
    
    # [수정] 결재자 부서 변경 대응: 이름만 추출하여 그룹핑 (가장 끝 단어 기준)
    target_docs['approver_name'] = target_docs['current_approver'].apply(lambda x: str(x).strip().split()[-1] if str(x).strip() else "")
    
    messages = []
    for name_only, group in target_docs.groupby('approver_name'):
        if not name_only:
            continue
            
        # 가장 최근 날짜의 문서에 기록된 최신 부서명+이름을 대표 이름으로 사용
        latest_approver = group['current_approver'].iloc[0]
        
        total_count = len(group)
        
        # 상태 분류 (3가지):
        # 1) detail_comments가 존재하는 문서 → 지급완료 후 기안승인 대기
        # 2) 나머지 중 state에 '완료' 포함 → 지급 완료
        # 3) 그 외 전부 → 지급 대기
        has_comment = group[
            group['detail_comments'].apply(lambda x: bool(str(x).strip()) and str(x).strip() not in ('', 'None', 'nan'))
        ]
        no_comment = group.drop(has_comment.index)
        completed = no_comment[no_comment['state'].str.contains('완료', na=False)]
        pending = no_comment[~no_comment['state'].str.contains('완료', na=False)]
        
        lines = [
            "안녕하십니까",
            "상신 후 결재 대기 중인 지출결의서 목록입니다. 확인 및 승인 부탁드립니다.",
            "설명이 필요한 건은, 말씀주시면 내용 정리하여 찾아뵙겠습니다.",
            "",
            "---",
            f"■총 결재 요청 건 수: {total_count}건",
            ""
        ]
        
        # 조건부 노출: 지급완료 후 기안승인 대기 건
        if not has_comment.empty:
            lines.append(f"*💰 [■지급완료 후 기안승인 대기 중] - {len(has_comment)}건*")
            for seq, (_, row) in enumerate(has_comment.iterrows(), start=1):
                url = row.get('doc_url', row.get('href', ''))
                subj = clean_text(str(row['subject']))
                lines.append(f"{seq}. [{subj}]({url})")
            lines.append("")
        
        # 조건부 노출: 지급 완료 건
        if not completed.empty:
            lines.append(f"*✅ [지급 완료 건] - {len(completed)}건*")
            for seq, (_, row) in enumerate(completed.iterrows(), start=1):
                url = row.get('doc_url', row.get('href', ''))
                subj = clean_text(str(row['subject']))
                lines.append(f"{seq}. [{subj}]({url})")
            lines.append("")
        
        # 조건부 노출: 지급 대기 건
        if not pending.empty:
            lines.append(f"*⏳ [지급 대기 건] - {len(pending)}건*")
            for seq, (_, row) in enumerate(pending.iterrows(), start=1):
                url = row.get('doc_url', row.get('href', ''))
                subj = clean_text(str(row['subject']))
                lines.append(f"{seq}. [{subj}]({url})")
            lines.append("")
        
        lines.append("감사합니다")
        messages.append((str(latest_approver), "\n".join(lines)))
    
    return messages

def save_outputs(df_all: pd.DataFrame, df_changed: pd.DataFrame):
    # Backward compatibility for history json (원본 데이터 그대로 저장)
    df_all.to_json(HISTORY_FILE, orient="records", lines=True, force_ascii=False)
    logger.info("오늘까지의 전체 크롤링 내역을 내부 기록용(JSON)으로 안전하게 백업했습니다.")
    
    # --- Google Sheets Workflow ---
    logger.info("이제 확보한 최신 데이터를 구글 시트에 업데이트하기 시작합니다...")
    
    # 구글 API 결측치(NaN) 에러 차단
    df_all = df_all.astype(object).fillna("")
    if not df_changed.empty:
        df_changed = df_changed.astype(object).fillna("")
    
    # 사람이 읽기 편한 레포트 양식으로 전처리
    df_all_clean = prepare_for_sheets(df_all)
    df_changed_clean = prepare_for_sheets(df_changed) if not df_changed.empty else df_changed
    
    try:
        gs_manager = GoogleSheetsManager()
        
        # 구글 API NaTType 직렬화 크래시 완벽 차단 (문자열 강제 캐스팅)
        df_all_clean = df_all_clean.astype(str).replace(["NaT", "nan", "None", "<NA>"], "")
        if not df_changed_clean.empty:
            df_changed_clean = df_changed_clean.astype(str).replace(["NaT", "nan", "None", "<NA>"], "")
            
        gs_manager.sync_main_sheet(df_all_clean, df_changed_clean)
        gs_manager.append_changelog_sheet(df_changed_clean)
        
        # Slack messages (원본 df_all 사용 - 내부 키 참조 필요)
        slack_msgs = generate_slack_messages(df_all)
        gs_manager.update_slack_sheet(slack_msgs)
    except Exception as e:
        logger.error(f"Google Sheets Sync Failed: {repr(e)}")
        sys.exit(1)
    
    if not df_changed.empty:
        daily_file = OUTPUT_DIR / "gw_changed_today.csv"
        df_changed.to_csv(daily_file, index=False, encoding='utf-8-sig')
        
        archive_path = get_archive_dir()
        archive_file = archive_path / "gw_changed_today.csv"
        df_changed.to_csv(archive_file, index=False, encoding='utf-8-sig')
        logger.info(f"Saved daily changed data to {daily_file} and {archive_file}")
    else:
        logger.info("No changed documents today.")

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        login(page)
        
        all_items = []
        for cat, path in PATHS.items():
            full_url = urljoin(LAUNDRYGO_GW_URL, path)
            logger.info(f"[{cat}] 탭으로 이동하여 데이터를 확인합니다...")
            try:
                page.goto(full_url)
                # 문서함 데이터 렌더링 확인 (10초 대기)
                page.locator("td.subject a").first.wait_for(state="visible", timeout=10000)
                
                set_pagination_limit(page)
                
                items = collect_list_data(page, cat)
                logger.info(f"[{cat}] 총 {len(items)}개의 문서 목록을 성공적으로 확보했습니다.")
                all_items.extend(items)
            except Exception as e:
                save_error_dom(page, f"{cat} navigation or scrape failed.")
                logger.error(f"Failed to scrape path {cat}: {e}")
                sys.exit(1)
            
        df_all, df_changed = process_diffs_and_scrape_details(page, all_items)
        save_outputs(df_all, df_changed)
        
        # --- 최종 리포트 출력 ---
        print("\n" + "="*60)
        print("📊 [지결서 크롤링 자동화 작업 결과 보고서]")
        print("="*60)
        print(f"✅ 총 누적 관리 기안문 : {len(df_all)} 건")
        print(f"🔄 금일 업데이트된 문서 : {len(df_changed)} 건 (신규/상태변경/댓글추가 등)")
        
        if not df_changed.empty:
            print("  [완료된 후속 작업]")
            print("  - 엑셀(구글 시트) 'Main' 전체 현황 최신화")
            print("  - 엑셀(구글 시트) 'ChangeLog' 변경 이력 누적")
            print("  - 엑셀(구글 시트) 'SlackMessages' 알림 대상 정리")
            print("  - 로컬 백업용 CSV 파일 저장")
        else:
            print("  ※ 오늘은 내용이 변경되거나 새롭게 올라온 문서가 없습니다.")
            
        print("="*60)
        print("🎉 모든 작업이 안정적으로 마무리되었습니다. 수고하셨습니다!\n")

        while True:
            choice = input("\n작업이 완료되었습니다. [1] output 폴더 열기 / [2] 종료 : ")
            if choice == '1':
                import os
                if os.path.exists(OUTPUT_DIR):
                    os.system(f"open '{OUTPUT_DIR}'")
                else:
                    print(f"⚠️ output 폴더를 찾을 수 없습니다: {OUTPUT_DIR}")
                break
            elif choice == '2':
                break
            else:
                print("1 또는 2를 입력해주세요.")

        browser.close()

if __name__ == "__main__":
    run()
