from fastapi import FastAPI

from app.routes.wallets import router

app = FastAPI(title="PayForge")

app.include_router(router)


@app.get("/")
def root():
    return {"status": "PayForge API running"}