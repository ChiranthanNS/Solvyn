import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests

from app.database import get_db
from app import crud, schemas
from app.auth import create_access_token

router = APIRouter()

GOOGLE_CLIENT_ID = "138791352054-srdkgo2h3sm0i9irl7a2o2q99avkc9b5.apps.googleusercontent.com"


class GoogleAuthRequest(BaseModel):
    id_token: str


class GoogleAccessTokenRequest(BaseModel):
    access_token: str


def _get_or_create_user(db: Session, email: str, name: str):
    """Helper: look up user by email, create if not found."""
    if not email:
        raise HTTPException(status_code=400, detail="Email not found in Google profile")
    user = crud.get_user_by_email(db, email)
    if not user:
        user = crud.create_user(
            db,
            schemas.UserCreate(name=name, email=email, password="google_oauth"),
        )
    token = create_access_token({"user_id": user.id})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/google")
def google_auth(data: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Verify a Google ID token (preferred path for native / non-web platforms)."""
    try:
        info = id_token.verify_oauth2_token(
            data.id_token,
            requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google ID token: {e}")

    return _get_or_create_user(db, info.get("email"), info.get("name", "User"))


@router.post("/google-token")
async def google_auth_access_token(data: GoogleAccessTokenRequest, db: Session = Depends(get_db)):
    """
    Verify a Google OAuth2 access token via Google's userinfo endpoint.
    This is the fallback used by Flutter Web when idToken is unavailable.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {data.access_token}"},
            )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not reach Google API: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid Google access token")

    info = resp.json()
    email = info.get("email")
    name = info.get("name", info.get("given_name", "User"))

    return _get_or_create_user(db, email, name)
