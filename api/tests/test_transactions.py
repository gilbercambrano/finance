from datetime import date
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_cash(client: AsyncClient) -> dict:
    accounts = (await client.get("/api/accounts")).json()
    return next(a for a in accounts if a["is_cash"])


async def _create_account(client: AsyncClient, kind: str = "debito", nature: str = "activo",
                           balance: float = 5000.0) -> dict:
    r = await client.post("/api/accounts", json={
        "name": f"Cuenta {kind}", "account_type": kind, "nature": nature,
        "initial_balance": balance,
    })
    assert r.status_code == 200, r.text
    return r.json()


async def _first_cat(client: AsyncClient, kind: str) -> int:
    cats = (await client.get(f"/api/categories?kind={kind}")).json()
    return cats[0]["id"]


async def _txn(client: AsyncClient, **kwargs) -> dict:
    payload = {"date": str(date.today()), **kwargs}
    r = await client.post("/api/transactions", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


async def _balance(client: AsyncClient, account_id: int) -> float:
    accounts = (await client.get("/api/accounts?include_inactive=true")).json()
    return next(a["current_balance"] for a in accounts if a["id"] == account_id)


# ---------------------------------------------------------------------------
# Ingresos
# ---------------------------------------------------------------------------

async def test_ingreso_cuenta_activa_incrementa_saldo(auth_client: AsyncClient):
    acc = await _create_account(auth_client, balance=1000.0)
    cat_id = await _first_cat(auth_client, "ingreso")
    await _txn(auth_client, kind="ingreso", amount=500.0, account_id=acc["id"], category_id=cat_id)
    assert await _balance(auth_client, acc["id"]) == 1500.0


async def test_ingreso_cuenta_pasiva_decrementa_saldo(auth_client: AsyncClient):
    acc = await _create_account(auth_client, kind="credito", nature="pasivo", balance=500.0)
    cat_id = await _first_cat(auth_client, "ingreso")
    await _txn(auth_client, kind="ingreso", amount=200.0, account_id=acc["id"], category_id=cat_id)
    assert await _balance(auth_client, acc["id"]) == 300.0


# ---------------------------------------------------------------------------
# Gastos
# ---------------------------------------------------------------------------

async def test_gasto_cuenta_activa_decrementa_saldo(auth_client: AsyncClient):
    acc = await _create_account(auth_client, balance=1000.0)
    cat_id = await _first_cat(auth_client, "gasto")
    await _txn(auth_client, kind="gasto", amount=300.0, account_id=acc["id"], category_id=cat_id)
    assert await _balance(auth_client, acc["id"]) == 700.0


async def test_gasto_tarjeta_credito_incrementa_saldo(auth_client: AsyncClient):
    acc = await _create_account(auth_client, kind="credito", nature="pasivo", balance=0.0)
    cat_id = await _first_cat(auth_client, "gasto")
    await _txn(auth_client, kind="gasto", amount=100.0, account_id=acc["id"], category_id=cat_id)
    assert await _balance(auth_client, acc["id"]) == 100.0


# ---------------------------------------------------------------------------
# Transferencias
# ---------------------------------------------------------------------------

async def test_transferencia_entre_activas(auth_client: AsyncClient):
    a1 = await _create_account(auth_client, balance=1000.0)
    a2 = await _create_account(auth_client, kind="ahorro", balance=500.0)
    await _txn(auth_client, kind="transferencia", amount=200.0,
               account_id=a1["id"], to_account_id=a2["id"])
    assert await _balance(auth_client, a1["id"]) == 800.0
    assert await _balance(auth_client, a2["id"]) == 700.0


async def test_transferencia_activa_a_pasiva_pago_tarjeta(auth_client: AsyncClient):
    activa = await _create_account(auth_client, balance=1000.0)
    pasiva = await _create_account(auth_client, kind="credito", nature="pasivo", balance=300.0)
    await _txn(auth_client, kind="transferencia", amount=300.0,
               account_id=activa["id"], to_account_id=pasiva["id"])
    assert await _balance(auth_client, activa["id"]) == 700.0
    assert await _balance(auth_client, pasiva["id"]) == 0.0


# ---------------------------------------------------------------------------
# Validaciones
# ---------------------------------------------------------------------------

async def test_ingreso_sin_category_retorna_400(auth_client: AsyncClient):
    acc = await _create_account(auth_client)
    r = await auth_client.post("/api/transactions", json={
        "date": str(date.today()), "kind": "ingreso", "amount": 100.0,
        "account_id": acc["id"],
    })
    assert r.status_code == 400


async def test_gasto_con_categoria_ingreso_retorna_400(auth_client: AsyncClient):
    acc = await _create_account(auth_client)
    cat_id = await _first_cat(auth_client, "ingreso")
    r = await auth_client.post("/api/transactions", json={
        "date": str(date.today()), "kind": "gasto", "amount": 50.0,
        "account_id": acc["id"], "category_id": cat_id,
    })
    assert r.status_code == 400


async def test_transferencia_misma_cuenta_retorna_400(auth_client: AsyncClient):
    acc = await _create_account(auth_client)
    r = await auth_client.post("/api/transactions", json={
        "date": str(date.today()), "kind": "transferencia", "amount": 50.0,
        "account_id": acc["id"], "to_account_id": acc["id"],
    })
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Edición
# ---------------------------------------------------------------------------

async def test_editar_gasto_corrige_saldo(auth_client: AsyncClient):
    acc = await _create_account(auth_client, balance=1000.0)
    cat_id = await _first_cat(auth_client, "gasto")
    txn = await _txn(auth_client, kind="gasto", amount=100.0, account_id=acc["id"], category_id=cat_id)
    assert await _balance(auth_client, acc["id"]) == 900.0

    r = await auth_client.put(f"/api/transactions/{txn['id']}", json={
        "date": str(date.today()), "kind": "gasto", "amount": 200.0,
        "account_id": acc["id"], "category_id": cat_id,
    })
    assert r.status_code == 200
    # Original 100 reversed (+100), new 200 applied (-200) → 1000 - 200 = 800
    assert await _balance(auth_client, acc["id"]) == 800.0


# ---------------------------------------------------------------------------
# Eliminación
# ---------------------------------------------------------------------------

async def test_delete_ingreso_revierte_saldo(auth_client: AsyncClient):
    acc = await _create_account(auth_client, balance=1000.0)
    cat_id = await _first_cat(auth_client, "ingreso")
    txn = await _txn(auth_client, kind="ingreso", amount=500.0, account_id=acc["id"], category_id=cat_id)
    assert await _balance(auth_client, acc["id"]) == 1500.0

    r = await auth_client.delete(f"/api/transactions/{txn['id']}")
    assert r.status_code == 200
    assert await _balance(auth_client, acc["id"]) == 1000.0


async def test_delete_transferencia_revierte_ambos_saldos(auth_client: AsyncClient):
    a1 = await _create_account(auth_client, balance=1000.0)
    a2 = await _create_account(auth_client, kind="ahorro", balance=500.0)
    txn = await _txn(auth_client, kind="transferencia", amount=300.0,
                     account_id=a1["id"], to_account_id=a2["id"])
    assert await _balance(auth_client, a1["id"]) == 700.0
    assert await _balance(auth_client, a2["id"]) == 800.0

    r = await auth_client.delete(f"/api/transactions/{txn['id']}")
    assert r.status_code == 200
    assert await _balance(auth_client, a1["id"]) == 1000.0
    assert await _balance(auth_client, a2["id"]) == 500.0


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

async def test_filtro_por_account_id(auth_client: AsyncClient):
    a1 = await _create_account(auth_client, balance=500.0)
    a2 = await _create_account(auth_client, kind="ahorro", balance=500.0)
    cat_id = await _first_cat(auth_client, "gasto")
    await _txn(auth_client, kind="gasto", amount=10.0, account_id=a1["id"], category_id=cat_id)
    await _txn(auth_client, kind="gasto", amount=20.0, account_id=a2["id"], category_id=cat_id)

    r = await auth_client.get(f"/api/transactions?account_id={a1['id']}")
    txns = r.json()
    assert all(t["account_id"] == a1["id"] or t["to_account_id"] == a1["id"] for t in txns)
    assert any(t["amount"] == 10.0 for t in txns)
