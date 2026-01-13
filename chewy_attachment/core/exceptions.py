"""Custom exceptions for ChewyAttachment"""


class ChewyAttachmentException(Exception):
    """Base exception for ChewyAttachment"""

    pass


class FileNotFoundException(ChewyAttachmentException):
    """Raised when a file is not found"""

    def __init__(self, file_id: str):
        self.file_id = file_id
        super().__init__(f"File not found: {file_id}")


class PermissionDeniedException(ChewyAttachmentException):
    """Raised when permission is denied"""

    def __init__(self, action: str, file_id: str):
        self.action = action
        self.file_id = file_id
        super().__init__(f"Permission denied: cannot {action} file {file_id}")


class StorageException(ChewyAttachmentException):
    """Raised when storage operation fails"""

    def __init__(self, message: str):
        super().__init__(f"Storage error: {message}")


class InvalidFileException(ChewyAttachmentException):
    """Raised when file is invalid"""

    def __init__(self, message: str):
        super().__init__(f"Invalid file: {message}")
