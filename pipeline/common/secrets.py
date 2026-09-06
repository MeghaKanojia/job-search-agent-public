"""Same Fernet scheme as backend/app/core/security.py, duplicated here because the
pipeline is a separately-deployed process (GitHub Actions runner) that doesn't
import the backend package. Both must be pointed at the same ENCRYPTION_KEY secret.
"""

from cryptography.fernet import Fernet

from pipeline.common.config import config


def _fernet() -> Fernet:
    if not config.encryption_key:
        raise RuntimeError("ENCRYPTION_KEY env var is not set")
    return Fernet(config.encryption_key.encode())


def encrypt(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode())


def decrypt(ciphertext: bytes) -> str:
    # psycopg2 returns a raw SQL (not ORM) BYTEA column as a memoryview, not bytes --
    # Fernet.decrypt() strictly requires bytes/str and rejects memoryview outright
    # (observed in practice: "TypeError: token must be bytes or str" reading a stored
    # Gmail OAuth token). bytes() coerces memoryview/bytearray/bytes uniformly.
    return _fernet().decrypt(bytes(ciphertext)).decode()
