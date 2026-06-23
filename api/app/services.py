"""
Lógica de negocio:
- Efecto de transacciones sobre saldos (según naturaleza activo/pasivo).
- Cálculo del periodo de presupuesto vigente.
- Cálculo y avance de fechas para gastos fijos recurrentes.
- Sincronización de ocurrencias de gastos fijos (generación automática o
  pendiente de confirmación) y cálculo del indicador de gasto fijo mensual.
"""
import calendar
from datetime import date, timedelta
from typing import Optional
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from app import models


# ---------------------------------------------------------------
# Saldos de cuentas
# ---------------------------------------------------------------
def apply_transaction_effect(db: Session, txn: models.Transaction, reverse: bool = False):
    sign = -1 if reverse else 1
    account = db.query(models.Account).get(txn.account_id)

    if txn.kind == "ingreso":
        delta = txn.amount if account.nature == "activo" else -txn.amount
        account.current_balance += sign * delta

    elif txn.kind == "gasto":
        delta = -txn.amount if account.nature == "activo" else txn.amount
        account.current_balance += sign * delta

    elif txn.kind == "transferencia":
        to_account = db.query(models.Account).get(txn.to_account_id)
        delta_from = -txn.amount if account.nature == "activo" else txn.amount
        account.current_balance += sign * delta_from
        delta_to = txn.amount if to_account.nature == "activo" else -txn.amount
        to_account.current_balance += sign * delta_to

    db.add(account)


def net_worth(db: Session, user_id: int):
    accounts = db.query(models.Account).filter(
        models.Account.user_id == user_id, models.Account.is_active == True  # noqa: E712
    ).all()
    assets = sum(a.current_balance for a in accounts if a.nature == "activo")
    liabilities = sum(a.current_balance for a in accounts if a.nature == "pasivo")
    return {
        "activos": round(assets, 2),
        "pasivos": round(liabilities, 2),
        "patrimonio_neto": round(assets - liabilities, 2),
    }


# ---------------------------------------------------------------
# Periodos de presupuesto
# ---------------------------------------------------------------
def get_period_range(period_type: str, start_date: date, ref_date: date,
                      end_date: Optional[date] = None):
    if period_type == "personalizado":
        return start_date, (end_date or ref_date)

    if ref_date < start_date:
        return start_date, start_date

    if period_type == "mensual":
        cursor = start_date
        while True:
            nxt = cursor + relativedelta(months=1)
            if end_date and cursor > end_date:
                return cursor, cursor
            if cursor <= ref_date < nxt:
                period_end = min(nxt - timedelta(days=1), end_date) if end_date else nxt - timedelta(days=1)
                return cursor, period_end
            cursor = nxt

    delta_days = {"quincenal": 15, "semanal": 7}.get(period_type, 30)
    cursor = start_date
    while True:
        nxt = cursor + timedelta(days=delta_days)
        if end_date and cursor > end_date:
            return cursor, cursor
        if cursor <= ref_date < nxt:
            period_end = min(nxt - timedelta(days=1), end_date) if end_date else nxt - timedelta(days=1)
            return cursor, period_end
        cursor = nxt


# ---------------------------------------------------------------
# Gastos fijos: cálculo y avance de fechas
# ---------------------------------------------------------------
FREQUENCY_MONTHLY_FACTOR = {
    # factor para "mensualizar" un monto, según frecuencia
    "semanal": 4.345,
    "quincenal": 2.0,
    "mensual": 1.0,
    "bimestral": 0.5,
    "trimestral": 1 / 3,
    "semestral": 1 / 6,
    "anual": 1 / 12,
}


def _clamp_day(year: int, month: int, day: int) -> int:
    last_day = calendar.monthrange(year, month)[1]
    return min(day, last_day)


def first_due_date(frequency: str, due_day: int, start_date: date) -> date:
    """Calcula la primera fecha de vencimiento a partir de start_date."""
    if frequency == "semanal":
        # due_day = día de semana (0=lunes ... 6=domingo)
        days_ahead = (due_day - start_date.weekday()) % 7
        return start_date + timedelta(days=days_ahead)

    if frequency == "quincenal":
        # vence en los días 1 y 16 más próximos a partir de start_date
        candidates = []
        for d in (1, 16):
            c = start_date.replace(day=min(d, calendar.monthrange(start_date.year, start_date.month)[1]))
            if c >= start_date:
                candidates.append(c)
        if candidates:
            return min(candidates)
        nxt_month = start_date + relativedelta(months=1)
        return nxt_month.replace(day=1)

    # mensual, bimestral, trimestral, semestral, anual -> usan due_day como día del mes
    day = _clamp_day(start_date.year, start_date.month, due_day)
    candidate = start_date.replace(day=day)
    if candidate >= start_date:
        return candidate
    nxt = start_date + relativedelta(months=1)
    return nxt.replace(day=_clamp_day(nxt.year, nxt.month, due_day))


def advance_due_date(frequency: str, due_day: int, current_due: date) -> date:
    """Calcula la siguiente fecha de vencimiento a partir de la actual."""
    if frequency == "semanal":
        return current_due + timedelta(days=7)

    if frequency == "quincenal":
        if current_due.day == 1:
            return current_due.replace(day=min(16, calendar.monthrange(current_due.year, current_due.month)[1]))
        nxt = current_due + relativedelta(months=1)
        return nxt.replace(day=1)

    months_map = {"mensual": 1, "bimestral": 2, "trimestral": 3, "semestral": 6, "anual": 12}
    months = months_map.get(frequency, 1)
    nxt = current_due + relativedelta(months=months)
    return nxt.replace(day=_clamp_day(nxt.year, nxt.month, due_day))


# ---------------------------------------------------------------
# Sincronización de ocurrencias
# ---------------------------------------------------------------
def sync_fixed_expense(db: Session, fe: models.FixedExpense, today: Optional[date] = None,
                        max_iterations: int = 36):
    """
    Genera las ocurrencias vencidas hasta 'today' que falten, y si el gasto
    es de monto fijo y tiene auto_post activo, crea el movimiento real.
    Devuelve la lista de ocurrencias creadas en esta llamada.
    """
    today = today or date.today()
    created = []
    iterations = 0
    while fe.next_due_date <= today and iterations < max_iterations:
        iterations += 1
        existing = db.query(models.FixedExpenseOccurrence).filter_by(
            fixed_expense_id=fe.id, due_date=fe.next_due_date
        ).first()
        if existing:
            occ = existing
        else:
            occ = models.FixedExpenseOccurrence(
                fixed_expense_id=fe.id,
                due_date=fe.next_due_date,
                expected_amount=fe.estimated_amount,
                status="pendiente",
            )
            db.add(occ)
            db.flush()
            created.append(occ)

            if fe.auto_post and not fe.is_variable_amount:
                txn = models.Transaction(
                    user_id=fe.user_id,
                    date=occ.due_date,
                    kind="gasto",
                    amount=occ.expected_amount,
                    description=f"{fe.name} (automático)",
                    account_id=fe.account_id,
                    category_id=fe.category_id,
                    fixed_expense_occurrence_id=occ.id,
                )
                db.add(txn)
                db.flush()
                apply_transaction_effect(db, txn)
                occ.status = "pagado"

        fe.next_due_date = advance_due_date(fe.frequency, fe.due_day, fe.next_due_date)

    db.add(fe)
    return created


def sync_all_fixed_expenses(db: Session, user_id: int):
    expenses = db.query(models.FixedExpense).filter(
        models.FixedExpense.user_id == user_id, models.FixedExpense.is_active == True  # noqa: E712
    ).all()
    for fe in expenses:
        sync_fixed_expense(db, fe)
    db.commit()
