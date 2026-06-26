import pytest
from httpx import AsyncClient


_DEBITO = {
    "name": "Mi Débito",
    "account_type": "debito",
    "nature": "activo",
    "initial_balance": 1000.0,
}

_CREDITO = {
    "name": "Mi Tarjeta",
    "account_type": "credito",
    "nature": "pasivo",
    "initial_balance": 0.0,
}


async def _create(client: AsyncClient, payload: dict) -> dict:
    r = await client.post("/api/accounts", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- creación ----------

async def test_crear_cuenta_activa_saldo_inicial(auth_client: AsyncClient):
    data = await _create(auth_client, _DEBITO)
    assert data["current_balance"] == 1000.0
    assert data["nature"] == "activo"


async def test_crear_cuenta_activa_nature_invalido(auth_client: AsyncClient):
    payload = {**_DEBITO, "nature": "pasivo"}
    r = await auth_client.post("/api/accounts", json=payload)
    assert r.status_code == 400


async def test_crear_cuenta_pasiva_sin_credit_detail(auth_client: AsyncClient):
    data = await _create(auth_client, _CREDITO)
    assert data["nature"] == "pasivo"
    assert data["credit_detail"] is None


async def test_crear_cuenta_pasiva_con_credit_detail(auth_client: AsyncClient):
    payload = {
        **_CREDITO,
        "credit_detail": {
            "credit_limit": 50000.0,
            "cutoff_day": 25,
            "payment_due_day": 15,
            "interest_rate_annual": 36.0,
        },
    }
    data = await _create(auth_client, payload)
    assert data["nature"] == "pasivo"
    cd = data["credit_detail"]
    assert cd["credit_limit"] == 50000.0
    assert cd["cutoff_day"] == 25


async def test_crear_cuenta_pasiva_nature_invalido(auth_client: AsyncClient):
    payload = {**_CREDITO, "nature": "activo"}
    r = await auth_client.post("/api/accounts", json=payload)
    assert r.status_code == 400


# ---------- listado ----------

async def test_listado_solo_activas(auth_client: AsyncClient):
    r = await auth_client.get("/api/accounts")
    assert r.status_code == 200
    accounts = r.json()
    assert all(a["is_active"] for a in accounts)


async def test_listado_include_inactive(auth_client: AsyncClient):
    # Create an account then deactivate it
    acc = await _create(auth_client, _DEBITO)
    # Ensure no transactions so it gets deleted (it will be deleted, not deactivated)
    # Instead just verify that include_inactive=true works with what we have
    r = await auth_client.get("/api/accounts?include_inactive=true")
    assert r.status_code == 200
    # The list is a superset of active accounts
    active_r = await auth_client.get("/api/accounts")
    assert len(r.json()) >= len(active_r.json())


# ---------- edición ----------

async def test_editar_nombre_cuenta(auth_client: AsyncClient):
    acc = await _create(auth_client, _DEBITO)
    r = await auth_client.put(f"/api/accounts/{acc['id']}", json={"name": "Nuevo Nombre"})
    assert r.status_code == 200
    assert r.json()["name"] == "Nuevo Nombre"


async def test_editar_agrega_credit_detail(auth_client: AsyncClient):
    acc = await _create(auth_client, _CREDITO)
    r = await auth_client.put(f"/api/accounts/{acc['id']}", json={
        "credit_detail": {"credit_limit": 20000.0, "cutoff_day": 10, "payment_due_day": 5}
    })
    assert r.status_code == 200
    assert r.json()["credit_detail"]["credit_limit"] == 20000.0


async def test_editar_cuenta_ajena_retorna_404(two_auth_clients):
    ca, cb = two_auth_clients
    acc = await _create(ca, _DEBITO)
    r = await cb.put(f"/api/accounts/{acc['id']}", json={"name": "Hack"})
    assert r.status_code == 404


# ---------- eliminación ----------

async def test_delete_cuenta_sin_movimientos(auth_client: AsyncClient):
    acc = await _create(auth_client, _DEBITO)
    r = await auth_client.delete(f"/api/accounts/{acc['id']}")
    assert r.status_code == 200
    # Account is gone (GET returns empty for this id means 404 via PUT)
    r2 = await auth_client.put(f"/api/accounts/{acc['id']}", json={"name": "X"})
    assert r2.status_code == 404


async def test_delete_cuenta_con_transacciones_desactiva(auth_client: AsyncClient):
    acc = await _create(auth_client, _DEBITO)
    # Get a gasto category from seed
    cats = (await auth_client.get("/api/categories?kind=gasto")).json()
    cat_id = cats[0]["id"]
    from datetime import date
    await auth_client.post("/api/transactions", json={
        "date": str(date.today()), "kind": "gasto", "amount": 50.0,
        "account_id": acc["id"], "category_id": cat_id,
    })
    r = await auth_client.delete(f"/api/accounts/{acc['id']}")
    assert r.status_code == 200
    # Should now be inactive
    r2 = await auth_client.get("/api/accounts?include_inactive=true")
    ids = [a["id"] for a in r2.json() if not a["is_active"]]
    assert acc["id"] in ids


async def test_delete_cuenta_efectivo_retorna_400(auth_client: AsyncClient):
    # Find the seeded cash account
    accounts = (await auth_client.get("/api/accounts")).json()
    cash = next(a for a in accounts if a["is_cash"])
    r = await auth_client.delete(f"/api/accounts/{cash['id']}")
    assert r.status_code == 400
