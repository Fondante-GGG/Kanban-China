class DomainException(Exception):
    """Base domain exception"""
    def __init__(self, message: str = "Domain error occurred"):
        self.message = message
        super().__init__(self.message)



class EntityNotFoundException(DomainException):
    """Raised when an entity is not found"""
    def __init__(self, entity_name: str, entity_id: any):
        super().__init__(f"{entity_name} with id {entity_id} was not found.")
        self.entity_name = entity_name
        self.entity_id = entity_id


class PermissionDeniedException(DomainException):
    """Raised when an operation is forbidden for the current role/user"""
    def __init__(self, message: str = "Permission denied for this operation."):
        super().__init__(message)


class ValidationException(DomainException):
    """Raised when domain invariants or input validation fail"""
    def __init__(self, message: str = "Validation error."):
        super().__init__(message)


class AuthenticationFailedException(DomainException):
    """Raised on invalid credentials or inactive account"""
    def __init__(self, message: str = "Invalid credentials or inactive account."):
        super().__init__(message)
