"""
Authentication API routes
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    ResponseSchema,
    UserCreate,
    UserResponse,
    TokenResponse,
    UserWithToken,
    ErrorResponse,
)
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
)
from app.dependencies import get_db
from app.repositories.user import UserRepository

router = APIRouter(prefix="/auth", tags=["认证"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post(
    "/register",
    response_model=ResponseSchema[UserResponse],
    summary="用户注册",
    description="注册新用户账号",
    responses={
        201: {"description": "注册成功"},
        400: {"model": ErrorResponse, "description": "注册失败"},
    },
)
async def register(user_data: UserCreate):
    """
    注册新用户
    
    - **username**: 用户名 (3-50字符)
    - **email**: 邮箱地址
    - **password**: 密码 (至少8位)
    - **nickname**: 昵称 (可选)
    """
    # 注册功能暂未实现
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="接口未实现"
    )


@router.post(
    "/login",
    response_model=ResponseSchema[UserWithToken],
    summary="用户登录",
    description="使用邮箱和密码登录",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录
    
    - **username**: 邮箱地址
    - **password**: 密码
    """
    user_repo = UserRepository(db)
    
    # 查找用户
    user = await user_repo.get_by_email(form_data.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证密码
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查用户状态
    if user.status.value == "banned":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被封禁",
        )
    
    if user.status.value == "inactive":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号未激活",
        )
    
    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    await db.flush()
    
    # 生成 token
    token_data = {"sub": str(user.id), "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return ResponseSchema(
        success=True,
        message="登录成功",
        data=UserWithToken(
            id=user.id,
            username=user.username,
            email=user.email,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            level=user.level,
            experience=user.experience,
            is_active=user.status.value == "active",
            is_verified=user.is_verified,
            created_at=user.created_at,
            last_login=user.last_login_at,
            token=TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=1800,  # 30分钟
            ),
        ),
    )


@router.post(
    "/refresh",
    response_model=ResponseSchema[TokenResponse],
    summary="刷新令牌",
    description="使用刷新令牌获取新的访问令牌",
)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    刷新访问令牌
    
    - **refresh_token**: 刷新令牌
    """
    from app.core.security import decode_token
    
    # 验证 refresh token
    payload = decode_token(refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查 token 类型
    token_type = payload.get("type")
    if token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌类型",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 获取用户 ID
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌内容",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 查询用户是否存在
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(int(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    
    # 检查用户状态
    if user.status.value == "banned":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被封禁",
        )
    
    # 生成新的 token
    token_data = {"sub": str(user.id), "email": user.email}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    
    return ResponseSchema(
        success=True,
        message="令牌刷新成功",
        data=TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=1800,  # 30分钟
        ),
    )


@router.post(
    "/logout",
    response_model=ResponseSchema,
    summary="用户登出",
    description="注销当前用户的登录状态",
)
async def logout(token: str = Depends(oauth2_scheme)):
    """
    用户登出
    """
    # TODO: 实现登出逻辑（将token加入黑名单）
    return ResponseSchema(success=True, message="登出成功")


@router.get(
    "/me",
    response_model=ResponseSchema[UserResponse],
    summary="获取当前用户",
    description="获取当前登录用户的信息",
)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前登录用户信息
    """
    from app.core.security import decode_token
    
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(int(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    
    return ResponseSchema(
        success=True,
        data=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            level=user.level,
            experience=user.experience,
            is_active=user.status.value == "active",
            is_verified=user.is_verified,
            created_at=user.created_at,
            last_login=user.last_login_at,
        ),
    )
