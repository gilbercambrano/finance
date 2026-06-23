from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.routers import auth, accounts, categories, transactions, budgets, fixed_expenses, dashboard

app = FastAPI(title="Finanzas Personales API", version="2.0.0")

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(fixed_expenses.router)
app.include_router(dashboard.router)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/login")
def serve_login():
    return FileResponse(os.path.join(STATIC_DIR, "login.html"))


@app.get("/register")
def serve_register():
    return FileResponse(os.path.join(STATIC_DIR, "register.html"))


@app.get("/{full_path:path}")
def serve_index(full_path: str):
    # SPA catch-all: cualquier otra ruta sirve la app (la auth se valida en el cliente)
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
