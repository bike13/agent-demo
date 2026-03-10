"""用户相关路由"""
from fastapi import APIRouter, HTTPException
from ..models import UserCreate, UserResponse
from ..crud import user_crud

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def get_users():
    """获取所有用户"""
    return user_crud.get_all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    """获取用户详情"""
    user = user_crud.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.post("", response_model=UserResponse)
def create_user(user: UserCreate):
    """创建用户"""
    try:
        user_id = user_crud.create(user.model_dump())
        return user_crud.get_by_id(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

