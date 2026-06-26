# User Data Isolation Spec

## Purpose

Garantizar que cada usuario solo puede ver y modificar sus propios datos. Cubre el aislamiento de cuentas, transacciones, categorías, gastos fijos y presupuestos.

## Requirements

### Requirement: Aislamiento de cuentas entre usuarios
El sistema SHALL devolver 404 (nunca datos ni 403) cuando un usuario intenta leer o modificar una cuenta que pertenece a otro usuario.

#### Scenario: Leer cuenta ajena devuelve 404
- **WHEN** el usuario B hace GET de una cuenta que pertenece al usuario A
- **THEN** la respuesta es 404

#### Scenario: Editar cuenta ajena devuelve 404
- **WHEN** el usuario B hace PUT sobre una cuenta del usuario A
- **THEN** la respuesta es 404

#### Scenario: Eliminar cuenta ajena devuelve 404
- **WHEN** el usuario B hace DELETE sobre una cuenta del usuario A
- **THEN** la respuesta es 404

---

### Requirement: Aislamiento de transacciones entre usuarios
El sistema SHALL filtrar transacciones por `user_id` del usuario autenticado. Un usuario no SHALL poder ver, editar ni eliminar transacciones de otro usuario.

#### Scenario: Listado no incluye transacciones ajenas
- **WHEN** el usuario B hace GET `/api/transactions`
- **THEN** la respuesta no contiene ninguna transacción que pertenezca al usuario A

#### Scenario: Editar transacción ajena devuelve 404
- **WHEN** el usuario B hace PUT `/api/transactions/{id}` sobre una transacción del usuario A
- **THEN** la respuesta es 404

#### Scenario: Eliminar transacción ajena devuelve 404
- **WHEN** el usuario B hace DELETE `/api/transactions/{id}` sobre una transacción del usuario A
- **THEN** la respuesta es 404

---

### Requirement: Aislamiento de categorías entre usuarios
El sistema SHALL filtrar categorías por `user_id`. Un usuario no SHALL poder asignar a sus transacciones una categoría de otro usuario.

#### Scenario: Crear transacción con categoría ajena rechazado
- **WHEN** el usuario B hace POST `/api/transactions` con `category_id` de una categoría del usuario A
- **THEN** la respuesta es 400 (categoría inválida)

---

### Requirement: Aislamiento de gastos fijos entre usuarios
El sistema SHALL filtrar gastos fijos por `user_id`. Un usuario no SHALL poder ver, editar, desactivar ni confirmar ocurrencias de gastos fijos ajenos.

#### Scenario: Listado de gastos fijos solo del usuario autenticado
- **WHEN** el usuario B hace GET `/api/fixed-expenses`
- **THEN** la respuesta no contiene gastos fijos del usuario A

#### Scenario: Confirmar ocurrencia ajena devuelve 404
- **WHEN** el usuario B hace POST `/api/fixed-expenses/occurrences/{id}/confirm` sobre una ocurrencia del usuario A
- **THEN** la respuesta es 404

---

### Requirement: Aislamiento de presupuestos entre usuarios
El sistema SHALL filtrar presupuestos por `user_id`. Un usuario no SHALL poder ver ni modificar presupuestos de otro usuario.

#### Scenario: Estado de presupuesto ajeno devuelve 404
- **WHEN** el usuario B hace GET `/api/budgets/{id}/status` sobre un presupuesto del usuario A
- **THEN** la respuesta es 404

#### Scenario: Desactivar presupuesto ajeno devuelve 404
- **WHEN** el usuario B hace DELETE `/api/budgets/{id}` sobre un presupuesto del usuario A
- **THEN** la respuesta es 404
