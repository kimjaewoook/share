import gspread
from gspread_formatting import *
import pandas as pd
from typing import List
from config import SPREADSHEET_ID, SERVICE_ACCOUNT_FILE, logger

class GoogleSheetsManager:
    def __init__(self):
        self.gc = gspread.service_account(filename=str(SERVICE_ACCOUNT_FILE))
        self.sh = self.gc.open_by_key(SPREADSHEET_ID)

    def _get_or_create_worksheet(self, title: str) -> gspread.Worksheet:
        try:
            return self.sh.worksheet(title)
        except gspread.exceptions.WorksheetNotFound:
            logger.info(f"Worksheet '{title}' not found. Creating it.")
            return self.sh.add_worksheet(title=title, rows=1000, cols=20)

    def get_main_sheet_data(self) -> pd.DataFrame:
        ws = self._get_or_create_worksheet("Main")
        all_values = ws.get_all_values()
        if not all_values:
            return pd.DataFrame()
        headers = all_values[0]
        data = all_values[1:]
        return pd.DataFrame(data, columns=headers)

    def sync_main_sheet(self, df_all: pd.DataFrame, df_changed: pd.DataFrame = None):
        ws = self._get_or_create_worksheet("Main")
        ws.clear()
        
        # Replace NaN with empty string
        df_safe = df_all.astype(object).fillna("")
        
        # Write Header and values
        columns = df_safe.columns.tolist()
        values = [columns] + df_safe.values.tolist()
        ws.update(range_name='A1', values=values, value_input_option='USER_ENTERED')
        
        try:
            fmt = cellFormat(numberFormat=numberFormat(type='NUMBER', pattern='#,##0'))
            format_cell_range(ws, 'H2:H', fmt)
        except Exception as e:
            logger.warning(f"천단위 서식 적용 실패: {e}")
            
        logger.info(f"구글 시트 'Main' 탭에 총 {len(df_safe)}건의 최신 현황이 깔끔하게 업데이트되었습니다.")
                
    def append_changelog_sheet(self, df_changed: pd.DataFrame):
        if df_changed is None or df_changed.empty:
            return
            
        ws = self._get_or_create_worksheet("ChangeLog")
        df_safe = df_changed.astype(object).fillna("")
        
        # If empty, write header
        if not ws.get_all_values():
            ws.append_row(df_safe.columns.tolist(), value_input_option='USER_ENTERED')
            
        ws.append_rows(df_safe.values.tolist(), value_input_option='USER_ENTERED')
        
        try:
            fmt = cellFormat(numberFormat=numberFormat(type='NUMBER', pattern='#,##0'))
            format_cell_range(ws, 'H2:H', fmt)
        except Exception as e:
            logger.warning(f"천단위 서식 적용 실패: {e}")
            
        logger.info(f"오늘 새롭게 바뀐 {len(df_changed)}건의 문서는 'ChangeLog' 탭에 추가로 기록을 남겨두었습니다.")
        
    def update_slack_sheet(self, slack_messages: list):
        ws = self._get_or_create_worksheet("SlackMessages")
        ws.clear()
        
        # Just write as two columns: A=결재대기자, B=메시지
        if not slack_messages:
            ws.update(range_name='A1', values=[["메시지 생성 내역 없음"]])
            return
        
        values = [["결재대기자", "메시지 내용"]]
        for item in slack_messages:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                values.append([item[0], item[1]])
            else:
                values.append(["", str(item)])
        
        ws.update(range_name='A1', values=values)
        logger.info(f"담당자별로 발송할 슬랙 알림 메시지 {len(slack_messages)}건을 훌륭하게 정리하여 시트에 담아두었습니다.")
