## ADDED Requirements

### Requirement: Crear presupuesto con ítems por categoría
El sistema SHALL crear un presupuesto con nombre, tipo de periodo (`mensual`, `quincenal`, `semanal`, `personalizado`), fecha de inicio y al menos un ítem con categoría y monto planificado. Debe rechazar presupuestos sin ítems.

#### Scenario: Crear presupuesto mensual con ítems
- **WHEN** se hace POST `/api/budgets` con `period_type="mensual"`, `start_date` válida y lista de `items` no vacía
- **THEN** la respuesta es 200 con el presupuesto creado y sus ítems persistidos

#### Scenario: Presupuesto sin ítems rechazado
- **WHEN** se hace POST `/api/budgets` con `items=[]`
- **THEN** la respuesta es 400

---

### Requirement: Cálculo de estado del presupuesto vigente
El sistema SHALL calcular para el periodo activo (según `ref_date` o la fecha actual): el monto real gastado por categoría, la desviación absoluta (`actual - planned`) y la desviación porcentual. El estado de cada ítem es `alerta` si la desviación es positiva, `ok` en caso contrario.

#### Scenario: Presupuesto sin transacciones en el periodo
- **WHEN** se hace GET `/api/budgets/{id}/status` y no existen transacciones en el periodo activo
- **THEN** `actual_amount=0`, `deviation` es negativo (igual al negativo del monto planificado) y `status="ok"` para cada ítem

#### Scenario: Desviación positiva marca alerta
- **WHEN** el monto real gastado en una categoría supera el monto planificado en el periodo activo
- **THEN** el ítem correspondiente tiene `status="alerta"` y `deviation > 0`

#### Scenario: Cálculo correcto del total del presupuesto
- **WHEN** se hace GET `/api/budgets/{id}/status` con múltiples ítems
- **THEN** `total_planned` es la suma de todos los `planned_amount`, `total_actual` es la suma de todos los `actual_amount`, y `total_deviation = total_actual - total_planned`

#### Scenario: Filtro por ref_date fuera del periodo
- **WHEN** se hace GET `/api/budgets/{id}/status?ref_date=<fecha fuera del periodo>`
- **THEN** la respuesta usa el periodo correspondiente a esa fecha de referencia

---

### Requirement: Desactivación de presupuesto
El sistema SHALL desactivar un presupuesto (no eliminarlo) para que no aparezca en el listado activo por defecto.

#### Scenario: Desactivar presupuesto activo
- **WHEN** se hace DELETE `/api/budgets/{id}`
- **THEN** la respuesta es 200 y el presupuesto queda con `is_active=false`
