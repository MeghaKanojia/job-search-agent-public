from cryptography.fernet import Fernet

from app.core import config as config_module
from app.core.security import decrypt, encrypt


def test_decrypt_accepts_memoryview_like_a_raw_sql_bytea_read(monkeypatch):
    # A raw SQL (not ORM) BYTEA column comes back from psycopg2 as a memoryview,
    # not bytes. The pipeline's identical copy of this code crashed a real
    # ingestion run reading a stored Gmail OAuth token this exact way -- fixing
    # here too since this backend copy will hit the same wall reading
    # oauth_tokens/credentials.
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(config_module.settings, "encryption_key", key)

    ciphertext = encrypt("some-secret")
    as_memoryview = memoryview(ciphertext)

    assert decrypt(as_memoryview) == "some-secret"


def test_decrypt_still_accepts_plain_bytes(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(config_module.settings, "encryption_key", key)

    ciphertext = encrypt("some-secret")

    assert decrypt(ciphertext) == "some-secret"
