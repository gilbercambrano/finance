from datetime import date
from httpx import AsyncClient


async def _first_gasto_cat(client: AsyncClient) -> int:
    return (await client.get("/api/categories?kind=gasto")).json()[0]["id"]


async def _create_budget(client: AsyncClient, cat_id: int, planned: float = 1000.0) -> dict:
    r = await client.post("/api/budgets", json={
        "name": "Presupuesto Test",
        "period_type": "mensual",
        "start_date": str(date.today().replace(day=1)),
        "items": [{"category_id": cat_id, "planned_amount": planned}],
    })
    assert r.status_code == 200, r.text
    return r.json()


async def test_crear_presupuesto_con_items(auth_client: AsyncClient):
    cat_id = await _first_gasto_cat(auth_client)
    budget = await _create_budget(auth_client, cat_id)
    assert budget["period_type"] == "mensual"
    assert len(budget["items"]) == 1
    assert budget["items"][0]["planned_amount"] == 1000.0


async def test_crear_presupuesto_sin_items_retorna_400(auth_client: AsyncClient):
    r = await auth_client.post("/api/budgets", json={
        "name": "Vacio",
        "period_type": "mensual",
        "start_date": str(date.today().replace(day=1)),
        "items": [],
    })
    assert r.status_code == 400


async def test_status_sin_transacciones(auth_client: AsyncClient):
    cat_id = await _first_gasto_cat(auth_client)
    budget = await _create_budget(auth_client, cat_id, planned=500.0)
    r = await auth_client.get(f"/api/budgets/{budget['id']}/status")
    assert r.status_code == 200
    data = r.json()
    item = data["items"][0]
    assert item["actual_amount"] == 0.0
    assert item["deviation"] == -500.0
    assert item["status"] == "ok"


async def test_status_gasto_supera_planificado_marca_alerta(auth_client: AsyncClient):
    cat_id = await _first_gasto_cat(auth_client)
    budget = await _create_budget(auth_client, cat_id, planned=100.0)

    # Post a transaction that exceeds the planned amount
    accounts = (await auth_client.get("/api/accounts")).json()
    acc_id = next(a["id"] for a in accounts if a["is_cash"])
    await auth_client.post("/api/transactions", json={
        "date": str(date.today()),
        "kind": "gasto",
        "amount": 150.0,
        "account_id": acc_id,
        "category_id": cat_id,
    })

    r = await auth_client.get(f"/api/budgets/{budget['id']}/status")
    item = r.json()["items"][0]
    assert item["actual_amount"] == 150.0
    assert item["deviation"] == 50.0
    assert item["status"] == "alerta"


async def test_status_totales_correctos(auth_client: AsyncClient):
    cats = (await auth_client.get("/api/categories?kind=gasto")).json()
    cat1_id, cat2_id = cats[0]["id"], cats[1]["id"]
    r = await auth_client.post("/api/budgets", json={
        "name": "Dos Categorias",
        "period_type": "mensual",
        "start_date": str(date.today().replace(day=1)),
        "items": [
            {"category_id": cat1_id, "planned_amount": 400.0},
            {"category_id": cat2_id, "planned_amount": 600.0},
        ],
    })
    budget = r.json()
    data = (await auth_client.get(f"/api/budgets/{budget['id']}/status")).json()
    assert data["total_planned"] == 1000.0
    assert data["total_actual"] == 0.0
    assert data["total_deviation"] == -1000.0


async def test_delete_presupuesto_lo_desactiva(auth_client: AsyncClient):
    cat_id = await _first_gasto_cat(auth_client)
    budget = await _create_budget(auth_client, cat_id)
    r = await auth_client.delete(f"/api/budgets/{budget['id']}")
    assert r.status_code == 200
    # Should not appear in active list
    active = (await auth_client.get("/api/budgets")).json()
    assert budget["id"] not in [b["id"] for b in active]
