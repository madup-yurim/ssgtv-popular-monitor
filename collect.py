"""
통합 수집 진입점: 크롤링 → 시트 직접 쓰기 (subprocess 1회만).

- crawler.crawl_all_to_memory(): 메모리에 수집 (SQLite 안 거침)
- sheets_writer.write_products_to_sheets(): 시트에 바로 append
- 로컬 환경에서는 백업용으로 SQLite에도 저장 (옵셔널)

환경변수:
- GCP_SA_JSON: 서비스계정 JSON (Streamlit Cloud용)
- 없으면 service_account.json 파일 사용 (로컬용)
"""

import json
import os
import sys
import traceback

from crawler import crawl_all_to_memory
from sheets_writer import write_products_to_sheets


def _save_to_sqlite_optional(collected_at: str, products: list[dict]) -> None:
    """로컬 백업용 SQLite 저장. 실패해도 무시."""
    try:
        from database import init_db, create_session, save_products
        init_db()
        session_id = create_session(collected_at)
        save_products(session_id, products)
        print(f"  SQLite 백업 완료 (session_id={session_id})")
    except Exception as e:
        print(f"  SQLite 백업 스킵: {e}")


def main() -> dict:
    print("=" * 50)
    print("1단계: 크롤링")
    print("=" * 50)
    collected_at, products = crawl_all_to_memory()

    if not products:
        raise RuntimeError("수집된 상품이 없습니다.")

    print()
    print("=" * 50)
    print("2단계: SQLite 백업 (베스트에포트)")
    print("=" * 50)
    _save_to_sqlite_optional(collected_at, products)

    print()
    print("=" * 50)
    print("3단계: 시트 업데이트")
    print("=" * 50)
    result = write_products_to_sheets(collected_at, products)
    result["collected_at"] = collected_at
    result["total_products"] = len(products)
    return result


if __name__ == "__main__":
    try:
        result = main()
        print()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)
    except Exception as e:
        print(f"\n실패: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
