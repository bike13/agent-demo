"""数据库连接和初始化"""
import sqlite3
from contextlib import contextmanager
from typing import Generator
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ecommerce.db")

# 确保数据目录存在
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """获取数据库连接的上下文管理器"""
    conn = sqlite3.connect(DB_PATH)
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
    """初始化数据库表"""
    with get_db() as conn:
        cursor = conn.cursor()
        # 创建用户表，包含用户名、角色（商家/买家）、余额、创建时间等字段
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tc_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 主键自增
                username TEXT UNIQUE NOT NULL,         -- 用户名，唯一且不能为空
                role TEXT NOT NULL CHECK(role IN ('seller', 'buyer')),  -- 用户角色，只能为 seller 或 buyer
                balance REAL DEFAULT 0,                -- 账户余额，默认为0
                created_at TEXT DEFAULT CURRENT_TIMESTAMP  -- 创建时间，默认为当前时间
            )
        """)
        
        # 创建商品表，包含商品名称、描述、价格、库存、所属商家等字段
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tc_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,   -- 主键自增
                name TEXT NOT NULL,                    -- 商品名，不能为空
                description TEXT,                      -- 商品描述
                price REAL NOT NULL CHECK(price > 0),  -- 商品价格，必须大于0
                stock INTEGER NOT NULL CHECK(stock >= 0),  -- 库存，不能为负
                seller_id INTEGER NOT NULL,            -- 商家ID（外键）
                created_at TEXT DEFAULT CURRENT_TIMESTAMP, -- 创建时间
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP, -- 更新时间
                FOREIGN KEY (seller_id) REFERENCES tc_users(id) -- 关联商家
            )
        """)
        
        # 创建订单表，包含买家、商品、数量、总金额、下单时间等信息
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tc_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,   -- 主键自增
                buyer_id INTEGER NOT NULL,              -- 买家ID（外键）
                product_id INTEGER NOT NULL,            -- 商品ID（外键）
                quantity INTEGER NOT NULL CHECK(quantity > 0), -- 购买数量，必须大于0
                total_amount REAL NOT NULL,             -- 总金额
                order_time TEXT DEFAULT CURRENT_TIMESTAMP, -- 下单时间
                FOREIGN KEY (buyer_id) REFERENCES tc_users(id),    -- 关联买家
                FOREIGN KEY (product_id) REFERENCES tc_products(id) -- 关联商品
            )
        """)
        # 初始化示例数据
        cursor.execute("SELECT COUNT(*) FROM tc_users")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("""
                INSERT INTO tc_users (username, role, balance) VALUES (?, ?, ?)
            """, [
                ("京东自营旗舰店", "seller", 0),
                ("张三", "buyer", 10000.0),
                ("李四", "buyer", 5000.0),
            ])
            
            cursor.execute("SELECT id FROM tc_users WHERE username = '京东自营旗舰店'")
            seller_id = cursor.fetchone()[0]
            cursor.executemany("""
                INSERT INTO tc_products (name, description, price, stock, seller_id)
                VALUES (?, ?, ?, ?, ?)
            """, [
                ("iPhone手机", "苹果iPhone 15 Pro 256G 原色钛金属，官方正品", 7000.0, 49, seller_id),
                ("智能机械键盘", "智能机械键盘", 1000.0, 20, seller_id),
                ("索尼耳机", "Sony WH-1000XM5 无线降噪蓝牙耳机", 200.0, 80, seller_id),
            ])

