from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.database import get_db
from app import models, schemas, services
from app.deps import get_current_user

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _validate_payload(payload: schemas.TransactionBase, db: Session, user_id: int):
    account = db.query(models.Account).filter(
        models.Account.id == payload.account_id, models.Account.user_id == user_id
    ).first()
    if not account or not account.is_active:
        raise HTTPException(400, "Cuenta de origen inválida")

    if payload.kind == "transferencia":
        if not payload.to_account_id:
            raise HTTPException(400, "Una transferencia requiere cuenta destino")
        if payload.to_account_id == payload.account_id:
            raise HTTPException(400, "La cuenta origen y destino no pueden ser la misma")
        to_account = db.query(models.Account).filter(
            models.Account.id == payload.to_account_id, models.Account.user_id == user_id
        ).first()
        if not to_account or not to_account.is_active:
            raise HTTPException(400, "Cuenta destino inválida")
    elif payload.kind in {"ingreso", "gasto"}:
        if not payload.category_id:
            raise HTTPException(400, "Ingresos y gastos requieren categoría")
        cat = db.query(models.Category).filter(
            models.Category.id == payload.category_id, models.Category.user_id == user_id
        ).first()
        if not cat:
            raise HTTPException(400, "Categoría inválida")
        if cat.kind != payload.kind:
            raise HTTPException(400, f"La categoría no corresponde a un {payload.kind}")
    else:
        raise HTTPException(400, "kind debe ser ingreso, gasto o transferencia")


def _to_detail(txn: models.Transaction) -> schemas.TransactionDetailOut:
    return schemas.TransactionDetailOut(
        id=txn.id, date=txn.date, kind=txn.kind, amount=txn.amount,
        description=txn.description, account_id=txn.account_id,
        to_account_id=txn.to_account_id, category_id=txn.category_id,
        created_at=txn.created_at,
        account_name=txn.account.name if txn.account else None,
        to_account_name=txn.to_account.name if txn.to_account else None,
        category_name=txn.category.name if txn.category else None,
    )


@router.get("", response_model=List[schemas.TransactionDetailOut])
def list_transactions(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user),
    account_id: Optional[int] = None, category_id: Optional[int] = None, kind: Optional[str] = None,
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    limit: int = Query(200, le=2000),
):
    q = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id)
    if account_id:
        q = q.filter(
            (models.Transaction.account_id == account_id) | (models.Transaction.to_account_id == account_id)
        )
    if category_id:
        q = q.filter(models.Transaction.category_id == category_id)
    if kind:
        q = q.filter(models.Transaction.kind == kind)
    if date_from:
        q = q.filter(models.Transaction.date >= date_from)
    if date_to:
        q = q.filter(models.Transaction.date <= date_to)
    txns = q.order_by(models.Transaction.date.desc(), models.Transaction.id.desc()).limit(limit).all()
    return [_to_detail(t) for t in txns]


@router.post("", response_model=schemas.TransactionDetailOut)
def create_transaction(payload: schemas.TransactionCreate, db: Session = Depends(get_db),
                        current_user: models.User = Depends(get_current_user)):
    _validate_payload(payload, db, current_user.id)
    txn = models.Transaction(user_id=current_user.id, **payload.dict())
    db.add(txn)
    db.flush()
    services.apply_transaction_effect(db, txn)
    db.commit()
    db.refresh(txn)
    return _to_detail(txn)


@router.put("/{txn_id}", response_model=schemas.TransactionDetailOut)
def update_transaction(txn_id: int, payload: schemas.TransactionCreate, db: Session = Depends(get_db),
                        current_user: models.User = Depends(get_current_user)):
    txn = db.query(models.Transaction).filter(
        models.Transaction.id == txn_id, models.Transaction.user_id == current_user.id
    ).first()
    if not txn:
        raise HTTPException(404, "Movimiento no encontrado")
    _validate_payload(payload, db, current_user.id)
    services.apply_transaction_effect(db, txn, reverse=True)
    for field, value in payload.dict().items():
        setattr(txn, field, value)
    db.flush()
    services.apply_transaction_effect(db, txn)
    db.commit()
    db.refresh(txn)
    return _to_detail(txn)


@router.delete("/{txn_id}")
def delete_transaction(txn_id: int, db: Session = Depends(get_db),
                        current_user: models.User = Depends(get_current_user)):
    txn = db.query(models.Transaction).filter(
        models.Transaction.id == txn_id, models.Transaction.user_id == current_user.id
    ).first()
    if not txn:
        raise HTTPException(404, "Movimiento no encontrado")
    services.apply_transaction_effect(db, txn, reverse=True)
    db.delete(txn)
    db.commit()
    return {"detail": "Movimiento eliminado y saldos actualizados"}
