"""Encrypt-at-rest helpers for anything stored in `credentials` / `oauth_tokens`.

The encryption key lives only in the ENCRYPTION_KEY env var (never in the DB,
never committed). Generate one with `Fernet.generate_key()` and store it as a
Render/GitHub Actions secret. Losing the key means every stored secret becomes
unrecoverable, that's intentional; it must not be recoverable from the DB alone.
"""

from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet() -> Fernet:
    if not settings.encryption_key:
        raise RuntimeError(
            "ENCRYPTION_KEY is not set. Generate one with "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"` "
            "and set it as an environment variable/secret."
        )
    return Fernet(settings.encryption_key.encode())


def encrypt(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode())


def decrypt(ciphertext: bytes) -> str:
    # A raw SQL (not ORM) BYTEA read comes back from psycopg2 as a memoryview, not
    # bytes -- Fernet.decrypt() rejects that outright. bytes() coerces uniformly.
    # (Confirmed via pipeline/common/secrets.py hitting this exact TypeError in
    # production reading a stored Gmail OAuth token; fixing here too since this
    # backend copy will hit the same wall once it reads oauth_tokens/credentials.)
    return _fernet().decrypt(bytes(ciphertext)).decode()