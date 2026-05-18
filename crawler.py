from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, Page

from database import init_db, create_session, save_products

CATEGORIES = [
    {"id": "30100020", "url": "https://www.shinsegaetvshopping.com/category/30100020?trackSearchType=y_pc_category&new_odd=y"},
    {"id": "30100005", "url": "https://www.shinsegaetvshopping.com/category/30100005?trackSearchType=y_pc_category"},
    {"id": "30100001", "url": "https://www.shinsegaetvshopping.com/category/30100001?trackSearchType=y_pc_category"},
    {"id": "30102001", "url": "https://www.shinsegaetvshopping.com/category/30102001?trackSearchType=y_pc_category"},
]

_JS_EXTRACT = """() => {
    const cards = document.querySelectorAll('div.card.gtm_list_item');
    return Array.from(cards).map(card => ({
        product_id:    card.dataset.gtmItemId    || '',
        product_name:  card.dataset.gtmItemName  || '',
        brand:         card.dataset.gtmItemBrand || '',
        category_path: card.dataset.gtmItemCategory  || '',
        badge:         card.dataset.gtmItemCategory2 || '',
        rank:          parseInt(card.dataset.gtmItemIndex) || 0,
        price:         parseInt((card.querySelector('._bestPrice')?.textContent || '0').replace(/,/g, '')) || 0,
        image_url:     card.querySelector('img._image')?.src || '',
        rating:        parseFloat(card.querySelector('.score')?.textContent?.trim() || '0') || 0.0,
        review_count:  parseInt((card.querySelector('.count em')?.textContent || '0').replace(/,/g, '')) || 0,
        card_benefit:  [
            card.querySelector('._promoCharge')?.textContent?.trim(),
            card.querySelector('._norestYn')?.textContent?.trim()
        ].filter(Boolean).join(' '),
        shipping:      card.querySelector('._ordCostYn')?.textContent?.trim() || '',
        product_url:   'https://www.shinsegaetvshopping.com/display/detail/' + card.dataset.gtmItemId
    }));
}"""


def _wait_for_products(page: Page) -> None:
    page.wait_for_selector("div.card.gtm_list_item", timeout=15000)
    page.wait_for_load_state("networkidle", timeout=15000)


def _get_category_name(page: Page, category_id: str) -> str:
    try:
        el = page.locator(f'a[href*="/category/{category_id}"]').first
        return el.text_content(timeout=3000).strip()
    except Exception:
        return category_id


def crawl_category(page: Page, category: dict) -> tuple[str, list[dict]]:
    """한 카테고리의 1~2페이지 상품을 크롤링. (category_name, products) 반환"""
    page.goto(category["url"], wait_until="domcontentloaded")
    _wait_for_products(page)

    category_name = _get_category_name(page, category["id"])
    products_p1: list[dict] = page.evaluate(_JS_EXTRACT)

    # 페이지 2 로드
    page.evaluate("goodsListPage(2)")
    _wait_for_products(page)
    page.wait_for_timeout(800)
    products_p2: list[dict] = page.evaluate(_JS_EXTRACT)

    # 페이지 2 rank는 p1 마지막 rank 이후로 오프셋
    p1_count = len(products_p1)
    for p in products_p2:
        p["rank"] = p["rank"] + p1_count

    all_products = products_p1 + products_p2
    for p in all_products:
        p["category_id"] = category["id"]
        p["category_name"] = category_name

    print(f"  [{category_name}] {len(all_products)}개 수집")
    return category_name, all_products


def crawl_all() -> int:
    """4개 카테고리 전체 수집 → DB 저장 → session_id 반환"""
    init_db()
    collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    session_id = create_session(collected_at)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 900})

            for cat in CATEGORIES:
                try:
                    _, products = crawl_category(page, cat)
                    save_products(session_id, products)
                except Exception as e:
                    print(f"  [{cat['id']}] 수집 실패: {e}")
        finally:
            browser.close()

    print(f"수집 완료 - session_id={session_id}, collected_at={collected_at}")
    return session_id


if __name__ == "__main__":
    crawl_all()
