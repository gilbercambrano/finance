import pytest
from httpx import AsyncClient


async def test_registro_exitoso(client: AsyncClient):
    r = await client.post("/api/auth/register", json={
        "email": "nuevo@test.com",
        "password": "Test1234!",
        "full_name": "Nuevo Usuario",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "nuevo@test.com"
    assert data["full_name"] == "Nuevo Usuario"
    assert "access_token" in r.cookies


async def test_registro_email_duplicado(client: AsyncClient):
    payload = {"email": "dup@test.com", "password": "Test1234!"}
    await client.post("/api/auth/register", json=payload)
    r = await client.post("/api/auth/register", json=payload)
    assert r.status_code == 400


async def test_registro_normaliza_email(client: AsyncClient):
    r = await client.post("/api/auth/register", json={
        "email": "MAYUS@TEST.COM",
        "password": "Test1234!",
    })
    assert r.status_code == 200
    assert r.json()["email"] == "mayus@test.com"


async def test_login_correcto(client: AsyncClient):
    await client.post("/api/auth/register", json={"email": "login@test.com", "password": "Test1234!"})
    # clear cookie to test login independently
    client.cookies.clear()
    r = await client.post("/api/auth/login", json={"email": "login@test.com", "password": "Test1234!"})
    assert r.status_code == 200
    assert "access_token" in r.cookies


async def test_login_contrasena_incorrecta(client: AsyncClient):
    await client.post("/api/auth/register", json={"email": "wrongpw@test.com", "password": "Test1234!"})
    client.cookies.clear()
    r = await client.post("/api/auth/login", json={"email": "wrongpw@test.com", "password": "MalContrasena"})
    assert r.status_code == 401


async def test_login_email_inexistente(client: AsyncClient):
    r = await client.post("/api/auth/login", json={"email": "noexiste@test.com", "password": "Test1234!"})
    assert r.status_code == 401


async def test_logout_elimina_cookie(auth_client: AsyncClient):
    r = await auth_client.post("/api/auth/logout")
    assert r.status_code == 200
    # cookie should be cleared (value empty or absent)
    assert auth_client.cookies.get("access_token") is None or r.headers.get("set-cookie", "").find("access_token=;") != -1


async def test_me_sin_cookie_retorna_401(client: AsyncClient):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401


async def test_me_con_cookie_retorna_usuario(auth_client: AsyncClient):
    r = await auth_client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "user@test.com"
