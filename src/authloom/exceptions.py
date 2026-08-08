from enum import StrEnum


class UserAlreadyExistsException(Exception):
    pass


class InvalidCredentialsException(Exception):
    pass


class InvalidPasswordResetTokenException(Exception):
    pass


class SessionCreationException(Exception):
    pass


class PasswordPolicyCode(StrEnum):
    TOO_SHORT = "password_too_short"
    TOO_LONG = "password_too_long"


class PasswordPolicyException(Exception):
    def __init__(self, code: PasswordPolicyCode, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)
