import os
import sys
import time
import argparse
import pyautogui
import pyperclip
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# 환경변수 로딩 로직 (python-dotenv가 필요할 수 있으나, 시스템에 없으면 os.environ을 활용하거나 수동 지정)
try:
    from dotenv import load_dotenv
    dotenv_path = '/Users/kimjaewoook/ai/.env'
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
except ImportError:
    pass

CREDENTIAL_PATH = os.environ.get('GOOGLE_SHEETS_CREDENTIALS', '/Users/kimjaewoook/ai/_config/credentials/google_sheets_service_account.json')

# 사용자 설정
DELAY_SHORT = 0.2  # 우측 방향키나 단순 이동 딜레이
DELAY_MID = 0.5    # 중간 수준의 서버 검증 대기 딜레이
DELAY_LONG = 1.0   # 엔터 등 서버 검증 대기 딜레이
PASTE_HOTKEY = 'ctrl' # Q1. 2번: Windows/가상머신 기준

def setup_interactive():
    print("==================================================")
    print("🤖 더존 ERP 발주(PO) 자동 키보드 입력(Key-in) 매크로")
    print("==================================================")
    print("※ 주의: 이 스크립트는 실행 도중 마우스를 움직이거나 다른 창을 클릭하면 데이터가 꼬일 수 있습니다.")
    print("✅ [Ctrl+V] 윈도우(Parallels/Citrix) 방식으로 설정되었습니다.")

def paste_text(text):
    text_str = str(text).strip()
    if not text_str or text_str == 'nan':
        text_str = ''
    pyperclip.copy(text_str)
    time.sleep(DELAY_SHORT)
    pyautogui.hotkey(PASTE_HOTKEY, 'v')
    time.sleep(DELAY_SHORT)

def run_macro():
    print("\n⏳ 구글 시트 데이터 로딩 중...")
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(CREDENTIAL_PATH, scopes=scopes)
    client = gspread.authorize(creds)
    
    SHEET_ID = '1BStqRHhmz6vIuR-S110BjeAhYyrkp_tkisAQLw6TkAo'
    try:
        sheet = client.open_by_key(SHEET_ID)
        ws = sheet.worksheet('발주관리_PO List')
        
        # 헤더가 1번 행인지 불확실할 수 있으나, 일반적으로 첫 행이 컬럼명임
        data = ws.get_all_values()
        header_idx = 0
        for i in range(min(5, len(data))):
            if '발주번호' in data[i]:
                header_idx = i
                break
                
        headers = data[header_idx]
        
        # 사용자가 AC열(29번째 열)에 마킹하므로 헤더를 강제 확장
        while len(headers) < 29:
            headers.append('')
        # AC열 헤더 이름이 비어있거나 다를 경우 확실하게 매핑
        if '더존입력완료' not in headers:
            headers[28] = '더존입력완료'
            
        rows = data[header_idx+1:]
        
        fixed_rows = []
        for r in rows:
            if len(r) < len(headers):
                r.extend([''] * (len(headers) - len(r)))
            elif len(r) > len(headers):
                r = r[:len(headers)]
            fixed_rows.append(r)
            
        df = pd.DataFrame(fixed_rows, columns=headers)
    except Exception as e:
        print(f"❌ 구글 시트 접근 에러: {e}")
        sys.exit(1)

    if '더존입력완료' not in df.columns:
        print("❌ 시트에서 '더존입력완료' 컬럼을 찾을 수 없습니다.")
        print("💡 팁: 구글 마스터 시트 [발주관리_PO List] 탭 우측 끝에 '더존입력완료' 라는 이름의 열을 생성해주세요.")
        sys.exit(1)

    if '발주유형' not in df.columns:
        print("❌ 시트에서 '발주유형' 컬럼을 찾을 수 없습니다.")
        sys.exit(1)

    # 더존입력완료가 비어있고 발주번호가 있으며, '발주유형'이 '양산'인 데이터 필터링
    df_unprocessed = df[(df['더존입력완료'] == '') & (df['발주번호'] != '') & (df['발주유형'] == '양산')]

    if df_unprocessed.empty:
        print("✅ 모든 발주건이 이미 더존에 입력되었습니다 (입력 대기 건 없음).")
        sys.exit(0)

    unique_pos = df_unprocessed['발주번호'].unique()
    print(f"\n✅ 더존 입력 대기 중인 발주건: 총 {len(unique_pos)}건 발견")
    print("==================================================")
    
    grouped = df_unprocessed.groupby('발주번호', sort=False)
    
    # 전체 대상 요약 출력 및 합계 계산
    unique_suppliers = set()
    total_qty = 0
    total_unit_price = 0
    total_supply_amt = 0
    total_vat = 0
    total_sum = 0

    for po_num, group in grouped:
        first_row = group.iloc[0]
        first_item_name = str(first_row.get('자재명', '')).split(' ')[0]
        supplier_name = str(first_row.get('공급업체(약식 명칭)', '')).strip()
        if supplier_name and supplier_name.lower() != 'nan':
            unique_suppliers.add(supplier_name)
        
        item_count = len(group)
        summary_name = f"{item_count}품목: {first_item_name} 등" if item_count > 1 else f"1품목: {first_item_name}"
        supplier_display = f" | 업체: {supplier_name}" if supplier_name and supplier_name.lower() != 'nan' else ""
        print(f"  - 발주번호: {po_num}{supplier_display} | 내용: {summary_name}")
        
    for _, row in df_unprocessed.iterrows():
        try:
            qty = int(str(row.get('수량', '0')).replace(',', '') or 0)
        except ValueError:
            qty = 0
        try:
            price = float(str(row.get('단가', '0')).replace(',', '') or 0)
        except ValueError:
            price = 0
            
        total_qty += qty
        total_unit_price += price
        
        supply_val = row.get('공급가액', '')
        if str(supply_val).strip() != '' and str(supply_val).strip().lower() != 'nan':
            try:
                supply_amt = float(str(supply_val).replace(',', ''))
            except ValueError:
                supply_amt = qty * price
        else:
            supply_amt = qty * price
            
        total_supply_amt += supply_amt
        
        vat_val = row.get('부가세', '')
        if str(vat_val).strip() != '' and str(vat_val).strip().lower() != 'nan':
            try:
                vat_amt = float(str(vat_val).replace(',', ''))
            except ValueError:
                vat_amt = supply_amt * 0.1
        else:
            vat_amt = supply_amt * 0.1
            
        total_vat += vat_amt
        
        total_val = row.get('총액', '')
        if str(total_val).strip() != '' and str(total_val).strip().lower() != 'nan':
            try:
                row_total = float(str(total_val).replace(',', ''))
            except ValueError:
                row_total = supply_amt + vat_amt
        else:
            row_total = supply_amt + vat_amt
            
        total_sum += row_total

    print("──────────────────────────────────────────────────")
    print(f"📌 [전체 대기 목록 요약]")
    print(f"  - 관련 공급업체 : {', '.join(sorted(unique_suppliers)) if unique_suppliers else '정보 없음'}")
    print(f"  - 총 수량 합계  : {total_qty:,}")
    print(f"  - 총 단가 합계  : {total_unit_price:,.0f}")
    print(f"  - 총 공급가액   : {total_supply_amt:,.0f}")
    print(f"  - 총 부가세     : {total_vat:,.0f}")
    print(f"  - 전체 총액     : {total_sum:,.0f}")
    print("==================================================")

    mode = input("\n진행 방식을 선택하세요. [1] 개별 승인 (기존 방식)  [2] 전체대상 자동 진행 : ").strip()
    if mode not in ['1', '2']:
        print("작업을 중단합니다.")
        sys.exit(0)
        
    if mode == '2':
        print("\n🚨 커서를 더존 ERP의 맨 처음 입력칸(발주번호)에 위치시켜 주세요.")
        resp = input("전체 발주건의 자동 입력을 시작할까요? [1] 시작  [2] 취소 : ").strip()
        if resp != '1':
            print("작업을 중단합니다.")
            sys.exit(0)
        print("5초 후 전체 텍스트 자동 타이핑이 시작됩니다...")
        for i in range(5, 0, -1):
            print(f"{i}...")
            time.sleep(1)
    
    for po_num, group in grouped:
        print(f"\n▶️ 대기 중인 발주: {po_num} (품목 수: {len(group)})")
        print("──────────────────────────────────────────────────────────────────────────────")
        print(f"  {'자재코드(구매)':<18} {'자재명':<22} {'수량':>8} {'단가':>10} {'금액':>12}")
        print("──────────────────────────────────────────────────────────────────────────────")
        total_qty = 0
        total_amt = 0
        for _, row in group.iterrows():
            code = str(row.get('자재코드(구매)', ''))[:16]
            name = str(row.get('자재명', ''))[:20]
            try:
                qty = int(str(row.get('수량', '0')).replace(',', '') or 0)
            except ValueError:
                qty = 0
            try:
                price = float(str(row.get('단가', '0')).replace(',', '') or 0)
            except ValueError:
                price = 0
            amt = qty * price
            total_qty += qty
            total_amt += amt
            print(f"  {code:<18} {name:<22} {qty:>8,} {price:>10,.0f} {amt:>12,.0f}")
        print("──────────────────────────────────────────────────────────────────────────────")
        print(f"  {'합계':<42} {total_qty:>8,} {'':>10} {total_amt:>12,.0f}")
        print("──────────────────────────────────────────────────────────────────────────────")
        
        if mode == '1':
            print("\n🚨 커서를 더존 ERP의 맨 처음 입력칸(발주번호)에 위치시켜 주세요.")
            resp = input(f"해당 건의 자동 입력을 시작할까요? [1] 시작  [2] 건너뛰기/종료 : ").strip()
            if resp != '1':
                print("작업을 중단합니다.")
                break
                
            print("5초 후 텍스트 자동 타이핑이 시작됩니다...")
            for i in range(5, 0, -1):
                print(f"{i}...")
                time.sleep(1)
        else:
            print("\n전체 자동 진행 중... (해당 건 입력 시작)")

        first_row = group.iloc[0]
        first_item_name = str(first_row.get('자재명', '')).split(' ')[0]
        item_count = len(group)
        summary_name = f"{item_count}품목: {first_item_name} 등" if item_count > 1 else f"1품목: {first_item_name}"

        # --- Header ---
        paste_text(po_num)
        pyautogui.press('right')
        time.sleep(DELAY_SHORT)
        
        paste_text(first_row.get('발주일자', ''))
        pyautogui.press('right')
        time.sleep(DELAY_SHORT)
        
        paste_text(first_row.get('업체코드', ''))
        pyautogui.press('right')
        time.sleep(1.0)  # 업체코드 로딩을 위해 개별 1초 대기로 변경
        
        pyautogui.press('enter')
        time.sleep(DELAY_SHORT)
        
        paste_text("김재욱")
        pyautogui.press('enter')
        time.sleep(DELAY_MID)
        
        paste_text(summary_name)
        pyautogui.press('enter')
        time.sleep(DELAY_LONG)

        # --- Item Loop ---
        for idx, row in group.iterrows():
            print(f"  - 품목 입력 중: {row.get('자재명', '')[:15]}...")
            
            paste_text(row.get('자재코드(구매)', ''))
            pyautogui.press('enter')
            time.sleep(DELAY_LONG)
            
            paste_text(row.get('입고요청일', ''))
            pyautogui.press('enter', presses=2, interval=DELAY_SHORT)
            time.sleep(0.6)
            
            paste_text(row.get('수량', ''))
            pyautogui.press('enter')
            time.sleep(DELAY_SHORT)
            
            paste_text(row.get('단가', ''))
            pyautogui.press('enter', presses=7, interval=0.05)
            time.sleep(DELAY_LONG)
            
        # --- 발주건 마지막: 헤더 영역으로 복귀 ---
        pyautogui.hotkey('shift', 'tab')
        time.sleep(0.1)
        pyautogui.press('enter')
        time.sleep(DELAY_LONG)
        pyautogui.press('right', presses=20, interval=DELAY_SHORT)
        pyautogui.press('left')
        time.sleep(DELAY_MID)
            
        print(f"✅ 발주번호 {po_num} 전체 품목 입력 완료!")
        print("💡 구글 시트의 해당 건 '더존입력완료' 란에 O 표시를 직접 입력해주세요.")
        
        if mode == '2':
            print("🔄 전체대상 자동 진행 모드: 0.5초 후 다음 발주건 입력을 시작합니다...")
            time.sleep(0.5)

if __name__ == '__main__':
    setup_interactive()
    run_macro()
