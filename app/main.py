from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers import guests, scanner, dashboard
import os

app = FastAPI(title="QR-Access Event Manager | Shaq O'Neal Private Event")

# Mount Routers
# app.include_router(auth.router)
app.include_router(guests.router)
app.include_router(scanner.router)
app.include_router(dashboard.router)

# Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/static")

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/scanner")
async def read_scanner(request: Request):
    return templates.TemplateResponse("scanner.html", {"request": request})

@app.get("/dashboard")
async def read_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/invitados")
async def read_invitados(request: Request):
    return templates.TemplateResponse("invitados.html", {"request": request})

@app.get("/capturas")
async def read_capturas(request: Request):
    return templates.TemplateResponse("capturas.html", {"request": request})
