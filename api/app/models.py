"""
Modelos de datos — v2 (multiusuario, PostgreSQL).

Cada tabla de negocio tiene user_id: cada usuario administra su información
de forma completamente independiente.

Cuentas / naturaleza:
- activo: débito, ahorro, efectivo, inversión, préstamo otorgado (a terceros)
- pasivo: tarjeta de crédito, préstamo recibido (deuda propia)

CreditDetail: información de ciclo de deuda para cuentas pasivas
(tarjeta de crédito o préstamo recibido): límite, corte, pago mínimo, tasa.

FixedExpense / FixedExpenseOccurrence: pagos fijos calendarizados
(servicios, suscripciones, domiciliados, mensualidades de deuda) con
generación de ocurrencias y registro automático o manual del movimiento.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, ForeignKey, Boolean,
    Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime, date as date_cls
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    account_type = Column(String(30), nullable=False)
    # debito, ahorro, credito, inversion, efectivo, prestamo, prestamo_recibido
    nature = Column(String(10), nullable=False)  # 'activo' | 'pasivo'
    bank_name = Column(String(100), nullable=True)
    initial_balance = Column(Float, default=0.0)
    current_balance = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    is_cash = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    credit_detail = relationship(
        "CreditDetail", back_populates="account", uselist=False, cascade="all, delete-orphan"
    )


class CreditDetail(Base):
    """Información de ciclo de deuda: tarjetas de crédito y préstamos recibidos."""
    __tablename__ = "credit_details"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), unique=True, nullable=False)

    credit_limit = Column(Float, nullable=True)        # solo tarjetas
    original_amount = Column(Float, nullable=True)      # solo préstamos
    cutoff_day = Column(Integer, nullable=True)         # día de corte (1-31)
    payment_due_day = Column(Integer, nullable=True)    # día límite de pago (1-31)
    minimum_payment = Column(Float, nullable=True)
    interest_rate_annual = Column(Float, nullable=True)  # % anual (CAT/tasa)
    notes = Column(Text, nullable=True)

    account = relationship("Account", back_populates="credit_detail")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    kind = Column(String(10), nullable=False)  # 'ingreso' | 'gasto'
    group = Column(String(20), nullable=False)
    # fijo | variable | ahorro_inversion | deuda | otros
    icon = Column(String(10), nullable=True)
    is_active = Column(Boolean, default=True)

    transactions = relationship("Transaction", back_populates="category")
    budget_items = relationship("BudgetItem", back_populates="category")
    fixed_expenses = relationship("FixedExpense", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, default=date_cls.today)
    kind = Column(String(15), nullable=False)  # 'ingreso' | 'gasto' | 'transferencia'
    amount = Column(Float, nullable=False)
    description = Column(String(255), nullable=True)

    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    fixed_expense_occurrence_id = Column(Integer, ForeignKey("fixed_expense_occurrences.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", foreign_keys=[account_id])
    to_account = relationship("Account", foreign_keys=[to_account_id])
    category = relationship("Category", back_populates="transactions")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    period_type = Column(String(20), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("BudgetItem", back_populates="budget", cascade="all, delete-orphan")


class BudgetItem(Base):
    __tablename__ = "budget_items"

    id = Column(Integer, primary_key=True, index=True)
    budget_id = Column(Integer, ForeignKey("budgets.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    planned_amount = Column(Float, nullable=False)

    budget = relationship("Budget", back_populates="items")
    category = relationship("Category", back_populates="budget_items")


class FixedExpense(Base):
    """
    Pago fijo / recurrente calendarizado: servicios (luz, agua, internet),
    suscripciones, pagos domiciliados, mensualidades de deuda, etc.
    """
    __tablename__ = "fixed_expenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)  # cuenta/tarjeta de pago

    estimated_amount = Column(Float, nullable=False)  # monto fijo o estimado si es variable
    is_variable_amount = Column(Boolean, default=False)  # True = monto cambia cada periodo (luz, agua)
    frequency = Column(String(20), nullable=False)
    # semanal | quincenal | mensual | bimestral | trimestral | semestral | anual
    due_day = Column(Integer, nullable=False)  # día del mes (1-31) o día de semana (0=lunes) si es semanal
    next_due_date = Column(Date, nullable=False)  # cursor de próxima fecha a generar

    auto_post = Column(Boolean, default=False)  # solo aplica si is_variable_amount=False
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="fixed_expenses")
    account = relationship("Account")
    occurrences = relationship("FixedExpenseOccurrence", back_populates="fixed_expense", cascade="all, delete-orphan")


class FixedExpenseOccurrence(Base):
    """Una instancia/periodo concreto de un gasto fijo (ej. 'Internet - julio 2026')."""
    __tablename__ = "fixed_expense_occurrences"

    id = Column(Integer, primary_key=True, index=True)
    fixed_expense_id = Column(Integer, ForeignKey("fixed_expenses.id"), nullable=False, index=True)
    due_date = Column(Date, nullable=False)
    expected_amount = Column(Float, nullable=False)
    status = Column(String(15), default="pendiente")  # pendiente | pagado | omitido
    created_at = Column(DateTime, default=datetime.utcnow)

    fixed_expense = relationship("FixedExpense", back_populates="occurrences")
    transaction = relationship("Transaction", uselist=False, viewonly=True,
                                primaryjoin="FixedExpenseOccurrence.id==Transaction.fixed_expense_occurrence_id")

    __table_args__ = (UniqueConstraint("fixed_expense_id", "due_date", name="uq_fixedexpense_duedate"),)
