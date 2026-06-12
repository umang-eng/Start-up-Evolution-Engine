class BaseBusinessException(Exception):
    """Base exception class for all structured business logic errors."""
    
    def __init__(self, message: str, code: str = "BUSINESS_ERROR", status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class EntityNotFoundError(BaseBusinessException):
    """Exception raised when database resources cannot be found."""
    def __init__(self, message: str = "Resource not found", code: str = "ENTITY_NOT_FOUND") -> None:
        super().__init__(message=message, code=code, status_code=404)


class AuthorizationError(BaseBusinessException):
    """Exception raised when scope validations fail."""
    def __init__(self, message: str = "Not authorized to perform this operation", code: str = "AUTHORIZATION_DENIED") -> None:
        super().__init__(message=message, code=code, status_code=403)


class AuthenticationError(BaseBusinessException):
    """Exception raised when credential checks fail."""
    def __init__(self, message: str = "Invalid credentials or session expired", code: str = "AUTHENTICATION_FAILED") -> None:
        super().__init__(message=message, code=code, status_code=401)


class ConflictError(BaseBusinessException):
    """Exception raised when logical resource conflicts occur."""
    def __init__(self, message: str = "Conflict detected with current state", code: str = "CONFLICT_DETECTED") -> None:
        super().__init__(message=message, code=code, status_code=409)


class GenerationLimitError(BaseBusinessException):
    """Exception raised when users exceed execution limits."""
    def __init__(self, message: str = "Generation rate limit exceeded", code: str = "LIMIT_EXCEEDED") -> None:
        super().__init__(message=message, code=code, status_code=429)
