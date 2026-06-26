import pytest
from httpx import AsyncClient


async def test_crear_categoria_ingreso(auth_client: AsyncClient):
    r = await auth_client.post("/api/categories", json={
        "name": "Freelance", "kind": "ingreso", "group": "variable",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["kind"] == "ingreso"
    assert data["name"] == "Freelance"
    assert data["is_active"] is True


async def test_crear_categoria_gasto(auth_client: AsyncClient):
    r = await auth_client.post("/api/categories", json={
        "name": "Viajes", "kind": "gasto", "group": "variable",
    })
    assert r.status_code == 200
    assert r.json()["kind"] == "gasto"


async def test_crear_categoria_kind_invalido(auth_client: AsyncClient):
    r = await auth_client.post("/api/categories", json={
        "name": "Mala", "kind": "otro", "group": "variable",
    })
    assert r.status_code == 400


async def test_listado_solo_activas_del_usuario(auth_client: AsyncClient):
    r = await auth_client.get("/api/categories")
    assert r.status_code == 200
    cats = r.json()
    assert len(cats) > 0
    assert all(c["is_active"] for c in cats)


async def test_filtro_kind_ingreso(auth_client: AsyncClient):
    r = await auth_client.get("/api/categories?kind=ingreso")
    assert r.status_code == 200
    cats = r.json()
    assert len(cats) > 0
    assert all(c["kind"] == "ingreso" for c in cats)


async def test_filtro_kind_gasto(auth_client: AsyncClient):
    r = await auth_client.get("/api/categories?kind=gasto")
    assert r.status_code == 200
    cats = r.json()
    assert len(cats) > 0
    assert all(c["kind"] == "gasto" for c in cats)


async def test_delete_desactiva_categoria(auth_client: AsyncClient):
    r_create = await auth_client.post("/api/categories", json={
        "name": "Temporal", "kind": "gasto", "group": "otros",
    })
    cat_id = r_create.json()["id"]
    r = await auth_client.delete(f"/api/categories/{cat_id}")
    assert r.status_code == 200
    # Should not appear in active list
    cats = (await auth_client.get("/api/categories")).json()
    assert cat_id not in [c["id"] for c in cats]


async def test_delete_categoria_ajena_retorna_404(two_auth_clients):
    ca, cb = two_auth_clients
    r_create = await ca.post("/api/categories", json={
        "name": "De A", "kind": "gasto", "group": "otros",
    })
    cat_id = r_create.json()["id"]
    r = await cb.delete(f"/api/categories/{cat_id}")
    assert r.status_code == 404
