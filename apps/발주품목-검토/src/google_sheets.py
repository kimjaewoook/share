import os
import google.auth
from googleapiclient.discovery import build
from google.oauth2 import service_account
from config.settings import GOOGLE_CREDENTIALS_PATH

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# L2: Service 객체를 모듈 레벨에서 1회만 생성하여 재사용
_service = None

def _get_service():
    global _service
    if _service is not None:
        return _service
    credentials = None
    if GOOGLE_CREDENTIALS_PATH and os.path.exists(GOOGLE_CREDENTIALS_PATH):
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
    else:
        credentials, _ = google.auth.default(scopes=SCOPES)
    _service = build('sheets', 'v4', credentials=credentials)
    return _service

def get_sheet_data(spreadsheet_id, range_name):
    """
    Google Sheets API를 사용하여 특정 스프레드시트의 데이터를 가져옵니다.
    """
    service = _get_service()
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])
    return values