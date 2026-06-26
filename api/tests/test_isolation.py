from datetime import date
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_account(client: AsyncClient) -> dict:
    r = await client.post("/api/accounts", json={
        "name": "Cuenta Privada", "account_type": "debito",
        "nature": "activo", "initial_balance": 1000.0,
    })
    assert r.status_code == 200, r.text
    return r.json()


async def _create_transaction(client: AsyncClient, acc_id: int, cat_id: int) -> dict:
    r = await client.post("/api/transactions", json={
        "date": str(date.today()), "kind": "gasto", "amount": 50.0,
        "account_id": acc_id, "category_id": cat_id,
    })
    assert r.status_code == 200, r.text
    return r.json()


async def _first_gasto_cat(client: AsyncClient) -> int:
    return (await client.get("/api/categories?kind=gasto")).json()[0]["id"]


async def _create_fixed_expense(client: AsyncClient) -> dict:
    from datetime import timedelta
    cat_id = await _first_gasto_cat(client)
    accounts = (await client.get("/api/accounts")).json()
    acc_id = next(a["id"] for a in accounts if a["is_cash"])
    past = date.today() - timedelta(days=35)
    r = await client.post("/api/fixed-expenses", json={
        "name": "Gasto Privado", "category_id": cat_id, "account_id": acc_id,
        "estimated_amount": 100.0, "is_variable_amount": False,
        "frequency": "mensual", "due_day": past.day,
        "auto_post": False, "start_date": past.isoformat(),
    })
    assert r.status_code == 200, r.text
    return r.json()


async def _create_budget(client: AsyncClient) -> dict:
    cat_id = await _first_gasto_cat(client)
    r = await client.post("/api/budgets", json={
        "name": "Presupuesto Privado", "period_type": "mensual",
        "start_date": str(date.today().replace(day=1)),
        "items": [{"category_id": cat_id, "planned_amount": 500.0}],
    })
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Cuentas
# ---------------------------------------------------------------------------

async def test_get_cuenta_ajena_retorna_404(two_auth_clients):
    ca, cb = two_auth_clients
    acc_a = await _create_account(ca)
    r = await cb.put(f"/api/accounts/{acc_a['id']}", json={"name": "Hack"})
    assert r.status_code == 404


async def test_put_cuenta_ajena_retorna_404(two_auth_clients):
    ca, cb = two_auth_clients
    acc_a = await _create_account(ca)
    r = await cb.put(f"/api/accounts/{acc_a['id']}", json={"name": "Hack"})
    assert r.status_code == 404


async def test_delete_cuenta_ajena_retorna_404(two_auth_clients):
    ca, cb = two_auth_clients
    acc_a = await _create_account(ca)
    r = await cb.delete(f"/api/accounts/{acc_a['id']}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Transacciones
# ---------------------------------------------------------------------------

async def test_listado_transacciones_no_incluye_ajenas(two_auth_clients):
    ca, cb = two_auth_clients
    acc_a = await _create_account(ca)
    cat_id_a = await _first_gasto_cat(ca)
    txn_a = await _create_transaction(ca, acc_a["id"], cat_id_a)

    r = await cb.get("/api/transactions")
    txn_ids = [t["id"] for t in r.json()]
    assert txn_a["id"] not in txn_ids


async def test_put_transaccion_ajena_retorna_404(two_auth_clients):
    ca, cb = two_auth_clients
    acc_a = await _create_account(ca)
    cat_id_a = await _first_gasto_cat(ca)
    txn_a = await _create_transaction(ca, acc_a["id"], cat_id_a)

    r = await cb.put(f"/api/transactions/{txn_a['id']}", json={
        "date": str(date.today()), "kind": "gasto", "amount": 999.0,
        "account_id": acc_a["id"], "category_id": cat_id_a,
    })
    assert r.status_code == 404


async def test_delete_transaccion_ajena_retorna_404(two_auth_clients):
    ca, cb = two_auth_clients
    acc_a = await _create_account(ca)
    cat_id_a = await _first_gasto_cat(ca)
    txn_a = await _create_transaction(ca, acc_a["id"], cat_id_a)

    r = await cb.delete(f"/api/transactions/{txn_a['id']}")
    assert r.status_code == 404


async def test_crear_transaccion_con_categoria_ajena_retorna_400(two_auth_clients):
    ca, cb = two_auth_clients
    cat_id_a = await _first_gasto_cat(ca)
    accounts_b = (await cb.get("/api/accounts")).json()
    acc_b_id = next(a["id"] for a in accounts_b if a["is_cash"])

    r = await cb.post("/api/transactions", json={
        "date": str(date.today()), "kind": "gasto", "amount": 50.0,
        "account_id": acc_b_id, "category_id": cat_id_a,
    })
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Gastos fijos
# ---------------------------------------------------------------------------

async def test_listado_gastos_fijos_no_incluye_ajenos(two_auth_clients):
    ca, cb = two_auth_clients
    fe_a = await _create_fixed_expense(ca)

    r = await cb.get("/api/fixed-expenses")
    fe_ids = [f["id"] for f in r.json()]
    assert fe_a["id"] not in fe_ids


async def test_confirmar_ocurrencia_ajena_retorna_404(two_auth_clients):
    ca, cb = two_auth_clients
    await _create_fixed_expense(ca)
    pending_a = (await ca.get("/api/fixed-expenses/occurrences/pending")).json()
    occ_a = pending_a[0]

    r = await cb.post(f"/api/fixed-expenses/occurrences/{occ_a['id']}/confirm", json={})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Presupuestos
# ---------------------------------------------------------------------------

async def test_status_presupuesto_ajeno_retorna_404(two_auth_clients):
    ca, cb = two_auth_clients
    budget_a = await _create_budget(ca)

    r = await cb.get(f"/api/budgets/{budget_a['id']}/status")
    assert r.status_code == 404


async def test_delete_presupuesto_ajeno_retorna_404(two_auth_clients):
    ca, cb = two_auth_clients
    budget_a = await _create_budget(ca)

    r = await cb.delete(f"/api/budgets/{budget_a['id']}")
    assert r.status_code == 404
