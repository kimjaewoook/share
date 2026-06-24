import os
import sys
import re
import json
import datetime
import shutil
from pathlib import Path
from collections import defaultdict
import gspread
from google.oauth2.service_account import Credentials

try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent.parent.parent  # ai/laundrygo/apps/카톡발주-메시지생성 -> ai/

CREDENTIAL_DIR = ROOT_DIR / os.getenv("CREDENTIAL_PATH", "_config/credentials")
CREDENTIAL_PATH = CREDENTIAL_DIR / "google_sheets_service_account.json"

KOREAN_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]

def get_archive_dir() -> Path:
    now = datetime.datetime.now()
    weekday = KOREAN_WEEKDAYS[now.weekday()]
    archive_dir = BASE_DIR / "archive" / f"{now.strftime('%Y-%m-%d')}({weekday})"
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir

def rotate_files(output_dir: Path, archive_dir: Path) -> None:
    if not output_dir.exists():
        return
    for f in output_dir.iterdir():
        if f.is_file():
            dst = archive_dir / f.name
            if dst.exists():
                ts = datetime.datetime.now().strftime("%H%M%S")
                dst = archive_dir / f"{f.stem}_{ts}{f.suffix}"
            shutil.copy2(str(f), str(dst))

def clean_location(location: str) -> str:
    """입고처에서 이름 및 전화번호 제거"""
    if not location:
        return ""
    # 예: 입고처: 자재창고(군포) 장현석 010-7294-9238 -> 입고처: 자재창고(군포)
    cleaned = re.sub(r'\s+[가-힣]{2,4}\s*01[0-9]-\d{3,4}-\d{4}.*', '', location)
    cleaned = re.sub(r'\s*01[0-9]-\d{3,4}-\d{4}.*', '', cleaned)
    return cleaned.strip()

def format_date(date_str: str) -> str:
    """2026.06.30(화) -> 6월 30일 화요일"""
    if not date_str:
        return ""
    m = re.match(r'\d{4}\.(\d{1,2})\.(\d{1,2})\((.)\)', date_str)
    if m:
        month = int(m.group(1))
        day = int(m.group(2))
        weekday = m.group(3)
        return f"{month}월 {day}일 {weekday}요일"
    return date_str

def main():
    print("==================================================")
    print("💌 카카오톡 발주 메시지 자동 생성기")
    print("==================================================")
    
    print("\n조회할 발주번호들을 입력하세요.")
    print("(여러 줄 복사/붙여넣기 가능합니다. 입력을 모두 마친 후 '빈 줄에서 엔터 키'를 한 번 더 누르세요.)")
    
    target_pos = set()
    while True:
        try:
            line = input().strip()
        except EOFError:
            break
            
        if not line:
            if target_pos:
                break
            else:
                continue
                
        # 쉼표, 띄어쓰기, 탭 등 다양한 구분자를 모두 처리하여 리스트 추출
        parts = re.split(r'[\s,]+', line)
        for p in parts:
            if p:
                target_pos.add(p)
                
    if not target_pos:
        print("발주번호가 입력되지 않았습니다. 종료합니다.")
        return
        
    target_pos = list(target_pos)
    print(f"\n⏳ 구글 시트 데이터 로딩 중...")
    
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    try:
        creds = Credentials.from_service_account_file(str(CREDENTIAL_PATH), scopes=scopes)
        client = gspread.authorize(creds)
        SHEET_ID = '1BStqRHhmz6vIuR-S110BjeAhYyrkp_tkisAQLw6TkAo'
        sheet = client.open_by_key(SHEET_ID)
        ws = sheet.worksheet('발주관리_PO List')
    except Exception as e:
        print(f"❌ 구글 시트 연동 실패: {e}")
        return
        
    data = ws.get_all_values()
    header_idx = 0
    for i in range(min(5, len(data))):
        if '발주번호' in data[i]:
            header_idx = i
            break

    headers = data[header_idx]
    rows = data[header_idx+1:]
    
    def get_col(row, header_names):
        # row가 headers 길이보다 짧을 수 있으므로 패딩
        padded_row = row + [''] * (len(headers) - len(row))
        for name in header_names:
            if name in headers:
                idx = headers.index(name)
                return str(padded_row[idx]).strip()
        return ""
        
    results = []
    found_pos = set()
    for row in rows:
        po_no = get_col(row, ["발주번호"])
        if po_no in target_pos:
            supplier = get_col(row, ["약식 명칭", "정식 명칭", "공급업체(약식 명칭)", "공급업체"])
            if not supplier:
                supplier = "미상_공급업체"
                
            item_code = get_col(row, ["품목코드", "자재코드(구매)"])
            item_name = get_col(row, ["자재명", "품목명"])
            qty = get_col(row, ["발주수량(낱개)", "수량"])
            # Format number if possible
            try:
                qty_clean = int(qty.replace(',', ''))
                qty = f"{qty_clean:,}"
            except ValueError:
                qty_clean = 0
                pass
                
            price_str = get_col(row, ["단가"])
            try:
                price = float(price_str.replace(',', '') or 0)
            except ValueError:
                price = 0
                
            supply_val = get_col(row, ["공급가액"])
            if supply_val:
                try:
                    supply_amt = float(supply_val.replace(',', ''))
                except ValueError:
                    supply_amt = qty_clean * price
            else:
                supply_amt = qty_clean * price
                
            vat_val = get_col(row, ["부가세", "부가세액"])
            if vat_val:
                try:
                    vat_amt = float(vat_val.replace(',', ''))
                except ValueError:
                    vat_amt = supply_amt * 0.1
            else:
                vat_amt = supply_amt * 0.1
                
            total_val = get_col(row, ["총액", "총금액", "금액", "합계"])
            if total_val:
                try:
                    row_total = float(total_val.replace(',', ''))
                except ValueError:
                    row_total = supply_amt + vat_amt
            else:
                row_total = supply_amt + vat_amt
                
            delivery_date = get_col(row, ["입고요청일"])
            raw_remark = get_col(row, ["발주서 비고란 입력내용 (공급업체 참고용)", "비고"])
            
            # 정규식 정제
            location = clean_location(raw_remark)
            
            results.append({
                "po_no": po_no,
                "supplier": supplier,
                "item_code": item_code,
                "item_name": item_name,
                "qty": qty,
                "qty_clean": qty_clean,
                "supply_amt": supply_amt,
                "vat_amt": vat_amt,
                "row_total": row_total,
                "delivery_date": delivery_date,
                "location": location
            })
            found_pos.add(po_no)
            
    missing_pos = set(target_pos) - found_pos
    if missing_pos:
        print(f"⚠️ 다음 발주번호는 찾을 수 없습니다: {', '.join(missing_pos)}")
        
    if not results:
        print("❌ 추출된 데이터가 없습니다.")
        return
        
    # Grouping Logic
    # 1순위: supplier, delivery_date
    groups = defaultdict(lambda: defaultdict(list))
    for r in results:
        # key1 = (supplier, delivery_date)
        # key2 = location
        groups[(r["supplier"], r["delivery_date"])][r["location"]].append(r)
        
    output_lines = []
    
    for (supplier, delivery_date), loc_dict in groups.items():
        output_lines.append(f"[{supplier}]\n")
        output_lines.append("안녕하세요. ")
        output_lines.append("이메일로 발주서 송부드렸습니다.")
        output_lines.append("발주 품목은 아래와 같습니다. ")
        output_lines.append("진행 부탁드립니다.\n\n")
        
        # 발주번호 목록 추출 (해당 그룹 내)
        group_pos = set()
        for items in loc_dict.values():
            for item in items:
                group_pos.add(item["po_no"])
        po_str = ", ".join(sorted(group_pos))
        
        output_lines.append(f"■발주번호 : {po_str}")
        output_lines.append(f"■입고요청일 : {format_date(delivery_date)}")
        output_lines.append("■입고장소 : 하단 개별 표기\n")
        
        output_lines.append("■품목 리스트")
        
        item_counter = 1
        for location, items in loc_dict.items():
            loc_disp = location if location else "입고장소 미지정"
            output_lines.append(f"[{loc_disp}]")
            
            # 발주번호 순으로 정렬
            items_sorted = sorted(items, key=lambda x: x["po_no"])
            for item in items_sorted:
                code_disp = item["item_code"] if item["item_code"] else "코드없음"
                output_lines.append(f"①{code_disp}   {item['item_name']}   {item['qty']}개 (발주: {item['po_no']})")
                item_counter += 1
            output_lines.append("") # 단락 사이 공백
            
        # numbering 재정렬 처리
        # 문자열 리스트에서 ①, ②, ③ 부분을 실제 인덱스로 교체
        final_lines_for_group = []
        real_idx = 1
        circled_numbers = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
        for line in output_lines[-item_counter-len(loc_dict):]:
            # we need to process the block we just added
            pass
            
        # 실제로는 위에서 추가하면서 바꾸는게 낫다.
        # So rebuild the item loop:
        
    # Rebuilding the output generation to fix circled numbers
    output_lines = []
    circled_numbers = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
    
    for (supplier, delivery_date), loc_dict in groups.items():
        output_lines.append(f"### {supplier}\n")
        output_lines.append("안녕하세요. ")
        output_lines.append("이메일로 발주서 송부드렸습니다.")
        output_lines.append("발주 품목은 아래와 같습니다. ")
        output_lines.append("진행 부탁드립니다.\n\n")
        
        group_pos = set()
        for items in loc_dict.values():
            for item in items:
                group_pos.add(item["po_no"])
        po_str = ", ".join(sorted(group_pos))
        
        output_lines.append(f"■발주번호 : {po_str}")
        output_lines.append(f"■입고요청일 : {format_date(delivery_date)}\n")
        
        output_lines.append("■품목 리스트")
        
        item_counter = 1
        for location, items in loc_dict.items():
            loc_disp = location if location else "입고장소 미지정"
            output_lines.append(f"[{loc_disp}]")
            
            items_sorted = sorted(items, key=lambda x: x["po_no"])
            for item in items_sorted:
                code_disp = item["item_code"] if item["item_code"] else "코드없음"
                num_char = circled_numbers[item_counter-1] if item_counter <= 20 else f"({item_counter})"
                output_lines.append(f"{num_char}{code_disp}   {item['item_name']}   {item['qty']}개")
                item_counter += 1
            output_lines.append("") 
            
        output_lines.append("협의 필요사항은 말씀 부탁드립니다.")
        output_lines.append("감사합니다.")
        output_lines.append("==================================================\n")
        
    final_text = "\n".join(output_lines)
    print("\n✅ 메세지 생성 완료!\n")
    print(final_text)
    
    # Save to file
    now = datetime.datetime.now()
    weekday = KOREAN_WEEKDAYS[now.weekday()]
    filename = f"{now.strftime('%Y-%m-%d')}({weekday})_발주카톡.txt"
    
    output_dir = BASE_DIR / "output"
    output_dir.mkdir(exist_ok=True)
    
    file_path = output_dir / filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_text)
        
    # Rotate to archive
    archive_dir = get_archive_dir()
    rotate_files(output_dir, archive_dir)
    
    print(f"📁 결과 파일이 저장되었습니다: {file_path}")
    
    print("\n==================================================")
    print("📊 발주 처리 요약")
    print("==================================================")
    
    unique_pos = set()
    total_items = len(results)
    summary_by_po = defaultdict(lambda: {
        'supplier': '',
        'qty': 0,
        'supply_amt': 0.0,
        'vat_amt': 0.0,
        'total_amt': 0.0
    })
    
    for r in results:
        p_no = r['po_no']
        unique_pos.add(p_no)
        summary_by_po[p_no]['supplier'] = r['supplier']
        summary_by_po[p_no]['qty'] += r.get('qty_clean', 0)
        summary_by_po[p_no]['supply_amt'] += r.get('supply_amt', 0.0)
        summary_by_po[p_no]['vat_amt'] += r.get('vat_amt', 0.0)
        summary_by_po[p_no]['total_amt'] += r.get('row_total', 0.0)
        
    print(f"총 발주번호 수 : {len(unique_pos)}개")
    print(f"총 품목 수    : {total_items}개")
    print("-" * 50)
    
    for p_no in sorted(unique_pos):
        data = summary_by_po[p_no]
        print(f"[{p_no}] {data['supplier']}")
        print(f"  - 수량 합계    : {data['qty']:,}개")
        print(f"  - 공급가액 합계: {data['supply_amt']:,.0f}원")
        print(f"  - 부가세 합계  : {data['vat_amt']:,.0f}원")
        print(f"  - 금액 합계    : {data['total_amt']:,.0f}원\n")
    print("==================================================")
    
    # 입력 버퍼 비우기 (복붙 시 남은 줄바꿈 문자로 인한 자동 종료 방지)
    try:
        import termios
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception:
        pass
        
    # Prompt to open folder
    resp = input("\n작업이 완료되었습니다. [1] output 폴더 열기  [2] 종료 : ").strip()
    if resp == '1':
        if sys.platform == 'darwin':
            os.system(f'open "{output_dir}"')
        elif sys.platform == 'win32':
            os.system(f'start "" "{output_dir}"')
        print("폴더를 열었습니다.")
    else:
        print("종료합니다.")

if __name__ == "__main__":
    main()
