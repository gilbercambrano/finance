import calendar
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from dateutil.relativedelta import relativedelta
from app.database import get_db
from app import models, services
from app.deps import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/resumen")
def resumen(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    nw = services.net_worth(db, current_user.id)
    accounts = db.query(models.Account).filter(
        models.Account.user_id == current_user.id, models.Account.is_active == True  # noqa: E712
    ).order_by(models.Account.is_cash.desc(), models.Account.name).all()
    accounts_out = [{
        "id": a.id, "name": a.name, "account_type": a.account_type,
        "nature": a.nature, "balance": round(a.current_balance, 2), "is_cash": a.is_cash,
    } for a in accounts]
    return {"patrimonio": nw, "cuentas": accounts_out}


@router.get("/flujo")
def flujo(date_from: Optional[date] = None, date_to: Optional[date] = None,
          db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    today = date.today()
    date_from = date_from or today.replace(day=1)
    date_to = date_to or today

    base_q = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.date >= date_from, models.Transaction.date <= date_to,
    )
    total_ingresos = sum(r[0] for r in base_q.filter(models.Transaction.kind == "ingreso").with_entities(models.Transaction.amount).all())
    total_gastos = sum(r[0] for r in base_q.filter(models.Transaction.kind == "gasto").with_entities(models.Transaction.amount).all())

    return {
        "periodo": {"desde": date_from, "hasta": date_to},
        "total_ingresos": round(total_ingresos, 2),
        "total_gastos": round(total_gastos, 2),
        "ahorro_neto": round(total_ingresos - total_gastos, 2),
        "tasa_ahorro_pct": round((total_ingresos - total_gastos) / total_ingresos * 100, 1) if total_ingresos else 0,
    }


@router.get("/gastos-por-categoria")
def gastos_por_categoria(date_from: Optional[date] = None, date_to: Optional[date] = None,
                          db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    today = date.today()
    date_from = date_from or today.replace(day=1)
    date_to = date_to or today
    rows = (
        db.query(models.Category.name, models.Category.group, models.Transaction.amount)
        .join(models.Transaction, models.Transaction.category_id == models.Category.id)
        .filter(
            models.Transaction.user_id == current_user.id, models.Transaction.kind == "gasto",
            models.Transaction.date >= date_from, models.Transaction.date <= date_to,
        ).all()
    )
    agg = {}
    for name, group, amount in rows:
        agg.setdefault(name, {"categoria": name, "grupo": group, "total": 0.0})
        agg[name]["total"] += amount
    result = sorted(agg.values(), key=lambda x: x["total"], reverse=True)
    for r in result:
        r["total"] = round(r["total"], 2)
    return result


@router.get("/tendencia")
def tendencia(meses: int = Query(6, ge=1, le=24), db: Session = Depends(get_db),
              current_user: models.User = Depends(get_current_user)):
    today = date.today()
    start = today.replace(day=1) - relativedelta(months=meses - 1)
    rows = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.kind.in_(["ingreso", "gasto"]),
        models.Transaction.date >= start,
    ).all()

    buckets = {}
    cursor = start
    for _ in range(meses):
        key = cursor.strftime("%Y-%m")
        buckets[key] = {"mes": key, "ingresos": 0.0, "gastos": 0.0}
        cursor = cursor + relativedelta(months=1)

    for t in rows:
        key = t.date.strftime("%Y-%m")
        if key in buckets:
            if t.kind == "ingreso":
                buckets[key]["ingresos"] += t.amount
            else:
                buckets[key]["gastos"] += t.amount

    result = list(buckets.values())
    for r in result:
        r["ingresos"] = round(r["ingresos"], 2)
        r["gastos"] = round(r["gastos"], 2)
        r["ahorro"] = round(r["ingresos"] - r["gastos"], 2)
    return result


@router.get("/presupuestos-activos")
def presupuestos_activos(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from app.routers.budgets import _budget_status
    budgets = db.query(models.Budget).filter(
        models.Budget.user_id == current_user.id, models.Budget.is_active == True  # noqa: E712
    ).all()
    return [_budget_status(b, db) for b in budgets]


@router.get("/deudas")
def deudas(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Resumen de tarjetas de crédito y préstamos recibidos (pasivos)."""
    accounts = db.query(models.Account).filter(
        models.Account.user_id == current_user.id, models.Account.is_active == True,  # noqa: E712
        models.Account.nature == "pasivo",
    ).all()
    today = date.today()
    result = []
    total_deuda = 0.0
    for a in accounts:
        cd = a.credit_detail
        item = {
            "account_id": a.id, "name": a.name, "account_type": a.account_type,
            "balance": round(a.current_balance, 2),
            "credit_limit": cd.credit_limit if cd else None,
            "utilization_pct": round(a.current_balance / cd.credit_limit * 100, 1) if (cd and cd.credit_limit) else None,
            "minimum_payment": cd.minimum_payment if cd else None,
            "interest_rate_annual": cd.interest_rate_annual if cd else None,
            "next_cutoff_date": None, "next_payment_due_date": None,
        }
        if cd and cd.cutoff_day:
            last_day = calendar.monthrange(today.year, today.month)[1]
            cutoff_this_month = today.replace(day=min(cd.cutoff_day, last_day))
            item["next_cutoff_date"] = (
                cutoff_this_month if cutoff_this_month >= today else
                (cutoff_this_month + relativedelta(months=1)).replace(
                    day=min(cd.cutoff_day, calendar.monthrange((cutoff_this_month + relativedelta(months=1)).year, (cutoff_this_month + relativedelta(months=1)).month)[1])
                )
            )
        if cd and cd.payment_due_day:
            last_day = calendar.monthrange(today.year, today.month)[1]
            due_this_month = today.replace(day=min(cd.payment_due_day, last_day))
            item["next_payment_due_date"] = (
                due_this_month if due_this_month >= today else
                (due_this_month + relativedelta(months=1)).replace(
                    day=min(cd.payment_due_day, calendar.monthrange((due_this_month + relativedelta(months=1)).year, (due_this_month + relativedelta(months=1)).month)[1])
                )
            )
        total_deuda += a.current_balance
        result.append(item)
    return {"total_deuda": round(total_deuda, 2), "cuentas": result}


@router.get("/gastos-fijos")
def gastos_fijos(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Indicador de gasto fijo mensual: mensualizado + lo real del mes (pagado/pendiente)."""
    services.sync_all_fixed_expenses(db, current_user.id)
    today = date.today()
    month_start = today.replace(day=1)
    month_end = month_start + relativedelta(months=1) - relativedelta(days=1)

    active = db.query(models.FixedExpense).filter(
        models.FixedExpense.user_id == current_user.id, models.FixedExpense.is_active == True  # noqa: E712
    ).all()
    total_mensualizado = sum(
        fe.estimated_amount * services.FREQUENCY_MONTHLY_FACTOR.get(fe.frequency, 1.0) for fe in active
    )

    occ_this_month = db.query(models.FixedExpenseOccurrence).join(models.FixedExpense).filter(
        models.FixedExpense.user_id == current_user.id,
        models.FixedExpenseOccurrence.due_date >= month_start,
        models.FixedExpenseOccurrence.due_date <= month_end,
    ).all()

    pagado = sum(o.expected_amount for o in occ_this_month if o.status == "pagado")
    pendiente_list = [o for o in occ_this_month if o.status == "pendiente"]
    pendiente = sum(o.expected_amount for o in pendiente_list)

    return {
        "total_mensualizado_estimado": round(total_mensualizado, 2),
        "mes_actual": {
            "pagado": round(pagado, 2),
            "pendiente": round(pendiente, 2),
            "pendientes": [
                {
                    "occurrence_id": o.id, "nombre": o.fixed_expense.name,
                    "categoria": o.fixed_expense.category.name if o.fixed_expense.category else None,
                    "monto_estimado": round(o.expected_amount, 2), "fecha_limite": o.due_date,
                } for o in sorted(pendiente_list, key=lambda x: x.due_date)
            ],
        },
        "cantidad_gastos_fijos_activos": len(active),
    }
