from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app import schemas, crud
from app.database import get_db
from app.auth import create_access_token

router = APIRouter()

@router.post("/signup", response_model=schemas.UserResponse)
@router.post("/register", response_model=schemas.UserResponse, include_in_schema=False)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    try:
        return crud.create_user(db, user)
    except IntegrityError as exc:
        db.rollback()
        if crud.get_user_by_email(db, user.email):
            raise HTTPException(status_code=400, detail="Email already registered") from exc
        raise

@router.post("/login", response_model=schemas.LoginResponse)
def login(req: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"user_id": user.id})
    return {"access_token": token}
