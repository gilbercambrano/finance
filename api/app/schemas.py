from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime


# ---------- Auth ----------
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Credit detail ----------
class CreditDetailBase(BaseModel):
    credit_limit: Optional[float] = None
    original_amount: Optional[float] = None
    cutoff_day: Optional[int] = Field(default=None, ge=1, le=31)
    payment_due_day: Optional[int] = Field(default=None, ge=1, le=31)
    minimum_payment: Optional[float] = None
    interest_rate_annual: Optional[float] = None
    notes: Optional[str] = None


class CreditDetailOut(CreditDetailBase):
    class Config:
        from_attributes = True


# ---------- Accounts ----------
class AccountBase(BaseModel):
    name: str
    account_type: str
    nature: str
    bank_name: Optional[str] = None
    initial_balance: float = 0.0
    notes: Optional[str] = None


class AccountCreate(AccountBase):
    credit_detail: Optional[CreditDetailBase] = None


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    bank_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    credit_detail: Optional[CreditDetailBase] = None


class AccountOut(AccountBase):
    id: int
    current_balance: float
    is_cash: bool
    is_active: bool
    credit_detail: Optional[CreditDetailOut] = None

    class Config:
        from_attributes = True


# ---------- Categories ----------
class CategoryBase(BaseModel):
    name: str
    kind: str
    group: str
    icon: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryOut(CategoryBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


# ---------- Transactions ----------
class TransactionBase(BaseModel):
    date: date
    kind: str
    amount: float = Field(gt=0)
    description: Optional[str] = None
    account_id: int
    to_account_id: Optional[int] = None
    category_id: Optional[int] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionOut(TransactionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionDetailOut(TransactionOut):
    account_name: Optional[str] = None
    to_account_name: Optional[str] = None
    category_name: Optional[str] = None


# ---------- Budgets ----------
class BudgetItemBase(BaseModel):
    category_id: int
    planned_amount: float = Field(gt=0)


class BudgetItemOut(BudgetItemBase):
    id: int
    category_name: Optional[str] = None

    class Config:
        from_attributes = True


class BudgetCreate(BaseModel):
    name: str
    period_type: str
    start_date: date
    end_date: Optional[date] = None
    items: List[BudgetItemBase]


class BudgetOut(BaseModel):
    id: int
    name: str
    period_type: str
    start_date: date
    end_date: Optional[date]
    is_active: bool
    items: List[BudgetItemOut] = []

    class Config:
        from_attributes = True


# ---------- Fixed Expenses ----------
class FixedExpenseBase(BaseModel):
    name: str
    category_id: int
    account_id: int
    estimated_amount: float = Field(gt=0)
    is_variable_amount: bool = False
    frequency: str  # semanal|quincenal|mensual|bimestral|trimestral|semestral|anual
    due_day: int = Field(ge=0, le=31)
    auto_post: bool = False
    notes: Optional[str] = None
    start_date: Optional[date] = None  # solo en creación, para anclar la primera ocurrencia


class FixedExpenseCreate(FixedExpenseBase):
    pass


class FixedExpenseUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None
    estimated_amount: Optional[float] = None
    is_variable_amount: Optional[bool] = None
    auto_post: Optional[bool] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class FixedExpenseOut(BaseModel):
    id: int
    name: str
    category_id: int
    category_name: Optional[str] = None
    account_id: int
    account_name: Optional[str] = None
    estimated_amount: float
    is_variable_amount: bool
    frequency: str
    due_day: int
    next_due_date: date
    auto_post: bool
    is_active: bool
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class FixedExpenseOccurrenceOut(BaseModel):
    id: int
    fixed_expense_id: int
    fixed_expense_name: Optional[str] = None
    category_name: Optional[str] = None
    account_name: Optional[str] = None
    due_date: date
    expected_amount: float
    status: str

    class Config:
        from_attributes = True


class ConfirmOccurrencePayload(BaseModel):
    amount: Optional[float] = None  # permite ajustar el monto real (ej. luz variable)
    account_id: Optional[int] = None  # permite pagar desde otra cuenta distinta a la default
    date: Optional[date] = None
