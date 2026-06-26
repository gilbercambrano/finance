## ADDED Requirements

### Requirement: Registro de usuario
El sistema SHALL crear un usuario nuevo cuando se proveen email único, contraseña y nombre completo, devolver los datos del usuario creado (sin contraseña), emitir una cookie `access_token` httpOnly, y ejecutar el seed de datos inicial para ese usuario.

#### Scenario: Registro exitoso
- **WHEN** se hace POST `/api/auth/register` con email, contraseña y nombre válidos
- **THEN** la respuesta es 200, contiene `id`, `email` y `full_name` del usuario creado, y la respuesta incluye la cookie `access_token`

#### Scenario: Email duplicado
- **WHEN** se hace POST `/api/auth/register` con un email ya registrado
- **THEN** la respuesta es 400 con mensaje de error

#### Scenario: Email normalizado a minúsculas
- **WHEN** se hace POST `/api/auth/register` con email en mayúsculas
- **THEN** el usuario se guarda con el email en minúsculas

---

### Requirement: Login de usuario
El sistema SHALL autenticar a un usuario con email y contraseña correctos, devolver los datos del usuario, y emitir la cookie `access_token` httpOnly. Debe rechazar credenciales incorrectas con 401.

#### Scenario: Login exitoso
- **WHEN** se hace POST `/api/auth/login` con credenciales válidas
- **THEN** la respuesta es 200 con datos del usuario y la cookie `access_token` está presente

#### Scenario: Contraseña incorrecta
- **WHEN** se hace POST `/api/auth/login` con contraseña errónea
- **THEN** la respuesta es 401

#### Scenario: Email no registrado
- **WHEN** se hace POST `/api/auth/login` con email que no existe
- **THEN** la respuesta es 401

---

### Requirement: Logout de usuario
El sistema SHALL eliminar la cookie `access_token` del cliente al hacer logout, de forma que peticiones posteriores con esa cookie sean rechazadas.

#### Scenario: Logout elimina la cookie
- **WHEN** se hace POST `/api/auth/logout` con una sesión activa
- **THEN** la respuesta es 200 y la cookie `access_token` ya no está presente en la respuesta

---

### Requirement: Protección de endpoints autenticados
El sistema SHALL rechazar con 401 cualquier petición a un endpoint protegido si no se incluye la cookie `access_token` o si el token es inválido/expirado.

#### Scenario: Petición sin cookie
- **WHEN** se hace GET `/api/auth/me` sin cookie
- **THEN** la respuesta es 401

#### Scenario: Petición con token inválido
- **WHEN** se hace GET `/api/auth/me` con cookie manipulada o expirada
- **THEN** la respuesta es 401

---

### Requirement: Aislamiento de sesión entre usuarios
El sistema SHALL garantizar que la cookie de sesión de un usuario no permite acceder como otro usuario.

#### Scenario: La cookie del usuario A no autentica al usuario B
- **WHEN** el usuario A hace GET `/api/auth/me` con su propia cookie
- **THEN** la respuesta devuelve los datos de A, no de B
