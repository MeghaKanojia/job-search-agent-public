from cryptography.fernet import Fernet

from pipeline.common import config as config_module
from pipeline.common.secrets import decrypt, encrypt


def test_decrypt_accepts_memoryview_like_a_raw_sql_bytea_read(monkeypatch):
    # A raw SQL (not ORM) BYTEA column comes back from psycopg2 as a memoryview,
    # not bytes. This crashed a real ingestion run reading a stored Gmail OAuth
    # token with "TypeError: token must be bytes or str".
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(config_module.config, "encryption_key", key)

    ciphertext = encrypt("some-oauth-token")
    as_memoryview = memoryview(ciphertext)

    assert decrypt(as_memoryview) == "some-oauth-token"


def test_decrypt_still_accepts_plain_bytes(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(config_module.config, "encryption_key", key)

    ciphertext = encrypt("some-oauth-token")

    assert decrypt(ciphertext) == "some-oauth-token"
