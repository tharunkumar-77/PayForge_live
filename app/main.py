from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.routes.users import router as users_router
from app.routes.wallets import router as wallets_router
from app.routes.payment import router as payment_router
from app.routes.refund import router as refund_router
from app.routes.auth import router as auth_router



app = FastAPI(title="PayForge")

# CORS configuration (allow all for demo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users_router)
app.include_router(wallets_router)
app.include_router(payment_router)
app.include_router(auth_router)

# Serve frontend static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# CORS configuration (allow all for demo)


# Include routers


# Serve frontend static files

