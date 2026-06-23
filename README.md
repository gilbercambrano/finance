# Ledger·MX — Finanzas Personales (v2)

Aplicación web multiusuario para control de finanzas personales: cuentas
bancarias, efectivo, tarjetas de crédito y deudas, pagos fijos
calendarizados, presupuesto y dashboard de indicadores. Pensada para
producción: PostgreSQL + Docker + Nginx.

## Novedades de esta versión

- **Multiusuario real**: registro, inicio y cierre de sesión (cookie JWT
  httpOnly). Cada usuario administra su información de forma
  completamente independiente — nadie ve los datos de otro usuario.
- **Tarjetas de crédito y deudas**: registra tarjetas de crédito y
  préstamos recibidos con límite de crédito, día de corte, día límite de
  pago, pago mínimo y tasa de interés anual. El dashboard calcula
  automáticamente la próxima fecha de corte/pago y el % de utilización
  del límite.
- **Gastos fijos / pagos domiciliados**: cataloga servicios (luz, agua,
  gas, internet), suscripciones y mensualidades de deuda con su
  periodicidad (semanal a anual). El sistema:
  - Registra el movimiento **automáticamente** si el monto es fijo y
    activaste esa opción.
  - Te pide **confirmación manual** (con monto editable) si el monto es
    variable (ej. luz) o si no activaste el automático.
  - Da mantenimiento completo: crear, editar, desactivar.
- **Indicador de gasto fijo mensual** en el dashboard: total mensualizado
  estimado + lo ya pagado/pendiente del mes en curso.
- **PostgreSQL + Alembic**: base de datos de producción con migraciones
  versionadas.

## Arquitectura

```
┌────────────┐      ┌──────────────────┐      ┌──────────────┐
│   Nginx    │ ───▶ │ FastAPI (Gunicorn │ ───▶ │  PostgreSQL  │
│ (80 / 443) │      │ + Uvicorn workers)│      │   (Docker)   │
└────────────┘      └──────────────────┘      └──────────────┘
```

Todo corre vía Docker Compose: `db`, `api`, `nginx`.

## 1. Requisitos en el servidor (GCP, Ubuntu)

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER   # cierra sesión y vuelve a entrar para aplicar
```

En la consola de GCP, abre el firewall del proyecto para permitir tráfico
entrante en los puertos **80** y **443** (VPC network → Firewall rules).

## 2. Configuración

```bash
git clone <tu-repositorio> finanzas-app   # o sube el .zip y descomprímelo
cd finanzas-app
cp .env.example .env
nano .env   # define POSTGRES_PASSWORD y SECRET_KEY (usa valores únicos y largos)
```

Genera una `SECRET_KEY` segura:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## 3. Levantar el proyecto

```bash
docker compose up -d --build
docker compose logs -f api   # verifica que las migraciones corrieron bien
```

La API queda accesible en `http://<IP-del-servidor>/` (vía Nginx).

> La primera vez que el contenedor `api` arranca, ejecuta automáticamente
> `alembic upgrade head` para crear las tablas. No necesitas hacer nada
> manual en la base de datos.

## 4. Activar HTTPS (recomendado)

Si tienes un dominio apuntando a la IP del servidor:

```bash
sudo docker compose run --rm --entrypoint "" nginx sh -c \
  "apk add certbot certbot-nginx --no-cache && \
   certbot certonly --webroot -w /var/www/certbot -d TU_DOMINIO.com"
```

Después, agrega el bloque `server { listen 443 ssl; ... }` en
`nginx/nginx.conf` apuntando a los certificados generados en
`/etc/letsencrypt/live/TU_DOMINIO.com/`, y reinicia:
```bash
docker compose restart nginx
```

Mientras no tengas HTTPS, deja `COOKIE_SECURE=false` en `.env`
(de lo contrario el navegador no podrá guardar la cookie de sesión).
Una vez con HTTPS, cambia a `COOKIE_SECURE=true` y reinicia el contenedor
`api`.

## 5. Respaldos

Los datos viven en el volumen Docker `pgdata`. Respaldo manual:
```bash
docker compose exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > respaldo_$(date +%F).sql
```
Restaurar:
```bash
cat respaldo_2026-06-22.sql | docker compose exec -T db psql -U $POSTGRES_USER -d $POSTGRES_DB
```

## 6. Migraciones futuras (cuando agreguemos más funciones)

```bash
# Generar una nueva migración tras cambiar app/models.py:
docker compose exec api alembic revision --autogenerate -m "descripcion"
docker compose exec api alembic upgrade head
```

## 7. Desarrollo local (sin Docker, opcional)

```bash
cd api
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/finanzas"
export SECRET_KEY="dev-secret"
export COOKIE_SECURE=false
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```
(Requiere un PostgreSQL local corriendo en el puerto 5432.)

## 8. Cómo está organizada la información

### Cuentas (vista "Cuentas")
Débito/nómina, ahorro, inversión y préstamos otorgados a terceros
(todos **activos**, suman al patrimonio).

### Tarjetas y Deudas (vista nueva)
Tarjetas de crédito y préstamos recibidos (**pasivos**, restan al
patrimonio). Aquí defines límite de crédito, día de corte, día límite de
pago, pago mínimo y tasa de interés. El sistema calcula automáticamente
las próximas fechas de corte y pago.

### Movimientos
- **Ingreso / Gasto**: afectan una cuenta y una categoría.
- **Transferencia**: mueve dinero entre dos cuentas — úsala para retiro
  de efectivo, depósito de efectivo, pago de tarjeta de crédito
  (Efectivo/banco → Tarjeta) o préstamo otorgado/recibido.

### Gastos Fijos (vista nueva)
Servicios, suscripciones y mensualidades de deuda con periodicidad
(semanal, quincenal, mensual, bimestral, trimestral, semestral, anual).
Cada vez que entras a la app, el sistema revisa qué pagos ya vencieron:
- Si es de **monto fijo** y activaste "automático", registra el
  movimiento solo.
- Si es de **monto variable** (o no activaste automático), aparece en
  "Pendientes por confirmar" para que captures el monto real y
  confirmes — así no se duplica ni se descuadra si el monto cambió.

### Presupuesto y Categorías
Igual que antes: presupuesto por periodo con alertas de desviación, y
catálogo de categorías clasificado en Fijo / Variable /
Ahorro-Inversión / Deuda / Otros.

### Dashboard
Patrimonio neto, flujo del mes, tendencia de 6 meses, gasto por
categoría, presupuesto vigente, **gasto fijo mensual estimado**,
**pagos fijos pendientes** y **resumen de tarjetas y deudas** con su
próxima fecha de pago.

## 9. Próximos pasos sugeridos (no incluidos todavía)

- Notificaciones por correo/WhatsApp antes de la fecha límite de pago.
- Importación de movimientos desde CSV/Excel del banco.
- Metas de ahorro/inversión a mediano-largo plazo.
- Reportes exportables a Excel/PDF.
- Recuperación de contraseña por correo.

Dime si quieres que sigamos con alguna de estas.
