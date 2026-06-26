## 1. Infraestructura de pruebas

- [x] 1.0 Crear `docker-compose.test.yml` en la raíz del repositorio con un servicio `postgres:16` en puerto 5433 (distinto al 5432 de desarrollo); levantar con `docker compose -f docker-compose.test.yml up -d` antes de correr pytest localmente
- [x] 1.1 Crear `api/requirements-dev.txt` con `pytest`, `pytest-asyncio`, `httpx`, `pytest-cov` y `python-dotenv`
- [x] 1.2 Crear `api/pytest.ini` con `asyncio_mode = auto`, `testpaths = tests`, y la cadena de conexión a la BD de prueba vía variable de entorno
- [x] 1.3 Crear `api/conftest.py` con fixture de sesión (`scope="session"`) que crea la BD `finanzas_test`, aplica migraciones de Alembic y la elimina al terminar
- [x] 1.4 Agregar fixture de función en `conftest.py` que abre una transacción SQLAlchemy por test y hace rollback al finalizar, con override de `get_db` en el app de FastAPI
- [x] 1.5 Agregar fixture `async_client` (sin auth) y factory de usuarios con helper `create_user(db, email, password)` en `conftest.py`
- [x] 1.6 Agregar fixture `auth_client_a` y `auth_client_b` (dos usuarios distintos autenticados) para los tests de aislamiento
- [x] 1.7 Verificar que `pytest --collect-only` no arroja errores y que la BD se crea y destruye correctamente

## 2. Tests de autenticación (`api/tests/test_auth.py`)

- [x] 2.1 Test: registro exitoso → 200, devuelve `email` y `full_name`, cookie `access_token` presente
- [x] 2.2 Test: registro con email duplicado → 400
- [x] 2.3 Test: registro normaliza email a minúsculas
- [x] 2.4 Test: login correcto → 200, cookie presente
- [x] 2.5 Test: login con contraseña incorrecta → 401
- [x] 2.6 Test: login con email inexistente → 401
- [x] 2.7 Test: logout elimina la cookie (cookie ausente en respuesta)
- [x] 2.8 Test: GET `/api/auth/me` sin cookie → 401
- [x] 2.9 Test: GET `/api/auth/me` con cookie válida → 200 con datos del usuario correcto

## 3. Tests de cuentas (`api/tests/test_accounts.py`)

- [x] 3.1 Test: crear cuenta activa (débito) con `initial_balance` → `current_balance` igual al inicial
- [x] 3.2 Test: crear cuenta activa con `nature="pasivo"` → 400
- [x] 3.3 Test: crear cuenta pasiva (crédito) sin `credit_detail` → 200
- [x] 3.4 Test: crear cuenta pasiva con `credit_detail` completo → 200, detalle persistido
- [x] 3.5 Test: crear cuenta pasiva (crédito) con `nature="activo"` → 400
- [x] 3.6 Test: GET `/api/accounts` devuelve solo cuentas activas del usuario
- [x] 3.7 Test: GET `/api/accounts?include_inactive=true` incluye cuentas inactivas
- [x] 3.8 Test: PUT edita nombre de cuenta propia → 200
- [x] 3.9 Test: PUT agrega `credit_detail` en edición de cuenta pasiva → 200, detalle persistido
- [x] 3.10 Test: DELETE cuenta sin movimientos → 200, cuenta eliminada físicamente
- [x] 3.11 Test: DELETE cuenta con transacciones → 200, cuenta queda `is_active=false`
- [x] 3.12 Test: DELETE cuenta de efectivo → 400

## 4. Tests de categorías (`api/tests/test_categories.py`)

- [x] 4.1 Test: crear categoría de tipo `ingreso` → 200, datos persistidos con `kind="ingreso"`
- [x] 4.2 Test: crear categoría de tipo `gasto` → 200, datos persistidos con `kind="gasto"`
- [x] 4.3 Test: crear categoría con `kind` inválido → 400
- [x] 4.4 Test: GET `/api/categories` devuelve solo categorías activas del usuario autenticado
- [x] 4.5 Test: GET `/api/categories?kind=ingreso` devuelve solo categorías de ingreso
- [x] 4.6 Test: GET `/api/categories?kind=gasto` devuelve solo categorías de gasto
- [x] 4.7 Test: DELETE `/api/categories/{id}` desactiva la categoría (`is_active=false`)
- [x] 4.8 Test: DELETE categoría de otro usuario → 404

## 5. Tests de transacciones (`api/tests/test_transactions.py`)

- [x] 5.1 Test: ingreso en cuenta activa incrementa `current_balance`
- [x] 5.2 Test: ingreso en cuenta pasiva decrementa `current_balance` (abono a deuda)
- [x] 5.3 Test: gasto en cuenta activa decrementa `current_balance`
- [x] 5.4 Test: gasto en tarjeta de crédito (pasiva) incrementa `current_balance`
- [x] 5.5 Test: transferencia entre dos cuentas activas ajusta ambos saldos correctamente
- [x] 5.6 Test: transferencia de cuenta activa a pasiva (pago de tarjeta) reduce activo y reduce saldo pasivo
- [x] 5.7 Test: ingreso sin `category_id` → 400
- [x] 5.8 Test: gasto con categoría de tipo `ingreso` → 400
- [x] 5.9 Test: transferencia con `account_id == to_account_id` → 400
- [x] 5.10 Test: PUT edita monto de gasto → saldos corregidos sin doble contabilidad
- [x] 5.11 Test: DELETE ingreso → saldo revierte al valor anterior
- [x] 5.12 Test: DELETE transferencia → ambos saldos revierten
- [x] 5.13 Test: GET `/api/transactions?account_id=` filtra correctamente

## 6. Tests de gastos fijos (`api/tests/test_fixed_expenses.py`)

- [x] 6.1 Test: crear gasto fijo mensual → `next_due_date` calculado correctamente (próximo `due_day`)
- [x] 6.2 Test: crear gasto fijo con `is_variable_amount=true` y `auto_post=true` → `auto_post` queda `false`
- [x] 6.3 Test: GET `/api/fixed-expenses` con `next_due_date` en el pasado → ocurrencias `pendiente` generadas
- [x] 6.4 Test: consultar ocurrencias pendientes dos veces → no hay duplicados
- [x] 6.5 Test: gasto fijo con `auto_post=true`, `next_due_date` <= hoy → ocurrencia `pagado`, transacción creada, saldo ajustado (inyectar fecha con `today=` en `sync_fixed_expense`)
- [x] 6.6 Test: confirmar ocurrencia pendiente sin payload → transacción por `expected_amount`, ocurrencia `pagado`, saldo ajustado
- [x] 6.7 Test: confirmar ocurrencia con `amount` diferente → transacción por el monto indicado
- [x] 6.8 Test: confirmar ocurrencia ya `pagado` → 400
- [x] 6.9 Test: omitir ocurrencia → `status="omitido"`, sin transacción creada
- [x] 6.10 Test: DELETE gasto fijo → `is_active=false`

## 7. Tests de presupuestos (`api/tests/test_budgets.py`)

- [x] 7.1 Test: crear presupuesto mensual con ítems → 200, ítems persistidos
- [x] 7.2 Test: crear presupuesto con `items=[]` → 400
- [x] 7.3 Test: GET `/api/budgets/{id}/status` sin transacciones → `actual_amount=0`, `deviation < 0`, `status="ok"` en todos los ítems
- [x] 7.4 Test: GET `/api/budgets/{id}/status` con gasto que supera el planificado → ítem con `status="alerta"` y `deviation > 0`
- [x] 7.5 Test: totales del presupuesto son suma correcta de ítems (`total_planned`, `total_actual`, `total_deviation`)
- [x] 7.6 Test: DELETE presupuesto → `is_active=false`

## 8. Tests de aislamiento de datos (`api/tests/test_isolation.py`)

- [x] 8.1 Test: GET cuenta del usuario A con sesión del usuario B → 404
- [x] 8.2 Test: PUT cuenta del usuario A con sesión del usuario B → 404
- [x] 8.3 Test: DELETE cuenta del usuario A con sesión del usuario B → 404
- [x] 8.4 Test: GET `/api/transactions` del usuario B no incluye transacciones del usuario A
- [x] 8.5 Test: PUT transacción del usuario A con sesión del usuario B → 404
- [x] 8.6 Test: DELETE transacción del usuario A con sesión del usuario B → 404
- [x] 8.7 Test: crear transacción con `category_id` del usuario A usando sesión del usuario B → 400
- [x] 8.8 Test: GET `/api/fixed-expenses` del usuario B no incluye gastos fijos del usuario A
- [x] 8.9 Test: confirmar ocurrencia del usuario A con sesión del usuario B → 404
- [x] 8.10 Test: GET `/api/budgets/{id}/status` del usuario A con sesión del usuario B → 404
- [x] 8.11 Test: DELETE presupuesto del usuario A con sesión del usuario B → 404

## 9. GitHub Actions CI

- [x] 9.1 Crear `.github/workflows/tests.yml` con servicio `postgres:16`, variables de entorno de BD de prueba, instalación de dependencias (`pip install -r requirements-dev.txt -r requirements.txt`) y ejecución de `pytest`
- [x] 9.2 Configurar el workflow para correr en `push` a `main` y en `pull_request` targeting `main`
- [x] 9.3 Verificar que el workflow pasa en GitHub Actions haciendo push de la suite completa
