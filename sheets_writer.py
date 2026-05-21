"""
Google Sheets 업데이트 모듈.
SQLite 세션 데이터를 지정 스프레드시트에 누적 기록한다.

설정 방법: README_SHEETS_SETUP.md 참고
"""

import json
import os
from pathlib import Path

import gspread

from database import get_products, get_sessions

SPREADSHEET_ID = "1NR55kj6kwK1vSG3J-3T_IROYibAgv5WUqw46adh3sKU"
SERVICE_ACCOUNT_PATH = Path(__file__).parent / "service_account.json"


def _client() -> gspread.Client:
    """환경변수 GCP_SA_JSON → service_account.json 파일 순으로 인증."""
    # 1순위: 환경변수 (app.py가 st.secrets → JSON → 환경변수로 전달)
    sa_json = os.environ.get("GCP_SA_JSON")
    if sa_json:
        info = json.loads(sa_json)
        return gspread.service_account_from_dict(info)
    # 2순위: 로컬 파일
    if SERVICE_ACCOUNT_PATH.exists():
        return gspread.service_account(filename=str(SERVICE_ACCOUNT_PATH))
    raise FileNotFoundError(
        f"서비스 계정 키를 찾을 수 없습니다.\n"
        f"  - 환경변수 GCP_SA_JSON 을 설정하거나\n"
        f"  - 로컬: {SERVICE_ACCOUNT_PATH} 파일을 배치하세요."
    )

COLUMNS = [
    "No", "수집일시", "카테고리", "순위",
    "상품ID", "상품명", "브랜드", "카테고리경로",
    "판매가(원)", "평점", "리뷰수", "배지",
    "배송", "카드혜택", "상품URL", "이미지URL",
]


def _ensure_header(ws: gspread.Worksheet) -> list[list]:
    """헤더가 없으면 추가하고, 기존 전체 데이터를 반환한다."""
    all_values = ws.get_all_values()
    if not all_values:
        ws.append_row(COLUMNS, value_input_option="RAW")
        ws.format("A1:P1", {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.2, "green": 0.5, "blue": 0.8},
        })
        return []
    return all_values


def write_to_sheets(session_id: int | None = None) -> dict:
    """
    session_id: None이면 최신 세션 사용
    이미 시트에 해당 수집일시 데이터가 있으면 스킵한다 (중복 방지).
    반환: {"sheet_url": str, "rows_written": int, "skipped": bool}
    """
    # 최신 세션 자동 선택
    if session_id is None:
        sessions = get_sessions()
        real = [s for s in sessions if len(get_products(s["id"])) >= 50]
        if not real:
            raise ValueError("수집된 데이터가 없습니다. 먼저 크롤러를 실행하세요.")
        session_id = real[0]["id"]

    products = get_products(session_id)
    if not products:
        raise ValueError(f"session_id={session_id} 에 상품 데이터가 없습니다.")

    collected_at = next(
        s["collected_at"] for s in get_sessions() if s["id"] == session_id
    )
    collected_str = collected_at.replace("T", " ")

    gc = _client()
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    ws = spreadsheet.get_worksheet(0)

    # 헤더 확인 + 기존 데이터 로드
    all_values = _ensure_header(ws)

    # 중복 체크: 이미 이 수집일시 데이터가 있으면 스킵
    existing_sessions = {row[1] for row in all_values[1:] if len(row) > 1}
    if collected_str in existing_sessions:
        sheet_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
        print(f"SKIP: {collected_str} already exists in sheet")
        return {"sheet_url": sheet_url, "rows_written": 0, "skipped": True}

    # 기존 No 최댓값 계산 (이어서 번호 부여)
    existing_nos = []
    for row in all_values[1:]:
        try:
            existing_nos.append(int(row[0]))
        except (ValueError, IndexError):
            pass
    start_no = max(existing_nos, default=0) + 1

    rows = []
    for i, p in enumerate(products, start=start_no):
        rows.append([
            i,
            collected_str,
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

    sheet_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
    print(f"OK: {len(rows)}rows appended (session: {collected_str})")
    print(f"URL: {sheet_url}")
    return {"sheet_url": sheet_url, "rows_written": len(rows), "skipped": False}


if __name__ == "__main__":
    result = write_to_sheets()
    print(json.dumps(result, ensure_ascii=False, indent=2))
