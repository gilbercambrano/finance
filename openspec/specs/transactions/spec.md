# Transactions Spec

## Purpose

Gestión de movimientos financieros (ingresos, gastos y transferencias). Cubre creación con ajuste de saldos, edición, eliminación y listado con filtros.

## Requirements

### Requirement: Crear transacción de ingreso
El sistema SHALL crear una transacción de tipo `ingreso`, asociarla a una categoría de tipo `ingreso` del mismo usuario, y ajustar `current_balance` de la cuenta según su naturaleza: suma en cuentas activas, resta en cuentas pasivas.

#### Scenario: Ingreso en cuenta activa incrementa saldo
- **WHEN** se hace POST `/api/transactions` con `kind="ingreso"`, `amount=500`, `account_id` de una cuenta activa con saldo inicial 1000
- **THEN** la respuesta es 200 y `current_balance` de la cuenta queda en 1500

#### Scenario: Ingreso en cuenta pasiva decrementa saldo (abono a deuda)
- **WHEN** se hace POST `/api/transactions` con `kind="ingreso"`, `amount=200`, `account_id` de una cuenta pasiva con saldo 500
- **THEN** `current_balance` de la cuenta pasiva queda en 300

#### Scenario: Ingreso sin categoría rechazado
- **WHEN** se hace POST `/api/transactions` con `kind="ingreso"` y sin `category_id`
- **THEN** la respuesta es 400

---

### Requirement: Crear transacción de gasto
El sistema SHALL crear una transacción de tipo `gasto`, asociarla a una categoría de tipo `gasto` del mismo usuario, y ajustar `current_balance` de la cuenta: resta en cuentas activas, suma en cuentas pasivas (acumulación de deuda).

#### Scenario: Gasto en cuenta activa decrementa saldo
- **WHEN** se hace POST `/api/transactions` con `kind="gasto"`, `amount=300`, `account_id` de una cuenta activa con saldo 1000
- **THEN** `current_balance` de la cuenta queda en 700

#### Scenario: Gasto en tarjeta de crédito incrementa saldo (más deuda)
- **WHEN** se hace POST `/api/transactions` con `kind="gasto"`, `amount=100`, `account_id` de una cuenta pasiva con saldo 0
- **THEN** `current_balance` de la cuenta pasiva queda en 100

#### Scenario: Categoría de tipo distinto al movimiento rechazada
- **WHEN** se hace POST `/api/transactions` con `kind="gasto"` y `category_id` que pertenece a una categoría de `ingreso`
- **THEN** la respuesta es 400

---

### Requirement: Crear transacción de transferencia
El sistema SHALL crear una transacción de tipo `transferencia` entre dos cuentas distintas del mismo usuario, ajustando ambos saldos según la naturaleza de cada cuenta. No debe aceptar cuenta origen y destino iguales.

#### Scenario: Transferencia entre dos cuentas activas
- **WHEN** se hace POST `/api/transactions` con `kind="transferencia"`, `amount=200`, `account_id` (saldo 1000) y `to_account_id` (saldo 500)
- **THEN** cuenta origen queda en 800 y cuenta destino en 700

#### Scenario: Transferencia de cuenta activa a cuenta pasiva (pago de tarjeta)
- **WHEN** se hace POST `/api/transactions` con `kind="transferencia"`, `amount=300`, `account_id` activo (saldo 1000) y `to_account_id` pasivo (saldo 300)
- **THEN** cuenta activa queda en 700 y cuenta pasiva queda en 0

#### Scenario: Transferencia con cuenta origen igual a destino rechazada
- **WHEN** se hace POST `/api/transactions` con `to_account_id` igual a `account_id`
- **THEN** la respuesta es 400

---

### Requirement: Editar transacción
El sistema SHALL revertir el efecto de la transacción original sobre los saldos y aplicar el efecto de la versión editada en una operación atómica.

#### Scenario: Editar monto de un gasto
- **WHEN** se hace PUT `/api/transactions/{id}` con `amount` diferente al original
- **THEN** la respuesta es 200, los saldos de la(s) cuenta(s) reflejan exactamente el nuevo monto (sin doble contabilidad)

---

### Requirement: Eliminar transacción
El sistema SHALL revertir el efecto de la transacción eliminada sobre los saldos de las cuentas involucradas.

#### Scenario: Eliminar ingreso revierte saldo
- **WHEN** se hace DELETE `/api/transactions/{id}` de un ingreso de 500 aplicado a una cuenta activa
- **THEN** la respuesta es 200 y `current_balance` de la cuenta vuelve al valor anterior al ingreso

#### Scenario: Eliminar transferencia revierte ambos saldos
- **WHEN** se hace DELETE `/api/transactions/{id}` de una transferencia
- **THEN** ambas cuentas recuperan sus saldos previos a la transferencia

---

### Requirement: Filtros de listado de transacciones
El sistema SHALL soportar filtros por `account_id`, `category_id`, `kind`, `date_from` y `date_to`, devolviendo solo transacciones del usuario autenticado.

#### Scenario: Filtro por cuenta
- **WHEN** se hace GET `/api/transactions?account_id={id}`
- **THEN** la respuesta contiene solo transacciones donde `account_id` o `to_account_id` coincide
