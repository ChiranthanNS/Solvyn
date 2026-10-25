from datetime import datetime, timedelta
import hashlib
import os

from jose import jwt, JWTError
import bcrypt
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("SESSION_SECRET") or os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7
PASSWORD_HASH_PREFIX = "bcrypt-sha256$"

# ==============================
# PASSWORD UTILS
# ==============================
def hash_password(password: str) -> str:
    # Pre-hash with SHA-256 so bcrypt's 72-byte input limit cannot truncate
    # long passwords. bcrypt still provides the salted, adaptive password KDF.
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    encoded = bcrypt.hashpw(digest, bcrypt.gensalt(rounds=12)).decode("ascii")
    return f"{PASSWORD_HASH_PREFIX}{encoded}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    raw_password = plain_password.encode("utf-8")
    try:
        if hashed_password.startswith(PASSWORD_HASH_PREFIX):
            digest = hashlib.sha256(raw_password).digest()
            encoded_hash = hashed_password.removeprefix(PASSWORD_HASH_PREFIX).encode("ascii")
            return bcrypt.checkpw(digest, encoded_hash)
        if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
            # Existing imported accounts used Passlib's bcrypt scheme, which
            # truncated inputs at bcrypt's historical 72-byte limit.
            return bcrypt.checkpw(raw_password[:72], hashed_password.encode("ascii"))
    except (ValueError, TypeError, UnicodeError):
        return False
    return False

# ==============================
# JWT TOKEN UTILS
# ==============================
def create_access_token(data: dict):
    if not SECRET_KEY:
        raise RuntimeError("SESSION_SECRET must be configured before issuing access tokens.")
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    if not SECRET_KEY:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
