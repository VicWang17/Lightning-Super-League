"""
Custom middleware for request/response logging
"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import request_logger, get_logger

logger = get_logger("app")


class LoggingMiddleware(BaseHTTPMiddleware):
    """中间件：记录所有 HTTP 请求和响应"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # 跳过静态文件和健康检查
        path = request.url.path
        if path in ["/", "/health", "/docs", "/redoc", "/openapi.json"] or \
           path.startswith("/static/") or path.startswith("/assets/"):
            return await call_next(request)
        
        # 记录请求开始
        start_time = time.time()
        method = request.method
        
        # 尝试获取用户信息
        user_id = None
        try:
            from app.core.security import decode_token
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                payload = decode_token(token)
                if payload:
                    user_id = payload.get("sub")
        except Exception:
            pass
        
        # 记录请求
        request_logger.log_request(method, path, user_id)
        
        # 处理请求
        try:
            response = await call_next(request)
            
            # 计算处理时间
            duration_ms = (time.time() - start_time) * 1000
            
            # 记录响应
            request_logger.log_response(
                method, path, response.status_code, duration_ms
            )
            
            return response
            
        except Exception as e:
            # 记录错误
            duration_ms = (time.time() - start_time) * 1000
            request_logger.log_error(method, path, e)
            raise


class ProcessTimeHeader(BaseHTTPMiddleware):
    """中间件：添加处理时间响应头"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
        return response
