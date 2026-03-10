"""商品相关路由"""
from fastapi import APIRouter, HTTPException
from ..models import ProductCreate, ProductUpdate, ProductResponse
from ..crud import product_crud

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[ProductResponse])
def get_products():
    """获取所有商品"""
    return product_crud.get_all()


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int):
    """获取商品详情"""
    product = product_crud.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.post("", response_model=ProductResponse)
def create_product(product: ProductCreate):
    """创建商品"""
    try:
        product_id = product_crud.create(product.model_dump())
        return product_crud.get_by_id(product_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product: ProductUpdate):
    """更新商品"""
    product_data = product.model_dump(exclude_unset=True)
    if not product_data:
        raise HTTPException(status_code=400, detail="没有要更新的字段")
    
    if not product_crud.update(product_id, product_data):
        raise HTTPException(status_code=404, detail="商品不存在")
    
    # 更新updated_at
    from ..database import get_db
    with get_db() as conn:
        conn.execute("UPDATE tc_products SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (product_id,))
    
    return product_crud.get_by_id(product_id)


@router.delete("/{product_id}")
def delete_product(product_id: int):
    """删除商品"""
    if not product_crud.delete(product_id):
        raise HTTPException(status_code=404, detail="商品不存在")
    return {"message": "删除成功"}

