import pandas as pd
import plotly.express as px
import streamlit as st

from crawler import crawl_all
from database import get_products, get_sessions, init_db

st.set_page_config(
    page_title="신세계쇼핑 인기상품 모니터링",
    page_icon="🛒",
    layout="wide",
)

init_db()

# ── 사이드바 ──────────────────────────────────────────────
with st.sidebar:
    st.title("🛒 인기상품 모니터링")

    if st.button("📥 지금 수집", use_container_width=True, type="primary"):
        with st.spinner("수집 중... (1~2분 소요)"):
            crawl_all()
        st.success("수집 완료!")
        st.rerun()

    sessions = get_sessions()
    if not sessions:
        st.info("수집 데이터가 없습니다. 위 버튼으로 수집해주세요.")
        st.stop()

    session_labels = {s["id"]: s["collected_at"].replace("T", " ") for s in sessions}
    selected_id = st.selectbox(
        "수집 회차 선택",
        options=list(session_labels.keys()),
        format_func=lambda x: session_labels[x],
    )

    all_products = get_products(selected_id)
    df_all = pd.DataFrame(all_products)

    categories = sorted(df_all["category_name"].unique().tolist())
    selected_cats = st.multiselect("카테고리 필터", categories, default=categories)

df = df_all[df_all["category_name"].isin(selected_cats)].copy()

# ── 요약 지표 ─────────────────────────────────────────────
st.subheader("요약")
c1, c2, c3, c4 = st.columns(4)
c1.metric("총 상품수", f"{len(df):,}개")
c2.metric("평균 판매가", f"{int(df['price'].mean()):,}원" if len(df) else "—")
c3.metric("평균 평점", f"{df['rating'].mean():.2f}" if len(df) else "—")
c4.metric("평균 리뷰수", f"{int(df['review_count'].mean()):,}건" if len(df) else "—")

st.divider()

# ── 차트 ─────────────────────────────────────────────────
st.subheader("분석")
col1, col2 = st.columns(2)

with col1:
    brand_counts = (
        df["brand"]
        .value_counts()
        .head(15)
        .reset_index()
    )
    brand_counts.columns = ["브랜드", "상품수"]
    fig_brand = px.bar(
        brand_counts,
        x="상품수",
        y="브랜드",
        orientation="h",
        title="브랜드별 인기상품 수 (Top 15)",
        color="상품수",
        color_continuous_scale="Blues",
    )
    fig_brand.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
    st.plotly_chart(fig_brand, use_container_width=True)

with col2:
    badge_counts = df["badge"].replace("", "없음").value_counts().reset_index()
    badge_counts.columns = ["배지", "상품수"]
    fig_badge = px.pie(
        badge_counts,
        names="배지",
        values="상품수",
        title="배지 분포",
        hole=0.4,
    )
    st.plotly_chart(fig_badge, use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    fig_price = px.histogram(
        df[df["price"] > 0],
        x="price",
        nbins=30,
        title="가격 분포",
        labels={"price": "판매가 (원)"},
        color_discrete_sequence=["#636EFA"],
    )
    st.plotly_chart(fig_price, use_container_width=True)

with col4:
    fig_rating = px.histogram(
        df[df["rating"] > 0],
        x="rating",
        nbins=20,
        title="평점 분포",
        labels={"rating": "평점"},
        color_discrete_sequence=["#EF553B"],
    )
    st.plotly_chart(fig_rating, use_container_width=True)

st.divider()

# ── 상품 목록 ─────────────────────────────────────────────
st.subheader("상품 목록")

tabs = st.tabs(selected_cats + ["전체"])

for i, cat in enumerate(selected_cats + ["전체"]):
    with tabs[i]:
        subset = df if cat == "전체" else df[df["category_name"] == cat]
        subset = subset.sort_values("rank").reset_index(drop=True)

        display_df = subset[[
            "rank", "image_url", "product_name", "brand",
            "category_path", "price", "badge", "rating",
            "review_count", "card_benefit", "shipping", "product_url"
        ]].copy()
        display_df.columns = [
            "순위", "이미지", "상품명", "브랜드",
            "카테고리", "판매가(원)", "배지", "평점",
            "리뷰수", "카드혜택", "배송", "상품URL"
        ]

        st.dataframe(
            display_df,
            column_config={
                "이미지": st.column_config.ImageColumn("이미지", width="small"),
                "상품명": st.column_config.TextColumn("상품명", width="large"),
                "상품URL": st.column_config.LinkColumn("상품URL"),
                "판매가(원)": st.column_config.NumberColumn("판매가(원)", format="%d"),
                "리뷰수": st.column_config.NumberColumn("리뷰수", format="%d"),
            },
            use_container_width=True,
            height=600,
        )
