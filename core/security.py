# from datetime import datetime, timedelta, timezone
# from typing import Any

# import jwt
# from passlib.context import CryptContext

# from core.config import settings

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ALGORITHM = "HS256"


# def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
#     expire = datetime.now(timezone.utc) + expires_delta
#     to_encode = {"exp": expire, "sub": str(subject)}
#     encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt


# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     return pwd_context.verify(plain_password, hashed_password)


# def get_password_hash(password: str) -> str:
#     return pwd_context.hash(password)

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from core.config import settings

# -----------------------------
# Use Argon2 as the password hashing algorithm
# -----------------------------
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

ALGORITHM = "HS256"

# -----------------------------
# JWT Token creation
# -----------------------------
def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# -----------------------------
# Password hashing & verification
# -----------------------------
def get_password_hash(password: str) -> str:
    """
    Hashes a plain password using Argon2
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against the Argon2 hash
    """
    return pwd_context.verify(plain_password, hashed_password)
