import sqlite3

DB_FILE = "pos.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # 商品表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS PRODUCT (
            PID TEXT PRIMARY KEY,
            NAME TEXT,
            PRICE REAL,
            STOCK INTEGER,
            DELETED INTEGER DEFAULT 0
        )
    ''')

    # 訂單主檔
    cur.execute('''
        CREATE TABLE IF NOT EXISTS ORDER_MASTER (
            OID TEXT PRIMARY KEY,
            DATE TEXT,
            TOTAL REAL,
            COMPLETED INTEGER DEFAULT 0
        )
    ''')

    # 訂單明細
    cur.execute('''
        CREATE TABLE IF NOT EXISTS ORDER_DETAIL (
            OID TEXT,
            PID TEXT,
            QTY INTEGER,
            SUBTOTAL REAL
        )
    ''')

    conn.commit()
    conn.close()

# 簡化版：全域流水號，從 1 開始，永不重複
def generate_pid():
    """產生 PID：P + 6位流水號 (P000001, P000002, ...)"""
    conn = get_connection()
    cur = conn.cursor()
    
    # 找最大 PID 的流水號
    cur.execute("SELECT MAX(CAST(SUBSTR(PID, 2) AS INTEGER)) FROM PRODUCT")
    result = cur.fetchone()[0]
    
    next_num = (result or 0) + 1
    conn.close()
    
    return f"P{next_num:06d}"  # P000001, P000002, ...