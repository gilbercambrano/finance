from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.database import get_db
from app import models, schemas, services
from app.deps import get_current_user

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


def _budget_to_out(budget: models.Budget) -> schemas.BudgetOut:
    return schemas.BudgetOut(
        id=budget.id, name=budget.name, period_type=budget.period_type,
        start_date=budget.start_date, end_date=budget.end_date, is_active=budget.is_active,
        items=[
            schemas.BudgetItemOut(
                id=i.id, category_id=i.category_id, planned_amount=i.planned_amount,
                category_name=i.category.name if i.category else None,
            ) for i in budget.items
        ],
    )


@router.get("", response_model=List[schemas.BudgetOut])
def list_budgets(include_inactive: bool = False, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user)):
    q = db.query(models.Budget).filter(models.Budget.user_id == current_user.id)
    if not include_inactive:
        q = q.filter(models.Budget.is_active == True)  # noqa: E712
    return [_budget_to_out(b) for b in q.order_by(models.Budget.start_date.desc()).all()]


@router.post("", response_model=schemas.BudgetOut)
def create_budget(payload: schemas.BudgetCreate, db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user)):
    if payload.period_type not in {"mensual", "quincenal", "semanal", "personalizado"}:
        raise HTTPException(400, "Tipo de periodo inválido")
    if not payload.items:
        raise HTTPException(400, "El presupuesto necesita al menos una categoría")
    budget = models.Budget(
        user_id=current_user.id, name=payload.name, period_type=payload.period_type,
        start_date=payload.start_date, end_date=payload.end_date,
    )
    db.add(budget)
    db.flush()
    for item in payload.items:
        db.add(models.BudgetItem(
            budget_id=budget.id, category_id=item.category_id, planned_amount=item.planned_amount
        ))
    db.commit()
    db.refresh(budget)
    return _budget_to_out(budget)


@router.delete("/{budget_id}")
def deactivate_budget(budget_id: int, db: Session = Depends(get_db),
                       current_user: models.User = Depends(get_current_user)):
    budget = db.query(models.Budget).filter(
        models.Budget.id == budget_id, models.Budget.user_id == current_user.id
    ).first()
    if not budget:
        raise HTTPException(404, "Presupuesto no encontrado")
    budget.is_active = False
    db.commit()
    return {"detail": "Presupuesto desactivado"}


def _budget_status(budget: models.Budget, db: Session, ref_date: Optional[date] = None):
    ref = ref_date or date.today()
    period_start, period_end = services.get_period_range(
        budget.period_type, budget.start_date, ref, budget.end_date
    )
    items_status = []
    total_planned = 0.0
    total_actual = 0.0
    for item in budget.items:
        actual = db.query(models.Transaction).filter(
            models.Transaction.category_id == item.category_id,
            models.Transaction.kind == item.category.kind,
            models.Transaction.date >= period_start,
            models.Transaction.date <= period_end,
        ).with_entities(models.Transaction.amount).all()
        actual_sum = sum(a[0] for a in actual)
        deviation = actual_sum - item.planned_amount
        deviation_pct = (deviation / item.planned_amount * 100) if item.planned_amount else 0
        total_planned += item.planned_amount
        total_actual += actual_sum
        items_status.append({
            "category_id": item.category_id, "category_name": item.category.name,
            "planned_amount": round(item.planned_amount, 2), "actual_amount": round(actual_sum, 2),
            "deviation": round(deviation, 2), "deviation_pct": round(deviation_pct, 1),
            "status": "alerta" if deviation > 0 else "ok",
        })
    return {
        "budget_id": budget.id, "budget_name": budget.name, "period_type": budget.period_type,
        "period_start": period_start, "period_end": period_end, "items": items_status,
        "total_planned": round(total_planned, 2), "total_actual": round(total_actual, 2),
        "total_deviation": round(total_actual - total_planned, 2),
    }


@router.get("/{budget_id}/status")
def budget_status(budget_id: int, ref_date: Optional[date] = None, db: Session = Depends(get_db),
                   current_user: models.User = Depends(get_current_user)):
    budget = db.query(models.Budget).filter(
        models.Budget.id == budget_id, models.Budget.user_id == current_user.id
    ).first()
    if not budget:
        raise HTTPException(404, "Presupuesto no encontrado")
    return _budget_status(budget, db, ref_date)
