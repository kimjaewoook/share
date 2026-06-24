import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import gspread
import requests
import json
from config import SERVICE_ACCOUNT_FILE

def run():
    gc = gspread.service_account(filename=str(SERVICE_ACCOUNT_FILE))
    SHEET_ID = "1OW405qapjFE5pPWaXKfqHPQ72KdHg33eO47Q7VpQAec"
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?includeGridData=true&ranges=A1:Z50"
    resp = gc.http_client.request('get', url).json()

    out_path = Path(__file__).resolve().parent.parent / "output" / "sheet_debug.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resp, f, ensure_ascii=False, indent=2)
    print(f"Debug data saved to {out_path}")

if __name__ == '__main__':
    run()
