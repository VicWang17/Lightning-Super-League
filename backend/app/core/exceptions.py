"""
Custom exceptions for the application
"""


class AppException(Exception):
    """Base application exception"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(AppException):
    """Resource not found"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ValidationException(AppException):
    """Validation error"""
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status_code=400)


class AuthenticationException(AppException):
    """Authentication error"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class AuthorizationException(AppException):
    """Authorization error"""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, status_code=403)
