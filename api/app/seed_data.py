"""
Carga inicial por usuario: se ejecuta una vez al registrarse.
Crea la cuenta especial "Efectivo" y un catálogo estándar de categorías.
"""
from sqlalchemy.orm import Session
from app import models

INCOME_CATEGORIES = [
    ("Salario / Nómina", "fijo", "💼"),
    ("Negocio propio", "variable", "🏪"),
    ("Rentas cobradas", "fijo", "🏠"),
    ("Intereses / Dividendos", "variable", "📈"),
    ("Venta de activos", "variable", "💰"),
    ("Reembolsos", "variable", "↩️"),
    ("Otros ingresos", "variable", "➕"),
]

EXPENSE_CATEGORIES = [
    ("Renta / Hipoteca", "fijo", "🏠"),
    ("Mantenimiento del hogar", "variable", "🛠️"),
    ("Luz", "fijo", "💡"),
    ("Agua", "fijo", "🚿"),
    ("Gas", "fijo", "🔥"),
    ("Internet / Telefonía", "fijo", "📶"),
    ("Suscripciones (streaming, software)", "fijo", "📺"),
    ("Supermercado", "variable", "🛒"),
    ("Restaurantes", "variable", "🍽️"),
    ("Transporte / Gasolina", "variable", "⛽"),
    ("Mantenimiento de auto", "variable", "🚗"),
    ("Salud / Seguro médico", "fijo", "🩺"),
    ("Medicamentos", "variable", "💊"),
    ("Educación", "fijo", "🎓"),
    ("Entretenimiento", "variable", "🎬"),
    ("Ropa y cuidado personal", "variable", "👕"),
    ("Seguros (auto, vida, etc.)", "fijo", "🛡️"),
    ("Mascotas", "variable", "🐾"),
    ("Pago de tarjeta de crédito", "deuda", "💳"),
    ("Pago de préstamos", "deuda", "🏦"),
    ("Aportación a ahorro", "ahorro_inversion", "🐖"),
    ("Aportación a inversión", "ahorro_inversion", "📊"),
    ("Otros gastos", "otros", "❓"),
]


def run_for_user(db: Session, user_id: int):
    cash = models.Account(
        user_id=user_id, name="Efectivo", account_type="efectivo", nature="activo",
        initial_balance=0.0, current_balance=0.0, is_cash=True,
        notes="Control de dinero en efectivo (fuera de cuentas bancarias).",
    )
    db.add(cash)

    for name, group, icon in INCOME_CATEGORIES:
        db.add(models.Category(user_id=user_id, name=name, kind="ingreso", group=group, icon=icon))
    for name, group, icon in EXPENSE_CATEGORIES:
        db.add(models.Category(user_id=user_id, name=name, kind="gasto", group=group, icon=icon))

    db.commit()
