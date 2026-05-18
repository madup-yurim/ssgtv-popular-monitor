"""
Google Sheets 업데이트 모듈.
SQLite 최신 세션 데이터를 지정 스프레드시트에 기록한다.

설정 방법: README_SHEETS_SETUP.md 참고
"""

import json
from datetime import datetime
from pathlib import Path

import gspread
from gspread.exceptions import SpreadsheetNotFound

from database import get_products, get_sessions

SPREADSHEET_ID = "1NR55kj6kwK1vSG3J-3T_IROYibAgv5WUqw46adh3sKU"
SERVICE_ACCOUNT_PATH = Path(__file__).parent / "service_account.json"

COLUMNS = [
    "No", "수집일시", "카테고리", "순위",
    "상품ID", "상품명", "브랜드", "카테고리경로",
    "판매가(원)", "평점", "리뷰수", "배지",
    "배송", "카드혜택", "상품URL", "이미지URL",
]


def _get_or_create_sheet(spreadsheet: gspread.Spreadsheet, tab_name: str) -> gspread.Worksheet:
    try:
        return spreadsheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=tab_name, rows=2000, cols=len(COLUMNS))
        ws.append_row(COLUMNS, value_input_option="RAW")
        ws.format("A1:P1", {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.2, "green": 0.5, "blue": 0.8},
        })
        return ws


def write_to_sheets(session_id: int | None = None, tab_name: str | None = None) -> dict:
    """
    session_id: None이면 최신 세션 사용
    tab_name: None이면 수집일자(YYYY-MM-DD) 탭 사용
    반환: {"sheet_url": str, "rows_written": int, "tab": str}
    """
    if not SERVICE_ACCOUNT_PATH.exists():
        raise FileNotFoundError(
            f"서비스 계정 키 파일이 없습니다: {SERVICE_ACCOUNT_PATH}\n"
            "README_SHEETS_SETUP.md 를 참고해 설정해주세요."
        )

    # 최신 세션 자동 선택
    if session_id is None:
        sessions = get_sessions()
        real = [s for s in sessions if get_products(s["id"])]
        if not real:
            raise ValueError("수집된 데이터가 없습니다. 먼저 크롤러를 실행하세요.")
        session_id = real[0]["id"]

    products = get_products(session_id)
    if not products:
        raise ValueError(f"session_id={session_id} 에 상품 데이터가 없습니다.")

    collected_at = next(
        s["collected_at"] for s in get_sessions() if s["id"] == session_id
    )
    if tab_name is None:
        tab_name = collected_at[:10]  # YYYY-MM-DD

    gc = gspread.service_account(filename=str(SERVICE_ACCOUNT_PATH))
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    ws = _get_or_create_sheet(spreadsheet, tab_name)

    # 기존 데이터 지우고 헤더 다시 쓰기
    ws.clear()
    ws.append_row(COLUMNS, value_input_option="RAW")

    rows = []
    for i, p in enumerate(products, start=1):
        rows.append([
            i,
            collected_at.replace("T", " "),
            p.get("category_name", ""),
            p.get("rank", ""),
            p.get("product_id", ""),
            p.get("product_name", ""),
            p.get("brand", ""),
            p.get("category_path", ""),
            p.get("price", ""),
            p.get("rating", ""),
            p.get("review_count", ""),
            p.get("badge", ""),
            p.get("shipping", ""),
            p.get("card_benefit", ""),
            p.get("product_url", ""),
            p.get("image_url", ""),
        ])

    ws.append_rows(rows, value_input_option="RAW")

    sheet_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid={ws.id}"
    print(f"✅ {len(rows)}행 → {tab_name} 탭 업데이트 완료")
    print(f"📊 {sheet_url}")
    return {"sheet_url": sheet_url, "rows_written": len(rows), "tab": tab_name}


if __name__ == "__main__":
    result = write_to_sheets()
    print(json.dumps(result, ensure_ascii=False, indent=2))
