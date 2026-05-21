import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

HERE = Path(__file__).parent

st.set_page_config(
    page_title="신세계쇼핑 인기상품 모니터링",
    layout="wide",
    page_icon="🛒",
)

st.title("🛒 신세계쇼핑 인기상품 모니터링")

IS_CLOUD = "gcp_service_account" in st.secrets

# ── 수집 버튼 (항상 표시) ──────────────────────────────────
col_btn, col_status = st.columns([2, 8])

with col_btn:
    collect = st.button("📥 수집하기", type="primary", use_container_width=True)

if collect:
    # 1단계: 크롤링
    status = col_status.empty()
    status.info("🕷️ 크롤링 중... (1~2분 소요)")

    result = subprocess.run(
        [sys.executable, str(HERE / "crawler.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(HERE),
    )

    if result.returncode != 0:
        status.error("크롤링 실패")
        with st.expander("에러 상세 보기", expanded=True):
            st.code(result.stderr[-1500:] if result.stderr else result.stdout[-1500:])
        st.stop()

    # 2단계: 시트 자동 업데이트
    sa = HERE / "service_account.json"
    if sa.exists():
        status.info("📊 시트 업데이트 중...")
        sheets_result = subprocess.run(
            [sys.executable, str(HERE / "sheets_writer.py")],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(HERE),
        )
        if sheets_result.returncode == 0:
            status.success("✅ 수집 완료! 시트도 업데이트됐습니다.")
        else:
            status.warning("⚠️ 수집은 완료됐지만 시트 업데이트 실패")
            st.text(sheets_result.stderr[-400:])
    else:
        status.success("✅ 수집 완료!")

    # 3단계: Sheets 캐시 초기화 후 재로딩
    if IS_CLOUD:
        if "refresh_count" not in st.session_state:
            st.session_state.refresh_count = 0
        st.session_state.refresh_count += 1

    st.rerun()

st.divider()

# ── 데이터 로드 + 세션 선택 ──────────────────────────────
if IS_CLOUD:
    from sheets_reader import get_sessions_from_sheets, load_all_from_sheets

    if "refresh_count" not in st.session_state:
        st.session_state.refresh_count = 0

    with st.spinner("데이터 로딩 중..."):
        all_df = load_all_from_sheets(refresh_count=st.session_state.refresh_count)

    if all_df.empty:
        st.info("수집 데이터가 없습니다. 위 버튼으로 수집해주세요.")
        st.stop()

    sessions = get_sessions_from_sheets(all_df)
    selected_session = st.selectbox(
        "수집 회차",
        options=sessions,
        label_visibility="collapsed",
    )
    df = all_df[all_df["collected_at"] == selected_session].copy()
    collected_at_label = selected_session

else:
    from database import get_products, get_sessions, init_db

    init_db()
    sessions = get_sessions()
    real_sessions = [s for s in sessions if len(get_products(s["id"])) >= 50]

    if not real_sessions:
        st.info("수집 데이터가 없습니다. 위 버튼으로 수집해주세요.")
        st.stop()

    session_labels = {s["id"]: s["collected_at"].replace("T", " ") for s in real_sessions}
    selected_id = st.selectbox(
        "수집 회차",
        options=list(session_labels.keys()),
        format_func=lambda x: session_labels[x],
        label_visibility="collapsed",
    )
    df = pd.DataFrame(get_products(selected_id))
    collected_at_label = session_labels[selected_id]

st.divider()

# ── 카테고리 필터 ──────────────────────────────────────────
categories = sorted(df["category_name"].unique().tolist())
selected_cats = st.multiselect(
    "카테고리 필터",
    options=categories,
    default=categories,
)

if not selected_cats:
    st.warning("카테고리를 1개 이상 선택해주세요.")
    st.stop()

df = df[df["category_name"].isin(selected_cats)].copy()

# ── 요약 지표 ─────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("총 상품수", f"{len(df):,}개")
m2.metric("카테고리", f"{df['category_name'].nunique()}개")
avg_price = df[df["price"] > 0]["price"].mean()
m3.metric("평균 판매가", f"{int(avg_price):,}원" if pd.notna(avg_price) else "—")
m4.metric("평균 평점", f"{df[df['rating']>0]['rating'].mean():.2f}" if df["rating"].any() else "—")
m5.metric("평균 리뷰수", f"{int(df[df['review_count']>0]['review_count'].mean()):,}건" if df["review_count"].any() else "—")

st.divider()

# ── 테이블 ────────────────────────────────────────────────
display = df[[
    "rank", "category_name", "image_url", "product_name", "brand",
    "category_path", "price", "badge", "rating", "review_count",
    "card_benefit", "shipping", "product_url",
]].copy()

display.columns = [
    "순위", "카테고리", "이미지", "상품명", "브랜드",
    "카테고리경로", "판매가(원)", "배지", "평점", "리뷰수",
    "카드혜택", "배송", "상품URL",
]

display = display.sort_values(["카테고리", "순위"]).reset_index(drop=True)

st.dataframe(
    display,
    use_container_width=True,
    height=700,
    column_config={
        "이미지": st.column_config.ImageColumn("이미지", width="small"),
        "상품명": st.column_config.TextColumn("상품명", width="large"),
        "상품URL": st.column_config.LinkColumn("링크", display_text="보기"),
        "판매가(원)": st.column_config.NumberColumn("판매가(원)", format="%d"),
        "리뷰수": st.column_config.NumberColumn("리뷰수", format="%d"),
        "평점": st.column_config.NumberColumn("평점", format="%.1f"),
        "순위": st.column_config.NumberColumn("순위", width="small"),
    },
    hide_index=True,
)

st.caption(f"수집 시각: {collected_at_label}  |  총 {len(df):,}개 상품")
