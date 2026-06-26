## ADDED Requirements

### Requirement: Listado de cuentas del usuario
El sistema SHALL devolver solo las cuentas activas del usuario autenticado, ordenadas por tipo (efectivo primero) y nombre. Con el parámetro `include_inactive=true` SHALL incluir también las cuentas inactivas.

#### Scenario: Listado de cuentas activas
- **WHEN** se hace GET `/api/accounts`
- **THEN** la respuesta es 200 con lista de cuentas activas del usuario autenticado

#### Scenario: Inclusión de cuentas inactivas
- **WHEN** se hace GET `/api/accounts?include_inactive=true`
- **THEN** la respuesta incluye tanto cuentas activas como inactivas

---

### Requirement: Creación de cuenta activa
El sistema SHALL crear una cuenta de tipo activo (débito, ahorro, efectivo, inversión, préstamo otorgado) con `nature="activo"` y `current_balance` igual al `initial_balance` indicado. No debe aceptar `credit_detail` para cuentas activas.

#### Scenario: Crear cuenta de débito
- **WHEN** se hace POST `/api/accounts` con `account_type="debito"`, `nature="activo"` e `initial_balance=1000`
- **THEN** la respuesta es 200 con `current_balance=1000` y `nature="activo"`

#### Scenario: Naturaleza incorrecta para tipo activo
- **WHEN** se hace POST `/api/accounts` con `account_type="debito"` y `nature="pasivo"`
- **THEN** la respuesta es 400

---

### Requirement: Creación de cuenta pasiva con detalle de deuda
El sistema SHALL crear cuentas de tipo pasivo (tarjeta de crédito, préstamo recibido) con `nature="pasivo"` y opcionalmente persistir el `CreditDetail` asociado (límite, día de corte, día de pago, tasa de interés, pago mínimo).

#### Scenario: Crear tarjeta de crédito sin detalle
- **WHEN** se hace POST `/api/accounts` con `account_type="credito"` y `nature="pasivo"` sin `credit_detail`
- **THEN** la respuesta es 200 con `nature="pasivo"` y sin `credit_detail`

#### Scenario: Crear tarjeta de crédito con detalle
- **WHEN** se hace POST `/api/accounts` con `account_type="credito"`, `nature="pasivo"` y `credit_detail` con `credit_limit`, `cutoff_day` y `payment_due_day`
- **THEN** la respuesta es 200 y `credit_detail` contiene los valores enviados

#### Scenario: Naturaleza incorrecta para tipo pasivo
- **WHEN** se hace POST `/api/accounts` con `account_type="credito"` y `nature="activo"`
- **THEN** la respuesta es 400

---

### Requirement: Edición de cuenta
El sistema SHALL permitir actualizar nombre, banco, notas y otros campos editables. Para cuentas pasivas, SHALL actualizar o crear el `CreditDetail` asociado.

#### Scenario: Editar nombre de cuenta
- **WHEN** se hace PUT `/api/accounts/{id}` con un nuevo `name`
- **THEN** la respuesta es 200 con el nombre actualizado

#### Scenario: Agregar detalle de crédito en edición
- **WHEN** se hace PUT `/api/accounts/{id}` en una cuenta pasiva con `credit_detail` incluido
- **THEN** la respuesta es 200 con `credit_detail` persistido

#### Scenario: Editar cuenta de otro usuario
- **WHEN** se hace PUT `/api/accounts/{id}` sobre una cuenta que pertenece a otro usuario
- **THEN** la respuesta es 404

---

### Requirement: Desactivación o eliminación de cuenta
El sistema SHALL desactivar una cuenta si tiene transacciones o gastos fijos asociados, o eliminarla físicamente si no los tiene. No SHALL permitir desactivar la cuenta de efectivo.

#### Scenario: Eliminar cuenta sin movimientos
- **WHEN** se hace DELETE `/api/accounts/{id}` en una cuenta sin transacciones ni gastos fijos
- **THEN** la respuesta es 200 y la cuenta ya no existe en la BD

#### Scenario: Desactivar cuenta con movimientos
- **WHEN** se hace DELETE `/api/accounts/{id}` en una cuenta con transacciones asociadas
- **THEN** la respuesta es 200 y la cuenta queda con `is_active=false`

#### Scenario: No se puede desactivar la cuenta de efectivo
- **WHEN** se hace DELETE `/api/accounts/{id}` sobre la cuenta de efectivo
- **THEN** la respuesta es 400
