from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.deps import get_current_user

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

VALID_TYPES = {"debito", "ahorro", "credito", "inversion", "efectivo", "prestamo", "prestamo_recibido"}
DEBT_TYPES = {"credito", "prestamo_recibido"}


@router.get("", response_model=List[schemas.AccountOut])
def list_accounts(include_inactive: bool = False, db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user)):
    q = db.query(models.Account).filter(models.Account.user_id == current_user.id)
    if not include_inactive:
        q = q.filter(models.Account.is_active == True)  # noqa: E712
    return q.order_by(models.Account.is_cash.desc(), models.Account.name).all()


@router.post("", response_model=schemas.AccountOut)
def create_account(payload: schemas.AccountCreate, db: Session = Depends(get_db),
                    current_user: models.User = Depends(get_current_user)):
    if payload.account_type not in VALID_TYPES:
        raise HTTPException(400, "Tipo de cuenta inválido")
    expected_nature = "pasivo" if payload.account_type in DEBT_TYPES else "activo"
    if payload.nature != expected_nature:
        raise HTTPException(400, f"Para '{payload.account_type}' la naturaleza debe ser '{expected_nature}'")

    account = models.Account(
        user_id=current_user.id, name=payload.name, account_type=payload.account_type,
        nature=payload.nature, bank_name=payload.bank_name,
        initial_balance=payload.initial_balance, current_balance=payload.initial_balance,
        notes=payload.notes, is_cash=False,
    )
    db.add(account)
    db.flush()

    if payload.account_type in DEBT_TYPES and payload.credit_detail:
        detail = models.CreditDetail(account_id=account.id, **payload.credit_detail.dict())
        db.add(detail)

    db.commit()
    db.refresh(account)
    return account


@router.put("/{account_id}", response_model=schemas.AccountOut)
def update_account(account_id: int, payload: schemas.AccountUpdate, db: Session = Depends(get_db),
                    current_user: models.User = Depends(get_current_user)):
    account = db.query(models.Account).filter(
        models.Account.id == account_id, models.Account.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(404, "Cuenta no encontrada")

    data = payload.dict(exclude_unset=True, exclude={"credit_detail"})
    for field, value in data.items():
        setattr(account, field, value)

    if payload.credit_detail is not None:
        if account.account_type not in DEBT_TYPES:
            raise HTTPException(400, "Esta cuenta no admite detalle de deuda")
        detail = account.credit_detail
        if not detail:
            detail = models.CreditDetail(account_id=account.id)
            db.add(detail)
        for field, value in payload.credit_detail.dict().items():
            setattr(detail, field, value)

    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}")
def deactivate_account(account_id: int, db: Session = Depends(get_db),
                        current_user: models.User = Depends(get_current_user)):
    account = db.query(models.Account).filter(
        models.Account.id == account_id, models.Account.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(404, "Cuenta no encontrada")
    if account.is_cash:
        raise HTTPException(400, "La cuenta de Efectivo no se puede desactivar")
    has_txns = db.query(models.Transaction).filter(
        (models.Transaction.account_id == account_id) | (models.Transaction.to_account_id == account_id)
    ).count()
    has_fixed = db.query(models.FixedExpense).filter(models.FixedExpense.account_id == account_id).count()
    if has_txns or has_fixed:
        account.is_active = False
        db.commit()
        return {"detail": "Cuenta desactivada (tiene movimientos o gastos fijos asociados)"}
    db.delete(account)
    db.commit()
    return {"detail": "Cuenta eliminada"}
