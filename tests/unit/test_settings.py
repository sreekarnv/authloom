import pytest
from pydantic import ValidationError

from authloom.settings import AuthLoomCookieSessionConfig


def test_cookie_session_allows_samesite_none_when_secure_true():
    session_config = AuthLoomCookieSessionConfig(
        secure=True,
        samesite="none",
    )

    if session_config.samesite != "none" or session_config.secure is not True:
        raise AssertionError


def test_cookie_session_rejects_samesite_none_when_secure_false():
    with pytest.raises(ValidationError):
        AuthLoomCookieSessionConfig(
            secure=False,
            samesite="none",
        )
