from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.database import get_db
from app import models, schemas, services
from app.deps import get_current_user

router = APIRouter(prefix="/api/fixed-expenses", tags=["fixed-expenses"])

VALID_FREQUENCIES = {"semanal", "quincenal", "mensual", "bimestral", "trimestral", "semestral", "anual"}


def _to_out(fe: models.FixedExpense) -> schemas.FixedExpenseOut:
    return schemas.FixedExpenseOut(
        id=fe.id, name=fe.name, category_id=fe.category_id,
        category_name=fe.category.name if fe.category else None,
        account_id=fe.account_id, account_name=fe.account.name if fe.account else None,
        estimated_amount=fe.estimated_amount, is_variable_amount=fe.is_variable_amount,
        frequency=fe.frequency, due_day=fe.due_day, next_due_date=fe.next_due_date,
        auto_post=fe.auto_post, is_active=fe.is_active, notes=fe.notes,
    )


@router.get("", response_model=List[schemas.FixedExpenseOut])
def list_fixed_expenses(include_inactive: bool = False, db: Session = Depends(get_db),
                         current_user: models.User = Depends(get_current_user)):
    services.sync_all_fixed_expenses(db, current_user.id)
    q = db.query(models.FixedExpense).filter(models.FixedExpense.user_id == current_user.id)
    if not include_inactive:
        q = q.filter(models.FixedExpense.is_active == True)  # noqa: E712
    return [_to_out(fe) for fe in q.order_by(models.FixedExpense.next_due_date).all()]


@router.post("", response_model=schemas.FixedExpenseOut)
def create_fixed_expense(payload: schemas.FixedExpenseCreate, db: Session = Depends(get_db),
                          current_user: models.User = Depends(get_current_user)):
    if payload.frequency not in VALID_FREQUENCIES:
        raise HTTPException(400, "Frecuencia inválida")
    account = db.query(models.Account).filter(
        models.Account.id == payload.account_id, models.Account.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(400, "Cuenta de pago inválida")
    cat = db.query(models.Category).filter(
        models.Category.id == payload.category_id, models.Category.user_id == current_user.id, models.Category.kind == "gasto"
    ).first()
    if not cat:
        raise HTTPException(400, "Categoría inválida (debe ser de tipo gasto)")

    start = payload.start_date or date.today()
    next_due = services.first_due_date(payload.frequency, payload.due_day, start)

    fe = models.FixedExpense(
        user_id=current_user.id, name=payload.name, category_id=payload.category_id,
        account_id=payload.account_id, estimated_amount=payload.estimated_amount,
        is_variable_amount=payload.is_variable_amount, frequency=payload.frequency,
        due_day=payload.due_day, next_due_date=next_due,
        auto_post=(payload.auto_post and not payload.is_variable_amount),
        notes=payload.notes,
    )
    db.add(fe)
    db.commit()
    db.refresh(fe)
    return _to_out(fe)


@router.put("/{fe_id}", response_model=schemas.FixedExpenseOut)
def update_fixed_expense(fe_id: int, payload: schemas.FixedExpenseUpdate, db: Session = Depends(get_db),
                          current_user: models.User = Depends(get_current_user)):
    fe = db.query(models.FixedExpense).filter(
        models.FixedExpense.id == fe_id, models.FixedExpense.user_id == current_user.id
    ).first()
    if not fe:
        raise HTTPException(404, "Gasto fijo no encontrado")

    data = payload.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(fe, field, value)
    if fe.is_variable_amount:
        fe.auto_post = False

    db.commit()
    db.refresh(fe)
    return _to_out(fe)


@router.delete("/{fe_id}")
def deactivate_fixed_expense(fe_id: int, db: Session = Depends(get_db),
                              current_user: models.User = Depends(get_current_user)):
    fe = db.query(models.FixedExpense).filter(
        models.FixedExpense.id == fe_id, models.FixedExpense.user_id == current_user.id
    ).first()
    if not fe:
        raise HTTPException(404, "Gasto fijo no encontrado")
    fe.is_active = False
    db.commit()
    return {"detail": "Gasto fijo desactivado. Ya no generará nuevas ocurrencias."}


@router.get("/occurrences/pending", response_model=List[schemas.FixedExpenseOccurrenceOut])
def pending_occurrences(db: Session = Depends(get_db),
                         current_user: models.User = Depends(get_current_user)):
    services.sync_all_fixed_expenses(db, current_user.id)
    rows = db.query(models.FixedExpenseOccurrence).join(models.FixedExpense).filter(
        models.FixedExpense.user_id == current_user.id,
        models.FixedExpenseOccurrence.status == "pendiente",
    ).order_by(models.FixedExpenseOccurrence.due_date).all()
    return [
        schemas.FixedExpenseOccurrenceOut(
            id=o.id, fixed_expense_id=o.fixed_expense_id, fixed_expense_name=o.fixed_expense.name,
            category_name=o.fixed_expense.category.name if o.fixed_expense.category else None,
            account_name=o.fixed_expense.account.name if o.fixed_expense.account else None,
            due_date=o.due_date, expected_amount=o.expected_amount, status=o.status,
        ) for o in rows
    ]


@router.post("/occurrences/{occ_id}/confirm")
def confirm_occurrence(occ_id: int, payload: schemas.ConfirmOccurrencePayload, db: Session = Depends(get_db),
                        current_user: models.User = Depends(get_current_user)):
    occ = db.query(models.FixedExpenseOccurrence).join(models.FixedExpense).filter(
        models.FixedExpenseOccurrence.id == occ_id, models.FixedExpense.user_id == current_user.id
    ).first()
    if not occ:
        raise HTTPException(404, "Ocurrencia no encontrada")
    if occ.status == "pagado":
        raise HTTPException(400, "Esta ocurrencia ya fue confirmada")

    fe = occ.fixed_expense
    account_id = payload.account_id or fe.account_id
    account = db.query(models.Account).filter(
        models.Account.id == account_id, models.Account.user_id == current_user.id
    ).first()
    if not account:
        raise HTTPException(400, "Cuenta de pago inválida")

    amount = payload.amount if payload.amount is not None else occ.expected_amount
    txn = models.Transaction(
        user_id=current_user.id, date=payload.date or date.today(), kind="gasto", amount=amount,
        description=f"{fe.name} (confirmado)", account_id=account_id, category_id=fe.category_id,
        fixed_expense_occurrence_id=occ.id,
    )
    db.add(txn)
    db.flush()
    services.apply_transaction_effect(db, txn)
    occ.status = "pagado"
    db.commit()
    return {"detail": "Pago confirmado y movimiento registrado"}


@router.post("/occurrences/{occ_id}/skip")
def skip_occurrence(occ_id: int, db: Session = Depends(get_db),
                     current_user: models.User = Depends(get_current_user)):
    occ = db.query(models.FixedExpenseOccurrence).join(models.FixedExpense).filter(
        models.FixedExpenseOccurrence.id == occ_id, models.FixedExpense.user_id == current_user.id
    ).first()
    if not occ:
        raise HTTPException(404, "Ocurrencia no encontrada")
    occ.status = "omitido"
    db.commit()
    return {"detail": "Ocurrencia omitida"}
