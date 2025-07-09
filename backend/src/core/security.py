import base64
import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: str | Any, expires_delta: timedelta | None = None
) -> str:
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt: str = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def create_refresh_token(
    subject: str | Any, expires_delta: timedelta | None = None
) -> str:
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt: str = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    result: bool = pwd_context.verify(plain_password, hashed_password)
    return result


def get_password_hash(password: str) -> str:
    hashed: str = pwd_context.hash(password)
    return hashed


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError as e:
        raise ValueError("Invalid token") from e


class APIKeyEncryption:
    def __init__(self) -> None:
        # Derive a consistent encryption key from the secret key
        # This ensures encrypted API keys can be decrypted after service restarts
        key_material = hashlib.pbkdf2_hmac(
            "sha256",
            settings.secret_key.encode(),
            b"api_key_encryption_salt",  # Static salt for consistency
            100000,  # Iterations
        )
        # Fernet requires a 32-byte base64-encoded key
        fernet_key = base64.urlsafe_b64encode(key_material[:32])
        self.cipher_suite = Fernet(fernet_key)

    def encrypt_key(self, api_key: str) -> str:
        return self.cipher_suite.encrypt(api_key.encode()).decode()

    def decrypt_key(self, encrypted_key: str) -> str:
        return self.cipher_suite.decrypt(encrypted_key.encode()).decode()


api_key_encryption = APIKeyEncryption()
