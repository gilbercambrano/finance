## Why

El backend de Ledger·MX carece de pruebas automatizadas, lo que hace que cada cambio en la lógica de saldos, aislamiento de datos o flujos de gastos fijos dependa de verificación manual. Agregar una suite de integración con pytest sobre PostgreSQL real elimina esa brecha y hace posible integrar CI (GitHub Actions) sin riesgos.

## What Changes

- Se agrega la suite de pruebas `api/tests/` con pytest + httpx AsyncClient contra una base de datos PostgreSQL de prueba aislada (creada y destruida por fixture de sesión).
- Se añaden dependencias de desarrollo (`pytest`, `pytest-asyncio`, `httpx`, `pytest-cov`) al proyecto.
- Se agrega `docker-compose.test.yml` con un servicio `postgres:16` dedicado exclusivamente a pruebas, en el puerto 5433 (sin conflicto con el puerto 5432 de desarrollo/producción).
- Se agrega archivo `api/conftest.py` con fixtures reutilizables: DB de prueba, cliente HTTP autenticado por usuario, factories de entidades.
- Se agrega `api/pytest.ini` / `pyproject.toml` de configuración de pytest.
- Se documentan las specs de los dominios existentes (auth, cuentas, categorías, transacciones, gastos fijos, presupuestos, aislamiento de datos) que las pruebas verificarán.
- Se agrega workflow `.github/workflows/tests.yml` para ejecutar la suite en GitHub Actions con PostgreSQL de servicio.

## Capabilities

### New Capabilities

- `auth`: Registro, login, logout y protección de sesión mediante JWT en cookie httpOnly. Cada usuario accede solo a su sesión.
- `accounts`: CRUD de cuentas bancarias (débito, ahorro, efectivo, inversión, préstamo otorgado) y pasivas (tarjeta de crédito, préstamo recibido), incluyendo la gestión del detalle de deuda (`CreditDetail`).
- `categories`: CRUD de categorías de ingreso y gasto del usuario; listado filtrable por `kind`, creación y desactivación.
- `transactions`: CRUD de transacciones (ingreso, gasto, transferencia) con efecto correcto sobre `current_balance` según la naturaleza activo/pasivo de la cuenta involucrada.
- `fixed-expenses`: Gastos fijos recurrentes: creación, sincronización de ocurrencias por fecha, confirmación manual con monto/cuenta variables, omisión, y auto-post para montos fijos.
- `budgets`: Presupuestos por periodo con ítems por categoría; cálculo de monto real, desviación absoluta y porcentual por ítem y total.
- `user-data-isolation`: Garantía de que un usuario nunca puede leer ni modificar cuentas, transacciones, categorías, gastos fijos ni ocurrencias de otro usuario (retorna 404, nunca 403 ni datos cruzados).
- `test-infrastructure`: Configuración de pytest, fixtures de base de datos de prueba PostgreSQL aislada, factories de entidades y workflow de GitHub Actions.

### Modified Capabilities

## Impact

- **Archivos nuevos**: `docker-compose.test.yml`, `api/tests/` (módulos de prueba por dominio), `api/conftest.py`, `api/pytest.ini`, `.github/workflows/tests.yml`.
- **Dependencias**: se agregan `pytest`, `pytest-asyncio`, `httpx`, `pytest-cov` a `requirements-dev.txt` (archivo nuevo, no afecta imagen de producción).
- **Sin cambios en código de producción**: los tests solo leen y llaman al código existente; no se modifica ningún router, modelo ni servicio.
- **Base de datos**: la suite usa una BD PostgreSQL separada (`finanzas_test`) creada por fixture; no toca la BD de desarrollo ni producción.

## Consideraciones de seguridad (OWASP Top 10)

Las pruebas verifican controles existentes pero no introducen superficie nueva de ataque. Aplican como áreas a verificar:

- **A01 Broken Access Control**: los tests de aislamiento de datos confirman explícitamente que los recursos de usuario A son inaccesibles para usuario B (endpoint devuelve 404).
- **A07 Identification and Authentication Failures**: los tests de auth verifican que sin cookie válida se retorna 401, y que logout invalida la sesión del lado del cliente.

No se introducen cambios en la lógica de autenticación ni en el manejo de dinero/saldos; los tests son solo lectores y ejecutores del código existente.

## Non-goals

- No se agregan pruebas unitarias puras (mocks de BD); la suite es 100 % de integración contra PostgreSQL real.
- No se cubren endpoints de dashboard ni seed data en esta iteración.
- No se implementan pruebas de carga o performance.
- No se modifica la lógica de producción como consecuencia de este cambio.
- No se agrega cobertura de la capa frontend (HTML/JS).
