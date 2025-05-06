import os
import asyncpg
from cryptography.fernet import Fernet
from urllib.parse import urlparse, urlunparse


# 1) Control-plane pool (superuser to control-plane DB)
_control_pool: asyncpg.Pool | None = None
async def get_control_pool() -> asyncpg.Pool:
    global _control_pool
    if not _control_pool:
        _control_pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
    return _control_pool

# 2) Decrypt a DSN
_cipher = Fernet(os.getenv("FERNET_KEY"))  # generate one and store in .env
def decrypt_dsn(enc: str) -> str:
    return _cipher.decrypt(enc.encode()).decode()
