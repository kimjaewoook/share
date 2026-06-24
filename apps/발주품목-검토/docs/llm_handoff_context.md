# 발주품목검토 시스템: AI Handoff Context (Gemini Deep Think 전용 가이드)

> 이 문서는 Google Gemini Deep Think 모델이 현재 프로젝트의 맥락과 사용자의 요구사항을 완벽히 이해하고, **"AI 기반 동적 발주 로직(Phase 2)"**의 구조와 파이썬 코드를 설계할 수 있도록 작성된 종합 컨텍스트 문서입니다.

---

## 1. 프로젝트 개요 (Project Overview)
- **목표**: 런드리고(Laundrygo)의 자재 발주(PO) 대상을 매일 자동 검토하고, **PO List 형식의 엑셀 리포트를 생성**하는 파이썬 시스템 구축.
- **현재 상태**: 구글 시트 연동 및 엑셀 생성 파이프라인의 기초 뼈대만 완성되어 있음. (단순히 수량을 합산해서 엑셀에 뿌려주는 수준)

## 2. 핵심 요구사항: "Harness 기반의 AI 동적 추론 엔진"
기존의 전통적인 개발 방식처럼 벤더별 룰(예: 에버원 6720개 제한, 짝수 파렛트)을 Python 파일에 **하드코딩(If-else)하지 마십시오.** 
사용자가 진정으로 원하는 것은 **"LLM 기반의 판단 엔진"**입니다.

1. **AI 기반 엣지케이스 처리 (`harness` 활용)**
   - 벤더별 제약사항은 `docs/harness_PO_업체명.md` 파일에 자연어로 정의되어 있습니다.
   - 파이썬 스크립트 실행 시, 발주 대상 데이터와 해당 업체의 `harness` 마크다운 파일을 읽어와서 **LLM API (Gemini 등)에게 프롬프트로 던져 추론(Think)**하게 만들어야 합니다.
   - AI가 문서를 읽고 스스로 판단하여: 
     1) 캐파 초과 시 다음 날짜로 행(Row) 복제 및 수량 분할
     2) 파렛트/MOQ 단위 수량 보정 (올림 처리)
     3) AI 사유(Action) 텍스트 작성
   - 위 결과물을 JSON 등의 형태로 반환받아 최종 엑셀 데이터에 반영하는 구조를 설계해야 합니다.

2. **지능형 여유수량(Buffer) 산출 로직**
   - 현장(팩토리) 요청 수량이 리드타임(L/T) 기간을 버틸 수 있는지 계산.
   - 부족할 경우 시스템이 스스로 (L/T + 안전재고) 분량을 얹어서 발주 제안.

3. **입고요청일 지능형 산출 룰**
   - 팩토리별 지정 납품 요일(**성수: 화요일, 군포: 수요일, 부산: 금요일**).
   - L/T를 적용해 입고 가능한 최초 일자를 구한 뒤, 가장 가까운 해당 팩토리의 정규 납품 요일로 `입고요청일` 강제 조정.

4. **엑셀 상세 사유 기록 (Audit-Ready)**
   - 엑셀 마지막 열(`AI 제안 액션 및 판단 사유`)에 AI가 수량을 보정하거나 날짜를 나눈 이유를 명확하게 텍스트로 기록.

## 3. 실무 개발을 위한 4대 필수 지침 (Technical Details)
Deep Think 모델은 코드를 설계할 때 다음 4가지 실무 스펙을 반드시 준수해야 합니다.

### ① 구글 시트 연동 스펙 및 인증 구조 (API 가이드)
- 이미 `src/google_sheets.py`에 Google API 인증(Service Account `.env` 기반) 및 데이터 추출 함수 `get_sheet_data(spreadsheet_id, range_name)`가 구현되어 있습니다.
- 새로운 OAuth 로직을 짤 필요 없이 기존 함수를 import해서 사용하도록 설계하세요.

### ② 마스터 시트별 헤더(Header) 구조 및 주의사항 (Data Schema)
- 마스터 구글 시트들은 상단에 병합 셀이나 설명란이 있어 헤더 행(Index)이 일정하지 않습니다.
- 예: `PO List` 시트는 인덱스 4번(5행), `자재요청서`는 인덱스 1번(2행), `공급업체`는 인덱스 2번(3행)이 실제 헤더입니다. DataFrame 변환 시 이 부분을 유의하여 파싱 로직을 설계하세요.

### ③ 필수 컬럼명 매핑 (Column Dictionary)
- AI가 임의로 컬럼명을 짓지 말고 실제 업무 시트의 컬럼명을 사용하세요.
- 주요 컬럼명: `자재코드(물류)`, `자재코드(구매)`, `자재명`, `공급업체명(약식)`, `요청수량`, `단가`, `최소주문수량(MOQ)`, `L/T`, `현재고량`, `일평균소모량`.

### ④ 예외 및 오류 처리 정책 (Error Handling Policy)
- 데이터 누락(예: 단가테이블에 없는 신규 자재)이나 벤더의 Harness 파일이 없는 경우, 에러를 내고 스크립트를 중단해서는 안 됩니다.
- 예외 상황 발생 시 원래 수량대로 진행하되, 엑셀의 'AI 제안 사유' 란에 `[시스템 경고] 단가테이블 누락` 또는 `[시스템 경고] Harness 파일 없음 (기본 산출 적용)`이라고 기록하여 실무자가 눈으로 확인할 수 있게 해야 합니다.

## 4. 현재 프로젝트 구조
```text
apps/발주품목검토/
├── 발주품목검토.py           # 전체 파이프라인(추출->AI추론->리포트) 오케스트레이션 메인
├── config/
│   └── settings.py          # 마스터 시트 ID 및 시트 범위(SHEET_RANGES) 관리
├── docs/
│   ├── harness_PO_경동라인.md # LLM에게 프롬프트로 쏴줄 벤더별 룰셋 문서들
│   └── harness_PO_에버원.md 
└── src/
    ├── google_sheets.py     # 데이터 Fetch 함수 (수정 불필요)
    ├── data_mapper.py       # 여러 시트를 DataFrame으로 Join
    ├── procurement_engine.py# (핵심) Harness 문서를 읽고 LLM API를 호출해 동적 결과물 산출
    └── report_generator.py  # (수정 불필요) DataFrame을 엑셀로 변환
```

---
> **최종 목표**: "코딩된 규칙(If-else)에 종속되지 마십시오. Markdown 파일(`harness_PO_*.md`)만 수정하면, AI 엔진이 이를 알아듣고 자동으로 발주 수량과 날짜 쪼개기 로직을 바꿔서 엑셀을 뽑아내는 진정한 'AI Agent 기반 물류 통제탑'을 설계하는 것이 당신의 임무입니다."


---

## 5. [APPENDIX] 원본 소스 코드 및 Raw Data
> 다음 LLM은 아래 제공된 실제 코드와 마크다운 원문을 바탕으로 구체적이고 바로 실행 가능한 수준의 파이썬 코드를 작성해야 합니다.

### 파일명: `발주품목검토.py`
```python
import os
from src.data_mapper import fetch_all_master_data
from src.procurement_engine import generate_procurement_plan
from src.report_generator import generate_excel_report

def main():
    print("==================================================")
    print("데일리 발주 대상 검토 자동화 스크립트 실행 (Python)")
    print("==================================================")
    
    try:
        # 1. 마스터 데이터 및 자재요청서 데이터 추출
        print("\n[1/3] 데이터 추출 중...")
        data_dict = fetch_all_master_data()
        
        if data_dict["pending_requests"].empty:
            print("발주 검토 대상(직납 미불출 건)이 없습니다.")
            # 일반 재고 산출은 별도로 처리 (추후 고도화)
            return

        # 2. 발주 로직 연산 (하드코딩 룰 + 수량/납기 산출)
        print("\n[2/3] 발주 산출 및 엣지케이스(Harness) 적용 중...")
        plan_df = generate_procurement_plan(data_dict)
        
        if plan_df.empty:
            print("산출된 발주 계획이 없습니다.")
            return
            
        print(f"산출된 발주 제안 건수: {len(plan_df)}건")

        # 3. 결과 리포트(엑셀) 생성
        print("\n[3/3] PO List 엑셀 리포트 생성 중...")
        # PO List 원본 헤더 가져오기 (마지막 행이 헤더라고 가정)
        po_df = data_dict["po_list"]
        po_headers = po_df.columns.tolist() if not po_df.empty else []
        
        filepath = generate_excel_report(plan_df, po_headers)
        
        print("\n모든 처리가 성공적으로 완료되었습니다.")
        
    except Exception as e:
        print(f"\n❌ 스크립트 실행 중 오류가 발생했습니다: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

```

### 파일명: `config/settings.py`
```python
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

# 시트 이름 설정
SHEET_RANGES = {
    "자재요청서": "'자재요청서_신청확인'!A1:M",
    "단가테이블": "'발주관리_단가테이블'!A1:AB",
    "PO_LIST": "'발주관리_PO List'!A1:AZ",
    "재고현황": "'장현석_재고현황'!A1:AZ",
    "예상시점": "'재고소진예상시점'!A1:AZ",
    "공급업체": "'공급업체관리'!A1:Z",
    "자재코드": "'자재코드 관리_자재코드 목록'!A1:M",
}

```

### 파일명: `src/data_mapper.py`
```python
import pandas as pd
from src.google_sheets import get_sheet_data
from config.settings import MASTER_PO_SPREADSHEET_ID, SHEET_RANGES

def get_dataframe_from_sheet(spreadsheet_id, range_name, header_row_index=0):
    values = get_sheet_data(spreadsheet_id, range_name)
    if not values or len(values) <= header_row_index + 1:
        return pd.DataFrame()
    
    headers = values[header_row_index]
    data = values[header_row_index + 1:]
    
    # 일부 행의 열 개수가 부족할 수 있으므로 보정
    max_cols = len(headers)
    for i in range(len(data)):
        if len(data[i]) < max_cols:
            data[i].extend([''] * (max_cols - len(data[i])))
        elif len(data[i]) > max_cols:
            data[i] = data[i][:max_cols]
            
    return pd.DataFrame(data, columns=headers)

def fetch_all_master_data():
    pending_df = get_dataframe_from_sheet(MASTER_PO_SPREADSHEET_ID, SHEET_RANGES["자재요청서"], header_row_index=1)
    if not pending_df.empty and '실입고일' in pending_df.columns:
        pending_df = pending_df[pending_df['실입고일'].astype(str).str.strip() == '']
        
    po_list_df = get_dataframe_from_sheet(MASTER_PO_SPREADSHEET_ID, SHEET_RANGES["PO_LIST"], header_row_index=4)
    
    # 여기서 필요한 다른 마스터들도 가져올 수 있음
    return {
        "pending_requests": pending_df,
        "po_list": po_list_df
    }
```

### 파일명: `src/procurement_engine.py`
```python
import pandas as pd
from datetime import datetime, timedelta
from config.edge_cases import *

def clean_number(val):
    if pd.isna(val) or val is None or str(val).strip() == "":
        return 0.0
    try:
        return float(str(val).replace(",", ""))
    except:
        return 0.0

def generate_procurement_plan(data_dict):
    df = data_dict["pending_requests"].copy()
    if df.empty:
        return pd.DataFrame()
        
    # Grouping logic
    # 성수/부산: 합치기. 군포: 부서별로 쪼개기
    grouped_plans = []
    
    # "팩토리", "팀명", "자재코드"
    for _, row in df.iterrows():
        factory = str(row.get("팩토리", "")).strip()
        mat_code = str(row.get("자재코드", "")).strip()
        mat_name = str(row.get("자재명", "")).strip()
        dept = str(row.get("팀명", "")).strip()
        req = str(row.get("신청인", "")).strip()
        qty = clean_number(row.get("수량(낱개)", 0))
        req_date = str(row.get("요청일자", "")).strip()
        
        if not mat_code:
            continue
            
        is_sungsu_busan = "성수" in factory or "부산" in factory
        
        found = False
        for plan in grouped_plans:
            if plan["mat_code"] == mat_code and plan["factory"] == factory:
                if is_sungsu_busan:
                    plan["qty"] += qty
                    found = True
                    break
                else:
                    if plan["department"] == dept:
                        plan["qty"] += qty
                        found = True
                        break
        
        if not found:
            grouped_plans.append({
                "factory": factory,
                "department": "" if is_sungsu_busan else dept,
                "requestor": "" if is_sungsu_busan else req,
                "date_requested": req_date,
                "mat_code": mat_code,
                "mat_name": mat_name,
                "qty": qty,
                # To be populated:
                "expected_date": "",
                "vendor": "",
                "action": "직납 발주 제안",
                "daily_usage": "",
                "vendor_manager": "",
                "vendor_email": ""
            })
            
    # Calculate Expected Date based on Harness (납품요일 룰)
    now = datetime.now()
    for plan in grouped_plans:
        # 1. 팩토리별 정기 발주/입고 요일 룰
        # 성수: 화요일 납품
        # 군포: 수요일 납품
        # 부산: 금요일 납품
        expected_dt = now
        factory = plan["factory"]
        
        if "성수" in factory:
            days_ahead = (1 - now.weekday()) % 7 # 화요일(1)
            if days_ahead == 0: days_ahead = 7
            expected_dt = now + timedelta(days=days_ahead)
        elif "군포" in factory:
            days_ahead = (2 - now.weekday()) % 7 # 수요일(2)
            if days_ahead == 0: days_ahead = 7
            expected_dt = now + timedelta(days=days_ahead)
        elif "부산" in factory:
            days_ahead = (4 - now.weekday()) % 7 # 금요일(4)
            if days_ahead == 0: days_ahead = 7
            expected_dt = now + timedelta(days=days_ahead)
            
        plan["expected_date"] = expected_dt.strftime("%Y-%m-%d")
        
        # Vendor (알 수 없음이 기본)
        plan["vendor"] = "알 수 없음"

    return pd.DataFrame(grouped_plans)
```

### 파일명: `src/report_generator.py`
```python
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from datetime import datetime
from config.settings import OUTPUT_DIR

def generate_excel_report(plan_df, po_headers):
    """
    발주 산출 결과를 엑셀 리포트로 생성 (PO List 양식 기반 풀매핑)
    """
    now = datetime.now()
    days = ['월', '화', '수', '목', '금', '토', '일']
    day_name = days[now.weekday()]
    filename = f"ai발주검토_{now.strftime('%Y-%m-%d')}({day_name})_{now.strftime('%H-%M-%S')}.xlsx"
    filepath = OUTPUT_DIR / filename
    
    # 엑셀 워크북 생성
    wb = Workbook()
    ws = wb.active
    ws.title = "발주제안결과"
    
    # 헤더 설정
    base_headers = po_headers if po_headers else ["팩토리", "요청부서", "요청자", "접수일자", "입고요청일", "자재코드(물류)", "자재명", "수량", "벤더명"]
    export_headers = list(base_headers) + ['업체 담당자명', '담당자 이메일', 'AI 제안 액션 및 판단 사유', '채택 일소요량(참고)']
    ws.append(export_headers)
    
    # 스타일 정의
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                         top=Side(style='thin'), bottom=Side(style='thin'))
                         
    # 헤더 스타일 적용
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border
        
    # 데이터 행 삽입
    for idx, row in plan_df.iterrows():
        row_data = [""] * len(export_headers)
        
        # 기본 매핑
        if len(row_data) > 1: row_data[1] = row.get("date_requested", "")
        if len(row_data) > 2: row_data[2] = row.get("factory", "")
        if len(row_data) > 3: row_data[3] = row.get("department", "")
        if len(row_data) > 4: row_data[4] = row.get("requestor", "")
        if len(row_data) > 10: row_data[10] = row.get("mat_code", "")
        if len(row_data) > 12: row_data[12] = row.get("mat_name", "")
        if len(row_data) > 13: row_data[13] = row.get("qty", "")
        if len(row_data) > 21: row_data[21] = row.get("expected_date", "")
        
        # 확장 항목 매핑 (마지막 4개 컬럼)
        base_len = len(base_headers)
        if len(row_data) > base_len: row_data[base_len] = row.get("vendor_manager", "")
        if len(row_data) > base_len+1: row_data[base_len+1] = row.get("vendor_email", "")
        if len(row_data) > base_len+2: row_data[base_len+2] = row.get("action", "")
        if len(row_data) > base_len+3: row_data[base_len+3] = row.get("daily_usage", "")
        
        ws.append(row_data)
        
        current_row = ws.max_row
        for col_idx, cell in enumerate(ws[current_row], start=1):
            cell.border = thin_border
            # 수량과 액션사유는 왼쪽 정렬
            if col_idx == 14 or col_idx == len(export_headers) - 1:
                cell.alignment = left_align
            else:
                cell.alignment = center_align
                
    ws.column_dimensions['M'].width = 30
    
    wb.save(filepath)
    print(f"\n✅ 엑셀 리포트 생성이 완료되었습니다.\n경로: {filepath}")
    return filepath
```

### 파일명: `docs/harness_PO_메이네티.md`
```markdown
# 발주 로직 하드코딩: 메이네티 (Mainetti)
- **분할 납품 (Split PO)**: 재고 부족 시 팩토리별(성수, 군포, 부산) 다중 발주서 생성 지원.
- **단가 이원화 (FIFO)**: 기존단가 재고 완전 소진 시점부터 신규단가 적용 연산.
- **가변 입수량**: 박스당 입수량이 수시로 변하므로, 항상 최신 마스터 데이터의 Box Qty를 참조하여 낱개 산출.

```

### 파일명: `docs/harness_PO_애경산업.md`
```markdown
# 발주 로직 하드코딩: 애경산업
- **월간 분할 발주 (Split PO)**: 대량 발주 시 월간 총량을 주/격주 단위로 쪼개어 다중 입고일 지정.
- **수령인 강제 맵핑**: 엑셀 리포트 출력 시 "요청자" 열에 물류센터/팩토리의 실제 수령 담당자 이름을 강제 매핑.

```

### 파일명: `docs/harness_PO_지수테크.md`
```markdown
# 발주 로직 하드코딩: 지수테크
- **발주 불가(Block) 라우팅**: 지수테크 대상 하의/와이셔츠 금형 옷걸이는 발주 Block 처리하고, 대체 벤더(에버원 등)로 발주 물량 이관.
- **샘플 발주 제한**: 신규/테스트 품번의 경우 상태값을 체크하여 최대 발주량을 1박스 등 최소 수량으로 제한.

```

### 파일명: `docs/harness_PO_경동라인.md`
```markdown
# 발주 로직 하드코딩: 경동라인
- **직납 라우팅**: 부산 팩토리의 용제 및 잡자재 발주 시 경동라인으로 자동 매핑.
- **MOQ 보정**: 산출된 발주 수량이 MOQ 미달 시, MOQ 단위로 강제 올림(Ceil) 발주 처리.

```

### 파일명: `docs/harness_PO_에버원.md`
```markdown
# 발주 로직 하드코딩: 에버원 (Everone)
- **생산 캐파 제한**: 일일 최대 생산량(6,720pcs) 초과 발주 시, 일자별 분할 발주서 생성.
- **짝수 파렛트 올림**: 발주 수량 산출 후, 최종 수량을 파렛트 입수량 단위로 나눈 값이 짝수가 되도록 올림(Rounding) 처리.

```

### 파일명: `docs/harness_PO_씨에스피.md`
```markdown
# 발주 로직 하드코딩: 씨에스피
- **차량 캐파(Capacity) 환산**: 런드렛 발주 시 낱개 소요량을 5톤 차량 캐파(예: 22파렛트/20파렛트) 기준으로 환산하여 수량 보정.
- **총책임자 맵핑**: 엑셀 리포트 출력 시 비고 혹은 요청자 란에 "장현석" 등 입고 총책임자 강제 기재.

```

### 파일명: `docs/harness_PO_동진네트웍스.md`
```markdown
# 발주 로직 하드코딩: 동진네트웍스
- **배송 방법 플래그**: PO 리포트에 [벤더 직납] / [자체 배차] 여부를 판별하는 컬럼 추가.

```

### 파일명: `docs/harness_PO_케이피코리아.md`
```markdown
# 발주 로직 하드코딩: 케이피코리아
- **입고 불가 요일 회피 (Capacity 제한)**: 산출된 희망입고일이 하역장/물류센터의 입고 불가 요일에 해당할 경우, 다음 입고 가능일로 자동 Delay 연산.

```

### 파일명: `docs/harness_PO_진주크린텍.md`
```markdown
# 발주 로직 하드코딩: 진주크린텍
- **직납 라우팅**: 성수/군포 팩토리의 세탁 용제 및 카본필터 발주 시 진주크린텍으로 자동 매핑.
- **정기 납품 요일 고정**: 리드타임 연산과 무관하게, 희망입고일을 가장 가까운 **금요일** 혹은 정해진 요일로 고정 산출.
- **단위 정규화**: 현장의 팩/박스/말통 등 혼재된 요청 단위를 품목 마스터의 기본 단위로 통일 환산.

```

### 파일명: `docs/harness_PO_이루다테크.md`
```markdown
# 발주 로직 하드코딩: 이루다테크
- **수량 연동 동적 L/T**: 발주량 구간(예: 20만장/40만장/60만장 등)에 따라 리드타임을 2주~4주로 차등 적용하여 희망입고일 산출.

```

### 파일명: `docs/harness_PO_새옷처럼.md`
```markdown
# 발주 로직 하드코딩: 새옷처럼
- **단가 정규화 (VAT Exclude)**: 마스터 데이터에 부가세 포함 단가로 등록된 품번의 경우, 시스템 연산 시 `/ 1.1`을 적용하여 부가세 제외 단가로 자동 치환.

```

### 파일명: `docs/harness_PO_서흥하이텍.md`
```markdown
# 발주 로직 하드코딩: 서흥하이텍
- **고정 입수량 올림 (Rounding)**: 등대지 등 종이류 발주 시 박스당 입수량을 800개로 고정하고, 800의 배수로 강제 올림 발주.

```

