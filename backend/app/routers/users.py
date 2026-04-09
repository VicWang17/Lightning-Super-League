"""
User management API routes
"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from app.schemas import (
    ResponseSchema,
    PaginatedResponse,
    PaginationParams,
    UserResponse,
    UserUpdate,
    ErrorResponse,
)

router = APIRouter(prefix="/users", tags=["用户"])


@router.get(
    "/",
    response_model=ResponseSchema[PaginatedResponse[UserResponse]],
    summary="获取用户列表",
    description="获取所有用户的分页列表",
)
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
):
    """
    获取用户列表（管理员权限）
    
    - **page**: 页码，从1开始
    - **page_size**: 每页数量
    - **search**: 搜索关键词（用户名/邮箱）
    """
    # TODO: 实现用户列表查询
    return ResponseSchema(
        success=True,
        data=PaginatedResponse.create(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
        ),
    )


@router.get(
    "/{user_id}",
    response_model=ResponseSchema[UserResponse],
    summary="获取用户详情",
    description="根据ID获取用户详细信息",
    responses={
        200: {"description": "获取成功"},
        404: {"model": ErrorResponse, "description": "用户不存在"},
    },
)
async def get_user(user_id: int):
    """
    获取指定用户的详细信息
    
    - **user_id**: 用户ID
    """
    # TODO: 实现用户详情查询
    return ResponseSchema(
        success=True,
        data=UserResponse(
            id=user_id,
            username="manager",
            email="manager@example.com",
            created_at="2024-01-01T00:00:00",
        ),
    )


@router.put(
    "/{user_id}",
    response_model=ResponseSchema[UserResponse],
    summary="更新用户信息",
    description="更新指定用户的信息",
)
async def update_user(user_id: int, user_data: UserUpdate):
    """
    更新用户信息
    
    - **user_id**: 用户ID
    - **nickname**: 昵称
    - **avatar_url**: 头像URL
    """
    # TODO: 实现用户更新逻辑
    return ResponseSchema(
        success=True,
        message="更新成功",
        data=UserResponse(
            id=user_id,
            username="manager",
            email="manager@example.com",
            nickname=user_data.nickname,
            created_at="2024-01-01T00:00:00",
        ),
    )


@router.delete(
    "/{user_id}",
    response_model=ResponseSchema,
    summary="删除用户",
    description="删除指定用户（软删除）",
)
async def delete_user(user_id: int):
    """
    删除用户
    
    - **user_id**: 用户ID
    """
    # TODO: 实现用户删除逻辑
    return ResponseSchema(success=True, message="删除成功")
