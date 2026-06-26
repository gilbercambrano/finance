# Test Infrastructure Spec

## Purpose

Infraestructura de pytest para la suite de integración: base de datos de prueba aislada, limpieza por rollback, override de dependencias de FastAPI, fixtures de autenticación y CI con GitHub Actions.

## Requirements

### Requirement: Base de datos de prueba PostgreSQL aislada
El sistema SHALL usar una base de datos PostgreSQL dedicada (`finanzas_test`) para la suite de tests. Esta BD SHALL crearse automáticamente al iniciar la sesión de pytest, aplicar las migraciones de Alembic y eliminarse al finalizar.

#### Scenario: BD de prueba creada y migrada al inicio
- **WHEN** se ejecuta `pytest` por primera vez
- **THEN** la BD `finanzas_test` existe, las tablas están creadas según el último estado de Alembic, y los tests pueden insertarse datos sin afectar la BD de desarrollo

#### Scenario: BD de prueba eliminada al terminar
- **WHEN** la sesión de pytest termina (con éxito o con error)
- **THEN** la BD `finanzas_test` es eliminada

---

### Requirement: Limpieza de datos entre tests (rollback por transacción)
El sistema SHALL aislar cada test en una transacción de SQLAlchemy que hace rollback al terminar, garantizando que ningún test comparte estado con otro.

#### Scenario: Estado de un test no contamina el siguiente
- **WHEN** el test A inserta registros y el test B se ejecuta a continuación
- **THEN** el test B no ve los registros insertados por el test A

---

### Requirement: Override de dependencia de BD en FastAPI
El sistema SHALL inyectar la sesión de test (con transacción abierta) en los endpoints de FastAPI mediante `app.dependency_overrides[get_db]`, de forma que los requests HTTP del cliente de test usen la misma sesión que los asserts.

#### Scenario: El cliente HTTP y los asserts comparten la misma sesión de BD
- **WHEN** un test hace un POST vía `AsyncClient` y luego consulta la BD directamente
- **THEN** el registro creado por el POST es visible en la misma transacción de test

---

### Requirement: Fixtures de usuario autenticado
La suite SHALL proveer fixtures que creen un usuario, hagan login y retornen un `AsyncClient` con la cookie de sesión lista, para que los tests no repitan código de setup de autenticación.

#### Scenario: Fixture de cliente autenticado listo para usar
- **WHEN** un test recibe el fixture `auth_client` (usuario A)
- **THEN** puede hacer requests a endpoints protegidos sin código adicional de login

---

### Requirement: Workflow de GitHub Actions con PostgreSQL
El sistema SHALL tener un workflow en `.github/workflows/tests.yml` que levanta un servicio PostgreSQL, instala dependencias, ejecuta las migraciones de Alembic y corre `pytest` en cada push a `main` y en cada PR hacia `main`.

#### Scenario: CI pasa con todos los tests verdes
- **WHEN** se hace push a `main` o se abre un PR hacia `main`
- **THEN** el workflow ejecuta la suite completa y reporta el resultado en GitHub
