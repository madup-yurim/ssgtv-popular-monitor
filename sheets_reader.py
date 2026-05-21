"""Google Sheets에서 누적 데이터를 읽어 DataFrame으로 반환한다."""

from pathlib import Path

import gspread
import pandas as pd
import streamlit as st

SPREADSHEET_ID = "1NR55kj6kwK1vSG3J-3T_IROYibAgv5WUqw46adh3sKU"

_COL_MAP = {
    "순위": "rank",
    "카테고리": "category_name",
    "이미지URL": "image_url",
    "상품명": "product_name",
    "브랜드": "brand",
    "카테고리경로": "category_path",
    "판매가(원)": "price",
    "배지": "badge",
    "평점": "rating",
    "리뷰수": "review_count",
    "카드혜택": "card_benefit",
    "배송": "shipping",
    "상품URL": "product_url",
    "수집일시": "collected_at",
}


def _client() -> gspread.Client:
    if "gcp_service_account" in st.secrets:
        return gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
    sa = Path(__file__).parent / "service_account.json"
    return gspread.service_account(filename=str(sa))


@st.cache_data(ttl=60)
def load_all_from_sheets() -> pd.DataFrame:
    """시트 전체 데이터를 읽어 DataFrame으로 반환."""
    gc = _client()
    ws = gc.open_by_key(SPREADSHEET_ID).get_worksheet(0)
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records).rename(columns=_COL_MAP)
    for col in ("rank", "price", "review_count"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0.0)
    return df


def get_sessions_from_sheets(df: pd.DataFrame) -> list[str]:
    """수집일시 목록을 최신순으로 반환."""
    if "collected_at" not in df.columns:
        return []
    return sorted(df["collected_at"].unique().tolist(), reverse=True)
