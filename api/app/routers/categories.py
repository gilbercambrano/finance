from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app import models, schemas
from app.deps import get_current_user

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=List[schemas.CategoryOut])
def list_categories(kind: Optional[str] = None, db: Session = Depends(get_db),
                     current_user: models.User = Depends(get_current_user)):
    q = db.query(models.Category).filter(
        models.Category.user_id == current_user.id, models.Category.is_active == True  # noqa: E712
    )
    if kind:
        q = q.filter(models.Category.kind == kind)
    return q.order_by(models.Category.kind, models.Category.group, models.Category.name).all()


@router.post("", response_model=schemas.CategoryOut)
def create_category(payload: schemas.CategoryCreate, db: Session = Depends(get_db),
                     current_user: models.User = Depends(get_current_user)):
    if payload.kind not in {"ingreso", "gasto"}:
        raise HTTPException(400, "kind debe ser 'ingreso' o 'gasto'")
    cat = models.Category(user_id=current_user.id, **payload.dict())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/{category_id}")
def deactivate_category(category_id: int, db: Session = Depends(get_db),
                         current_user: models.User = Depends(get_current_user)):
    cat = db.query(models.Category).filter(
        models.Category.id == category_id, models.Category.user_id == current_user.id
    ).first()
    if not cat:
        raise HTTPException(404, "Categoría no encontrada")
    cat.is_active = False
    db.commit()
    return {"detail": "Categoría desactivada"}
