"""
Structured logging configuration for the application
"""
import logging
import sys
from datetime import datetime
from typing import Any

# 日志格式
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 颜色代码（用于终端输出）
COLORS = {
    "DEBUG": "\033[36m",      # 青色
    "INFO": "\033[32m",       # 绿色
    "WARNING": "\033[33m",    # 黄色
    "ERROR": "\033[31m",      # 红色
    "CRITICAL": "\033[35m",   # 紫色
    "RESET": "\033[0m",       # 重置
}


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        # 添加颜色
        levelname = record.levelname
        if levelname in COLORS:
            record.levelname = f"{COLORS[levelname]}{levelname}{COLORS['RESET']}"
        
        # 添加图标
        icons = {
            "DEBUG": "🐛",
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "🔥",
        }
        record.icon = icons.get(levelname.strip(COLORS["DEBUG"]), "ℹ️")
        
        return super().format(record)


def setup_logging(debug: bool = False) -> None:
    """配置应用日志"""
    level = logging.DEBUG if debug else logging.INFO
    
    # 配置根日志器
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 设置第三方库的日志级别
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    
    # 获取应用日志器
    logger = logging.getLogger("app")
    logger.setLevel(level)
    
    # 应用日志格式
    formatter = ColoredFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    for handler in logger.handlers:
        handler.setFormatter(formatter)
    
    return logger


def get_logger(name: str = "app") -> logging.Logger:
    """获取日志器实例"""
    return logging.getLogger(name)


# 请求日志记录器
class RequestLogger:
    """记录 HTTP 请求和响应"""
    
    def __init__(self):
        self.logger = get_logger("app.request")
    
    def log_request(
        self,
        method: str,
        path: str,
        user_id: str | None = None,
        **kwargs: Any
    ) -> None:
        """记录请求信息"""
        user = f" user={user_id}" if user_id else ""
        self.logger.info(f"→ {method} {path}{user}")
    
    def log_response(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        **kwargs: Any
    ) -> None:
        """记录响应信息"""
        # 根据状态码选择图标
        if status_code < 400:
            icon = "✓"
        elif status_code < 500:
            icon = "⚠"
        else:
            icon = "✗"
        
        self.logger.info(
            f"← {method} {path} {icon} {status_code} ({duration_ms:.2f}ms)"
        )
    
    def log_error(
        self,
        method: str,
        path: str,
        error: Exception,
        **kwargs: Any
    ) -> None:
        """记录错误信息"""
        self.logger.error(f"✗ {method} {path} | Error: {str(error)}")


# 全局请求日志记录器
request_logger = RequestLogger()
