from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, seed_data
from app.security import hash_password, verify_password, create_access_token, COOKIE_NAME
from app.deps import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_auth_cookie(response: Response, user_id: int):
    token = create_access_token(user_id)
    response.set_cookie(
        key=COOKIE_NAME, value=token, httponly=True,
        samesite="lax", secure=settings.cookie_secure,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


@router.post("/register", response_model=schemas.UserOut)
def register(payload: schemas.UserRegister, response: Response, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(400, "Ya existe una cuenta con ese correo")
    user = models.User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    seed_data.run_for_user(db, user.id)

    _set_auth_cookie(response, user.id)
    return user


@router.post("/login", response_model=schemas.UserOut)
def login(payload: schemas.UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Correo o contraseña incorrectos")
    if not user.is_active:
        raise HTTPException(403, "Cuenta deshabilitada")
    _set_auth_cookie(response, user.id)
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"detail": "Sesión cerrada"}


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
