from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routers import guests, scanner, dashboard
import os

app = FastAPI(title="MSTCH Digital | QR-Access Manager")

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
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/scanner")
async def read_scanner(request: Request):
    return templates.TemplateResponse(request=request, name="scanner.html")

@app.get("/dashboard")
async def read_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.get("/invitados")
async def read_invitados(request: Request):
    return templates.TemplateResponse(request=request, name="invitados.html")

@app.get("/descarga-qrs")
async def read_descarga_qrs(request: Request):
    return templates.TemplateResponse(request=request, name="descarga_qrs.html")


@app.get("/capturas")
async def read_capturas(request: Request):
    return templates.TemplateResponse(request=request, name="capturas.html")
