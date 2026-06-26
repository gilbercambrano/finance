## Context

Ledger·MX tiene un backend FastAPI completo (auth, cuentas, transacciones, gastos fijos, presupuestos) sin ninguna prueba automatizada. Cada cambio requiere verificación manual, los errores en la lógica de saldos (activo/pasivo) son difíciles de detectar, y no hay CI. La suite se construye como pruebas de integración puras contra PostgreSQL real, usando el TestClient de FastAPI con override de dependencia de base de datos, de manera que los tests ejercen el stack completo: routing → validación → servicio → ORM → DB.

## Goals / Non-Goals

**Goals:**
- Suite pytest ejecutable con un único comando (`pytest`) en entorno local y en GitHub Actions.
- Base de datos PostgreSQL de prueba aislada: se crea con `CREATE DATABASE finanzas_test`, se aplican las migraciones de Alembic y se destruye al terminar la sesión de tests.
- Cada módulo de prueba limpia las tablas entre tests usando transacciones que hacen rollback (fixture de función), evitando estado compartido entre casos.
- Fixtures reutilizables que crean usuarios, tokens/cookies y entidades de dominio (cuentas, categorías, transacciones, gastos fijos, presupuestos).
- Cobertura de los dominios declarados en la propuesta; output de cobertura HTML disponible con `--cov`.
- Workflow de GitHub Actions listo para integrar desde el primer push.

**Non-Goals:**
- No se escriben mocks de BD ni pruebas unitarias puras de funciones aisladas.
- No se cubre el frontend (HTML/JS) ni los endpoints de dashboard/seed en esta iteración.
- No se modifica código de producción como consecuencia directa de los tests.
- No se agrega autenticación de dos factores ni cambios en el modelo de seguridad.

## Decisions

### D1: Integración pura contra PostgreSQL real (no SQLite, no mocks)

**Decisión**: usar `psycopg` + `CREATE DATABASE finanzas_test`, misma configuración que producción.

**Alternativas consideradas**:
- SQLite en memoria: descartado porque SQLAlchemy 2.0 + `psycopg` tiene comportamientos distintos en constraints, tipos y transacciones. Los bugs que importan (saldos, unicidad, FKs) son específicos de PostgreSQL.
- Mocks de Session: descartado porque enmascara exactamente los errores que queremos detectar (lógica de ORM, cascadas, transacciones).

**Rationale**: Las pruebas de integración contra la BD real dan mayor confianza con casi el mismo esfuerzo de setup. El overhead de tiempo es bajo (< 30 s para la suite completa proyectada).

---

### D2: Rollback por transacción en fixture de función (no truncate)

**Decisión**: cada test corre dentro de una transacción de SQLAlchemy que hace rollback al finalizar. La conexión de la BD de prueba se abre al inicio de la sesión y se comparte entre tests.

**Alternativas consideradas**:
- `TRUNCATE` o `DELETE` entre tests: más lento y propenso a problemas de orden de ejecución con FKs.
- Base de datos nueva por test: demasiado lento para una suite grande.

**Rationale**: El patrón de rollback es el estándar recomendado por SQLAlchemy para tests; garantiza limpieza perfecta sin costo de I/O adicional.

---

### D3: Override de `get_db` en FastAPI para inyectar la sesión de test

**Decisión**: usar `app.dependency_overrides[get_db] = override_get_db` en cada fixture de cliente HTTP. La función `override_get_db` retorna la misma sesión anclada a la transacción de rollback.

**Rationale**: Es el mecanismo oficial de FastAPI para sustituir dependencias en tests. Permite usar `httpx.AsyncClient` contra el app real sin levantar un servidor.

---

### D4: `httpx.AsyncClient` + `pytest-asyncio` en modo síncrono con `anyio`

**Decisión**: usar `AsyncClient(transport=ASGITransport(app=app))` para simular requests HTTP completos.

**Alternativas consideradas**:
- `TestClient` síncrono de Starlette: suficiente para la mayoría de endpoints, pero no cubre rutas `async def` de manera fiel. `httpx.AsyncClient` es la opción recomendada por FastAPI en su documentación de testing.

---

### D5: `requirements-dev.txt` separado (sin modificar la imagen de producción)

**Decisión**: agregar `pytest`, `pytest-asyncio`, `httpx`, `pytest-cov` solo en `api/requirements-dev.txt`.

**Rationale**: El `Dockerfile` de producción usa `requirements.txt`; las dependencias de test no deben inflar la imagen ni crear vectores de ataque en producción.

---

### D6: GitHub Actions con servicio PostgreSQL oficial

**Decisión**: usar `services: postgres:` en el workflow YAML, configurar `DATABASE_TEST_URL` como variable de entorno del job.

**Rationale**: Es el patrón estándar para tests de integración en GH Actions. No requiere Docker-in-Docker ni configuración adicional de infraestructura.

---

### D7: PostgreSQL local de pruebas vía Docker Compose (puerto 5433)

**Decisión**: agregar `docker-compose.test.yml` en la raíz del repositorio con un servicio `postgres:16` en el puerto 5433. Antes de correr pytest localmente se levanta con:

```bash
docker compose -f docker-compose.test.yml up -d
```

Y se detiene con:

```bash
docker compose -f docker-compose.test.yml down -v
```

**Alternativas consideradas**:
- Homebrew (`brew services start postgresql`): descartado porque no está disponible en todos los entornos (Linux, CI sin Homebrew), no garantiza la versión exacta de PostgreSQL, y comparte el puerto 5432 con la BD de desarrollo.
- Reutilizar el servicio `db` del `docker-compose.yml` existente: descartado para evitar que una ejecución de tests accidentalmente afecte datos de desarrollo.

**Rationale**: Docker Compose garantiza la misma versión (`postgres:16`) en todos los entornos (macOS, Linux, CI) y el puerto diferenciado (5433 vs 5432) elimina conflictos. El fixture de sesión de pytest usa la URL `postgresql+psycopg://postgres:postgres@localhost:5433/finanzas_test`.

## Risks / Trade-offs

- **[Riesgo] Tests lentos si la suite crece sin disciplina** → Mitigación: mantener el patrón de rollback, no usar `db.commit()` dentro de fixtures de función. Revisar duración en cada PR.
- **[Riesgo] La BD de prueba queda sucia si el proceso muere abruptamente** → Mitigación: el fixture de sesión hace `DROP DATABASE finanzas_test` con `IF EXISTS`; puede correrse manualmente o al inicio del siguiente `pytest`.
- **[Riesgo] `auto_post` en gastos fijos depende de `date.today()`** → Mitigación: los tests de sincronización inyectan fechas explícitas usando el parámetro `today=` de `services.sync_fixed_expense`.
- **[Trade-off] Rollback por transacción no prueba `ON COMMIT` triggers ni lógica que dependa de commits reales** → Aceptable: Ledger·MX no usa triggers de BD; toda la lógica está en Python.

## Migration Plan

1. Crear `docker-compose.test.yml` con servicio `postgres:16` en puerto 5433; levantar con `docker compose -f docker-compose.test.yml up -d` antes de correr pytest localmente.
2. Agregar `api/requirements-dev.txt` con dependencias de test.
3. Crear `api/conftest.py` con fixtures de sesión de BD, rollback por test y cliente HTTP.
4. Crear `api/tests/` con módulos `test_auth.py`, `test_accounts.py`, `test_categories.py`, `test_transactions.py`, `test_fixed_expenses.py`, `test_budgets.py`, `test_isolation.py`.
5. Agregar `api/pytest.ini` con configuración de asyncio mode y rutas.
6. Agregar `.github/workflows/tests.yml`.
7. Verificar que `pytest` pasa en local antes de hacer push.

No hay rollback necesario: este cambio solo agrega archivos nuevos, no modifica código de producción.

## Open Questions

- ¿Se genera HTML de cobertura como artefacto en GitHub Actions, o solo el resumen en consola? (Decisión de conveniencia; se puede agregar después.)
