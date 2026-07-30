from authloom.service import generate_session_token, hash_session_token


def test_generate_session_token_returns_non_empty_raw_token():
    token_raw, token_hash = generate_session_token()

    assert isinstance(token_raw, str)
    assert token_raw
    assert token_hash


def test_generate_session_token_returns_different_raw_tokens():
    first_token_raw, _ = generate_session_token()
    second_token_raw, _ = generate_session_token()

    assert first_token_raw != second_token_raw


def test_hash_session_token_is_deterministic_for_same_token():
    raw_value = "authloom-session-token"

    first_hash = hash_session_token(raw_value)
    second_hash = hash_session_token(raw_value)

    assert first_hash == second_hash


def test_hash_session_token_differs_for_different_tokens():
    first_hash = hash_session_token("authloom-session-token")
    second_hash = hash_session_token("different-authloom-session-token")

    assert first_hash != second_hash


def test_generate_session_token_hash_is_not_raw_token():
    token_raw, token_hash = generate_session_token()

    assert token_hash != token_raw
