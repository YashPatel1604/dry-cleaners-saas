from tenants.utils import generate_invite_token, hash_invite_token, verify_invite_token


def test_invite_token_utilities():
    token = generate_invite_token()
    assert isinstance(token, str)
    assert len(token) > 10

    token_hash = hash_invite_token(token)
    assert verify_invite_token(token, token_hash) is True
    assert verify_invite_token("wrong-token", token_hash) is False
