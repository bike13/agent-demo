"""订单相关路由"""
from fastapi import APIRouter, HTTPException
from ..models import OrderCreate, OrderResponse
from ..crud import order_crud
from ..services import order_service

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("", response_model=list[OrderResponse])
def get_orders(buyer_id: int = None):
    """获取订单列表"""
    if buyer_id:
        return order_crud.filter(buyer_id=buyer_id)
    return order_crud.get_all()


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int):
    """获取订单详情"""
    order = order_crud.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order


@router.post("", response_model=OrderResponse)
def create_order(order: OrderCreate):
    """创建订单"""
    result = order_service.create_order(order)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return order_crud.get_by_id(result["order_id"])

