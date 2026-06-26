## ADDED Requirements

### Requirement: Creación de categoría
El sistema SHALL crear una categoría de tipo `ingreso` o `gasto` para el usuario autenticado. Debe rechazar cualquier valor de `kind` distinto de esos dos.

#### Scenario: Crear categoría de ingreso
- **WHEN** se hace POST `/api/categories` con `kind="ingreso"`, `name` y `group` válidos
- **THEN** la respuesta es 200 con la categoría creada y `kind="ingreso"`

#### Scenario: Crear categoría de gasto
- **WHEN** se hace POST `/api/categories` con `kind="gasto"`, `name` y `group` válidos
- **THEN** la respuesta es 200 con la categoría creada y `kind="gasto"`

#### Scenario: kind inválido rechazado
- **WHEN** se hace POST `/api/categories` con `kind="otro"`
- **THEN** la respuesta es 400

---

### Requirement: Listado de categorías activas
El sistema SHALL devolver solo las categorías activas del usuario autenticado, ordenadas por `kind`, `group` y `name`. Debe soportar filtro opcional por `kind`.

#### Scenario: Listado sin filtro
- **WHEN** se hace GET `/api/categories`
- **THEN** la respuesta contiene solo categorías activas del usuario autenticado

#### Scenario: Filtro por kind=ingreso
- **WHEN** se hace GET `/api/categories?kind=ingreso`
- **THEN** la respuesta contiene solo categorías con `kind="ingreso"` del usuario autenticado

#### Scenario: Filtro por kind=gasto
- **WHEN** se hace GET `/api/categories?kind=gasto`
- **THEN** la respuesta contiene solo categorías con `kind="gasto"` del usuario autenticado

---

### Requirement: Desactivación de categoría
El sistema SHALL desactivar una categoría del usuario autenticado (no eliminarla físicamente). Debe retornar 404 si la categoría pertenece a otro usuario.

#### Scenario: Desactivar categoría propia
- **WHEN** se hace DELETE `/api/categories/{id}` sobre una categoría del usuario autenticado
- **THEN** la respuesta es 200 y la categoría queda con `is_active=false`

#### Scenario: Desactivar categoría ajena devuelve 404
- **WHEN** se hace DELETE `/api/categories/{id}` sobre una categoría de otro usuario
- **THEN** la respuesta es 404
