"""数据模型定义"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str
    role: str = Field(..., pattern="^(seller|buyer)$")
    balance: float = Field(default=0, ge=0)


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    created_at: str
    
    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    seller_id: int


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)


class ProductResponse(ProductBase):
    id: int
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    buyer_id: int
    product_id: int
    quantity: int = Field(..., gt=0)


class OrderResponse(BaseModel):
    id: int
    buyer_id: int
    product_id: int
    quantity: int
    total_amount: float
    order_time: str
    
    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    user_id: int


class ChatResponse(BaseModel):
    reply: str
    action_result: Optional[dict] = None


class IntentRecognition(BaseModel):
    """意图识别结果"""
    intent: str = Field(description="意图类型：purchase(购买), confirm(确认), cancel(取消), query(查询), other(其他)")
    product_id: Optional[int] = Field(None, description="商品ID，如果是购买意图")
    quantity: Optional[int] = Field(None, description="购买数量，如果是购买意图")
    confidence: float = Field(0.0, description="意图识别置信度，0-1之间")

