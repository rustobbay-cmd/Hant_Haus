import sqlite3

DB_PATH = '/root/Cafe_bot/orders.db'

def add_order_to_db(user_id, items, method, address, phone, user_name, comment):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (user_id, items, method, address, phone, user_name, comment, status) 
        VALUES (?, ?, ?, ?, ?, ?, ?, 'В обработке')
    ''', (user_id, items, method, address, phone, user_name, comment))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_orders_by_status():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Берем все, кроме доставленных и отмененных
    cursor.execute("SELECT id, items, status FROM orders WHERE status NOT IN ('Доставлен', 'Отменен')")
    orders = cursor.fetchall()
    conn.close()
    return orders

def update_order_status(order_id, status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()

def get_order_user_id(order_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM orders WHERE id = ?", (order_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            items TEXT,
            method TEXT,
            address TEXT,
            phone TEXT,
            user_name TEXT,
            comment TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()
