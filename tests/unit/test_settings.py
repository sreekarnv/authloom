import pytest
from pydantic import ValidationError

from authloom import AuthLoomCookieSessionConfig, AuthLoomPasswordConfig


def test_cookie_session_allows_samesite_none_when_secure_true():
    session_config = AuthLoomCookieSessionConfig(
        secure=True,
        samesite="none",
    )

    assert session_config.samesite == "none" and session_config.secure is True


def test_cookie_session_rejects_samesite_none_when_secure_false():
    with pytest.raises(ValidationError):
        AuthLoomCookieSessionConfig(
            secure=False,
            samesite="none",
        )


def test_cookie_session_allows_path_starting_with_slash():
    session_config = AuthLoomCookieSessionConfig(path="/hello-world")

    assert session_config.path == "/hello-world"


def test_cookie_session_rejects_path_without_leading_slash():
    with pytest.raises(ValidationError):
        AuthLoomCookieSessionConfig(path="invalid-hello-world")


def test_password_rejects_min_length_below_15():
    with pytest.raises(ValidationError):
        AuthLoomPasswordConfig(min_length=14)


def test_password_rejects_max_length_below_64():
    with pytest.raises(ValidationError):
        AuthLoomPasswordConfig(max_length=63)


def test_password_rejects_max_length_above_128():
    with pytest.raises(ValidationError):
        AuthLoomPasswordConfig(max_length=129)


def test_password_rejects_min_length_greater_than_max_length():
    with pytest.raises(ValidationError):
        AuthLoomPasswordConfig(
            max_length=40,
            min_length=50,
        )


@pytest.mark.parametrize("max_length", [64, 128])
def test_password_accepts_boundary_lengths(max_length: int):
    config = AuthLoomPasswordConfig(
        min_length=15,
        max_length=max_length,
    )

    assert config.min_length == 15
    assert config.max_length == max_length
