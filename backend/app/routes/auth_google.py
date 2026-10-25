import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field
from google.oauth2 import id_token
from google.auth.transport import requests

from app.database import get_db
from app import crud
from app.auth import create_access_token
from config import GOOGLE_CLIENT_ID

router = APIRouter()

class GoogleAuthRequest(BaseModel):
    id_token: str = Field(min_length=1, max_length=8192)
    nonce: str | None = Field(default=None, min_length=16, max_length=128)


class GoogleAccessTokenRequest(BaseModel):
    access_token: str = Field(min_length=1, max_length=8192)


def _get_or_create_user(db: Session, email: str, name: str):
    """Helper: look up user by email, create if not found."""
    if not email:
        raise HTTPException(status_code=400, detail="Email not found in Google profile")
    user = crud.get_user_by_email(db, email)
    if not user:
        try:
            user = crud.create_google_user(db, email)
        except IntegrityError as exc:
            db.rollback()
            user = crud.get_user_by_email(db, email.strip().lower())
            if not user:
                raise
    token = create_access_token({"user_id": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user.email,
    }


@router.post("/google")
def google_auth(data: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Verify a Google ID token (preferred path for native / non-web platforms)."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured.")
    try:
        info = id_token.verify_oauth2_token(
            data.id_token,
            requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid Google ID token.") from exc

    if info.get("email_verified") is not True:
        raise HTTPException(status_code=401, detail="Google must verify the account email.")
    if data.nonce is not None and info.get("nonce") != data.nonce:
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified.")

    return _get_or_create_user(db, info.get("email"), info.get("name", "User"))


@router.post("/google-token")
async def google_auth_access_token(data: GoogleAccessTokenRequest, db: Session = Depends(get_db)):
    """
    Verify a Google OAuth2 access token via Google's userinfo endpoint.
    This is the fallback used by Flutter Web when idToken is unavailable.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured.")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {data.access_token}"},
            )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not reach Google sign-in service.") from exc

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google access token")

    info = resp.json()
    if info.get("email_verified") is not True:
        raise HTTPException(status_code=401, detail="Google must verify the account email.")
    email = info.get("email")
    name = info.get("name", info.get("given_name", "User"))
    if not isinstance(email, str) or not email.strip():
        raise HTTPException(status_code=401, detail="Google did not return a verified email.")

    return _get_or_create_user(db, email, name)


@router.get("/google/config")
def google_auth_config():
    """Expose only the public OAuth client ID needed by the browser SDK."""
    return {"client_id": GOOGLE_CLIENT_ID or None}
