import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join('data', 'cafe_bot.db')


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    if not os.path.exists('data'):
        os.makedirs('data')
    with get_conn() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS cart
                        (user_id INTEGER, item TEXT, count INTEGER)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS orders
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         user_id INTEGER, details TEXT, method TEXT,
                         address TEXT, phone TEXT, name TEXT, status TEXT)''')
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cart_user     ON cart(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_user   ON orders(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")


def add_to_cart_db(user_id: int, item: str) -> None:
    with get_conn() as conn:
        exists = conn.execute(
            "SELECT 1 FROM cart WHERE user_id = ? AND item = ?", (user_id, item)
        ).fetchone()
        if exists:
            conn.execute(
                "UPDATE cart SET count = count + 1 WHERE user_id = ? AND item = ?",
                (user_id, item)
            )
        else:
            conn.execute(
                "INSERT INTO cart (user_id, item, count) VALUES (?, ?, 1)",
                (user_id, item)
            )


def remove_from_cart_db(user_id: int, item: str) -> None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT count FROM cart WHERE user_id = ? AND item = ?", (user_id, item)
        ).fetchone()
        if not row:
            return
        if row["count"] > 1:
            conn.execute(
                "UPDATE cart SET count = count - 1 WHERE user_id = ? AND item = ?",
                (user_id, item)
            )
        else:
            conn.execute(
                "DELETE FROM cart WHERE user_id = ? AND item = ?",
                (user_id, item)
            )


def get_cart_db(user_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT item, count FROM cart WHERE user_id = ?", (user_id,)
        ).fetchall()


def clear_cart_db(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))


def add_order_to_db(user_id: int, details: str, method: str,
                    address: str, phone: str, name: str) -> int:
    with get_conn() as conn:
        cursor = conn.execute(
            '''INSERT INTO orders (user_id, details, method, address, phone, name, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, details, method, address, phone, name, "В обработке")
        )
        return cursor.lastrowid


def get_orders_by_status(user_id: int = None) -> list:
    with get_conn() as conn:
        if user_id:
            return conn.execute(
                "SELECT id, details, status FROM orders "
                "WHERE user_id = ? ORDER BY id DESC",
                (user_id,)
            ).fetchall()
        return conn.execute(
            "SELECT id, details, status FROM orders "
            "WHERE status NOT IN ('Доставлен', 'Отменен') ORDER BY id DESC"
        ).fetchall()


def update_order_status(order_id: int, new_status: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id)
        )


def get_order_user_id(order_id: int) -> int | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT user_id FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        return row["user_id"] if row else None
