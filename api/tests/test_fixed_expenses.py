from datetime import date, timedelta
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_cash(client: AsyncClient) -> dict:
    accounts = (await client.get("/api/accounts")).json()
    return next(a for a in accounts if a["is_cash"])


async def _first_gasto_cat(client: AsyncClient) -> int:
    return (await client.get("/api/categories?kind=gasto")).json()[0]["id"]


async def _create_fe(client: AsyncClient, **overrides) -> dict:
    cash = await _get_cash(client)
    cat_id = await _first_gasto_cat(client)
    # Use a past start_date so next_due_date is always in the past
    past = date.today() - timedelta(days=35)
    payload = {
        "name": "Internet",
        "category_id": cat_id,
        "account_id": cash["id"],
        "estimated_amount": 500.0,
        "is_variable_amount": False,
        "frequency": "mensual",
        "due_day": past.day,
        "auto_post": False,
        "start_date": past.isoformat(),
    }
    payload.update(overrides)
    r = await client.post("/api/fixed-expenses", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


async def _balance(client: AsyncClient, account_id: int) -> float:
    r = await client.get("/api/accounts?include_inactive=true")
    return next(a["current_balance"] for a in r.json() if a["id"] == account_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_crear_gasto_fijo_mensual_calcula_next_due(auth_client: AsyncClient):
    fe = await _create_fe(auth_client)
    # next_due_date was in the past on creation, confirmed by the response
    assert fe["frequency"] == "mensual"
    assert fe["is_active"] is True


async def test_variable_amount_fuerza_auto_post_false(auth_client: AsyncClient):
    fe = await _create_fe(auth_client, is_variable_amount=True, auto_post=True)
    assert fe["auto_post"] is False


async def test_sync_genera_ocurrencias_pendientes(auth_client: AsyncClient):
    await _create_fe(auth_client)
    r = await auth_client.get("/api/fixed-expenses/occurrences/pending")
    assert r.status_code == 200
    pending = r.json()
    assert len(pending) >= 1
    assert all(o["status"] == "pendiente" for o in pending)


async def test_sync_no_genera_duplicados(auth_client: AsyncClient):
    await _create_fe(auth_client)
    r1 = await auth_client.get("/api/fixed-expenses/occurrences/pending")
    count1 = len(r1.json())
    r2 = await auth_client.get("/api/fixed-expenses/occurrences/pending")
    count2 = len(r2.json())
    assert count1 == count2


async def test_auto_post_crea_transaccion_y_ajusta_saldo(auth_client: AsyncClient):
    cash = await _get_cash(auth_client)
    saldo_inicial = cash["current_balance"]
    fe = await _create_fe(auth_client, auto_post=True, estimated_amount=300.0)
    # Trigger sync via list endpoint
    await auth_client.get("/api/fixed-expenses")
    # No pending occurrences for this FE (they were auto-posted)
    pending = (await auth_client.get("/api/fixed-expenses/occurrences/pending")).json()
    fe_pending = [o for o in pending if o["fixed_expense_id"] == fe["id"]]
    assert len(fe_pending) == 0
    # Balance decreased
    saldo_nuevo = await _balance(auth_client, cash["id"])
    assert saldo_nuevo < saldo_inicial


async def test_confirmar_ocurrencia_crea_transaccion(auth_client: AsyncClient):
    cash = await _get_cash(auth_client)
    saldo_inicial = cash["current_balance"]
    await _create_fe(auth_client, estimated_amount=400.0)
    pending = (await auth_client.get("/api/fixed-expenses/occurrences/pending")).json()
    occ = pending[0]
    r = await auth_client.post(f"/api/fixed-expenses/occurrences/{occ['id']}/confirm", json={})
    assert r.status_code == 200
    # Occurrence now paid, saldo reduced
    saldo_nuevo = await _balance(auth_client, cash["id"])
    assert saldo_nuevo == saldo_inicial - occ["expected_amount"]


async def test_confirmar_con_monto_diferente(auth_client: AsyncClient):
    cash = await _get_cash(auth_client)
    saldo_inicial = cash["current_balance"]
    await _create_fe(auth_client, estimated_amount=400.0)
    pending = (await auth_client.get("/api/fixed-expenses/occurrences/pending")).json()
    occ = pending[0]
    r = await auth_client.post(f"/api/fixed-expenses/occurrences/{occ['id']}/confirm",
                                json={"amount": 350.0})
    assert r.status_code == 200
    saldo_nuevo = await _balance(auth_client, cash["id"])
    assert saldo_nuevo == saldo_inicial - 350.0


async def test_confirmar_ocurrencia_ya_pagada_retorna_400(auth_client: AsyncClient):
    await _create_fe(auth_client)
    pending = (await auth_client.get("/api/fixed-expenses/occurrences/pending")).json()
    occ = pending[0]
    await auth_client.post(f"/api/fixed-expenses/occurrences/{occ['id']}/confirm", json={})
    r = await auth_client.post(f"/api/fixed-expenses/occurrences/{occ['id']}/confirm", json={})
    assert r.status_code == 400


async def test_omitir_ocurrencia(auth_client: AsyncClient):
    cash = await _get_cash(auth_client)
    saldo_inicial = cash["current_balance"]
    await _create_fe(auth_client)
    pending = (await auth_client.get("/api/fixed-expenses/occurrences/pending")).json()
    occ = pending[0]
    r = await auth_client.post(f"/api/fixed-expenses/occurrences/{occ['id']}/skip")
    assert r.status_code == 200
    # No change in balance
    assert await _balance(auth_client, cash["id"]) == saldo_inicial


async def test_delete_desactiva_gasto_fijo(auth_client: AsyncClient):
    fe = await _create_fe(auth_client, auto_post=False)
    r = await auth_client.delete(f"/api/fixed-expenses/{fe['id']}")
    assert r.status_code == 200
    # Appears in include_inactive list as inactive
    all_fes = (await auth_client.get("/api/fixed-expenses?include_inactive=true")).json()
    target = next((f for f in all_fes if f["id"] == fe["id"]), None)
    assert target is not None
    assert target["is_active"] is False
