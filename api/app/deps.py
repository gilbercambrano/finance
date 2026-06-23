from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.security import decode_access_token, COOKIE_NAME


def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="No has iniciado sesión")
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    user = db.query(models.User).get(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")
    return user
