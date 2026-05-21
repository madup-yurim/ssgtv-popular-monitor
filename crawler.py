import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

from database import init_db, create_session, save_products

KST = timezone(timedelta(hours=9))


def _ensure_browser() -> None:
    """Playwright Chromium 바이너리 + 시스템 의존성 보장."""
    # --with-deps: 시스템 패키지까지 함께 설치 (이미 있으면 빠르게 종료)
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        # sudo 없는 환경이면 바이너리만 설치 시도
        result2 = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True, text=True,
        )
        if result2.returncode != 0:
            print(result2.stdout, flush=True)
            print(result2.stderr, flush=True)
            raise RuntimeError(f"Playwright 설치 실패:\n{result2.stderr}")

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
    page.wait_for_selector("div.card.gtm_list_item", timeout=30000)
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass  # networkidle 타임아웃은 무시 (카드가 이미 로드됐으면 진행)


def _get_category_name(page: Page, category_id: str) -> str:
    try:
        el = page.locator(f'a[href*="/category/{category_id}"]').first
        return el.text_content(timeout=3000).strip()
    except Exception:
        return category_id


def crawl_category(page: Page, category: dict) -> tuple[str, list[dict]]:
    """한 카테고리의 1~2페이지 상품을 크롤링. (category_name, products) 반환"""
    page.goto(category["url"], wait_until="domcontentloaded", timeout=30000)
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


def _crawl_category_worker(cat: dict) -> tuple[str, list[dict]]:
    """독립 playwright 인스턴스로 카테고리 수집 (스레드 안전)."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 900})
            return crawl_category(page, cat)
        except Exception as e:
            print(f"  [{cat['id']}] 수집 실패: {e}")
            return cat["id"], []
        finally:
            browser.close()


def crawl_all() -> int:
    """4개 카테고리 병렬 수집 → DB 저장 → session_id 반환"""
    _ensure_browser()
    init_db()
    collected_at = datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S")
    session_id = create_session(collected_at)

    all_products: list[dict] = []
    with ThreadPoolExecutor(max_workers=len(CATEGORIES)) as executor:
        futures = {executor.submit(_crawl_category_worker, cat): cat for cat in CATEGORIES}
        for future in as_completed(futures):
            _, products = future.result()
            all_products.extend(products)

    save_products(session_id, all_products)
    print(f"수집 완료 - session_id={session_id}, collected_at={collected_at}, 총 {len(all_products)}개")
    return session_id


if __name__ == "__main__":
    crawl_all()
