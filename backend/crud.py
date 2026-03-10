"""共用的CRUD操作基类"""
from typing import TypeVar, Generic, List, Optional, Dict, Any
from .database import get_db
import sqlite3

T = TypeVar('T')


class CRUDBase(Generic[T]):
    """通用CRUD基类"""
    
    def __init__(self, table_name: str, id_field: str = "id"):
        self.table_name = table_name
        self.id_field = id_field
    
    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """将数据库行转换为字典"""
        return dict(row)
    
    def get_all(self) -> List[dict]:
        """获取所有记录"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {self.table_name}")
            return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def get_by_id(self, id: int) -> Optional[dict]:
        """根据ID获取记录"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE {self.id_field} = ?", (id,))
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None
    
    def create(self, data: dict) -> int:
        """创建记录，返回ID"""
        fields = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT INTO {self.table_name} ({fields}) VALUES ({placeholders})",
                tuple(data.values())
            )
            return cursor.lastrowid
    
    def update(self, id: int, data: dict) -> bool:
        """更新记录"""
        if not data:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in data.keys())
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE {self.table_name} SET {set_clause} WHERE {self.id_field} = ?",
                tuple(data.values()) + (id,)
            )
            return cursor.rowcount > 0
    
    def delete(self, id: int) -> bool:
        """删除记录"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {self.table_name} WHERE {self.id_field} = ?", (id,))
            return cursor.rowcount > 0
    
    def filter(self, **kwargs) -> List[dict]:
        """根据条件筛选记录"""
        if not kwargs:
            return self.get_all()
        conditions = " AND ".join(f"{k} = ?" for k in kwargs.keys())
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE {conditions}", tuple(kwargs.values()))
            return [self._row_to_dict(row) for row in cursor.fetchall()]


# 实例化各个表的CRUD对象
user_crud = CRUDBase("tc_users")
product_crud = CRUDBase("tc_products")
order_crud = CRUDBase("tc_orders")

