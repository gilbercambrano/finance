# Fixed Expenses Spec

## Purpose

Gestión de gastos fijos recurrentes (servicios, suscripciones, etc.). Cubre creación, sincronización automática de ocurrencias, auto-post, confirmación manual, omisión y desactivación.

## Requirements

### Requirement: Crear gasto fijo
El sistema SHALL crear un gasto fijo recurrente con nombre, categoría de tipo `gasto`, cuenta de pago, monto estimado, frecuencia y día de vencimiento. SHALL calcular `next_due_date` automáticamente a partir de `start_date` (o la fecha actual). Si `is_variable_amount=true`, SHALL forzar `auto_post=false`.

#### Scenario: Crear gasto fijo mensual
- **WHEN** se hace POST `/api/fixed-expenses` con `frequency="mensual"`, `due_day=5`, `start_date` y cuenta válida
- **THEN** la respuesta es 200 con `next_due_date` calculado correctamente (el próximo día 5)

#### Scenario: Variable amount fuerza auto_post false
- **WHEN** se hace POST `/api/fixed-expenses` con `is_variable_amount=true` y `auto_post=true`
- **THEN** `auto_post` queda en `false` en la entidad creada

---

### Requirement: Sincronización automática de ocurrencias (modo pendiente)
El sistema SHALL generar ocurrencias `pendiente` para cada periodo vencido desde `next_due_date` hasta la fecha actual cuando se consultan los gastos fijos o sus ocurrencias pendientes.

#### Scenario: Ocurrencias pendientes generadas en listado
- **WHEN** existe un gasto fijo con `next_due_date` en el pasado y se hace GET `/api/fixed-expenses`
- **THEN** la respuesta incluye el gasto fijo y la BD contiene las ocurrencias `pendiente` correspondientes a los periodos vencidos

#### Scenario: No se generan ocurrencias duplicadas
- **WHEN** se consultan las ocurrencias pendientes dos veces seguidas
- **THEN** el número de ocurrencias no aumenta en la segunda consulta

---

### Requirement: Auto-post de gasto fijo (modo automático)
El sistema SHALL, para gastos fijos con `auto_post=true` y `is_variable_amount=false`, crear automáticamente la transacción de gasto y marcar la ocurrencia como `pagado` al sincronizar, ajustando el saldo de la cuenta de pago.

#### Scenario: Auto-post crea transacción y ajusta saldo
- **WHEN** existe un gasto fijo con `auto_post=true`, `estimated_amount=500`, `account_id` de una cuenta activa con saldo 2000, y `next_due_date` <= hoy
- **THEN** después de sincronizar, la ocurrencia tiene `status="pagado"`, existe una transacción asociada de `kind="gasto"` por 500, y el saldo de la cuenta es 1500

---

### Requirement: Confirmación manual de ocurrencia
El sistema SHALL permitir confirmar una ocurrencia pendiente con POST a `/api/fixed-expenses/occurrences/{id}/confirm`, aceptando opcionalmente un `amount` diferente al estimado y una `account_id` diferente a la del gasto fijo. Debe crear la transacción de gasto y ajustar el saldo.

#### Scenario: Confirmar ocurrencia con monto por defecto
- **WHEN** se hace POST `/api/fixed-expenses/occurrences/{id}/confirm` sin payload adicional
- **THEN** se crea una transacción por el `expected_amount`, la ocurrencia queda `pagado` y el saldo de la cuenta disminuye

#### Scenario: Confirmar ocurrencia con monto distinto
- **WHEN** se hace POST `/api/fixed-expenses/occurrences/{id}/confirm` con `amount=350` (diferente al esperado)
- **THEN** la transacción creada tiene `amount=350` y el saldo refleja ese monto

#### Scenario: Confirmar ocurrencia ya pagada rechazado
- **WHEN** se hace POST `/api/fixed-expenses/occurrences/{id}/confirm` sobre una ocurrencia ya `pagado`
- **THEN** la respuesta es 400

---

### Requirement: Omisión de ocurrencia
El sistema SHALL permitir marcar una ocurrencia como `omitido` sin crear transacción ni afectar saldos.

#### Scenario: Omitir ocurrencia pendiente
- **WHEN** se hace POST `/api/fixed-expenses/occurrences/{id}/skip` sobre una ocurrencia `pendiente`
- **THEN** la respuesta es 200 y la ocurrencia queda con `status="omitido"` sin transacción creada

---

### Requirement: Desactivación de gasto fijo
El sistema SHALL desactivar un gasto fijo (no eliminarlo físicamente) para que no genere más ocurrencias futuras.

#### Scenario: Desactivar gasto fijo activo
- **WHEN** se hace DELETE `/api/fixed-expenses/{id}`
- **THEN** la respuesta es 200 y el gasto fijo queda con `is_active=false`
