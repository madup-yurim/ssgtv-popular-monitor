import sqlite3
from pathlib import Path

DB_PATH = Path("data/products.db")


def init_db() -> None:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS collection_sessions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            collected_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS products (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    INTEGER NOT NULL,
            category_id   TEXT NOT NULL,
            category_name TEXT NOT NULL,
            rank          INTEGER,
            product_id    TEXT,
            product_name  TEXT,
            brand         TEXT,
            category_path TEXT,
            price         INTEGER,
            badge         TEXT,
            rating        REAL,
            review_count  INTEGER,
            card_benefit  TEXT,
            shipping      TEXT,
            product_url   TEXT,
            image_url     TEXT,
            FOREIGN KEY (session_id) REFERENCES collection_sessions(id)
        );
    """)
    conn.commit()
    conn.close()


def create_session(collected_at: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO collection_sessions (collected_at) VALUES (?)",
        (collected_at,)
    )
    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return session_id


def save_products(session_id: int, products: list[dict]) -> None:
    if not products:
        return
    conn = sqlite3.connect(DB_PATH)
    conn.executemany(
        """INSERT INTO products
           (session_id, category_id, category_name, rank, product_id,
            product_name, brand, category_path, price, badge, rating,
            review_count, card_benefit, shipping, product_url, image_url)
           VALUES
           (:session_id, :category_id, :category_name, :rank, :product_id,
            :product_name, :brand, :category_path, :price, :badge, :rating,
            :review_count, :card_benefit, :shipping, :product_url, :image_url)""",
        [{**p, "session_id": session_id} for p in products]
    )
    conn.commit()
    conn.close()


def get_sessions() -> list[dict]:
    """최신순으로 수집 세션 목록 반환"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, collected_at FROM collection_sessions ORDER BY collected_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_products(session_id: int) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM products WHERE session_id = ? ORDER BY category_id, rank",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
