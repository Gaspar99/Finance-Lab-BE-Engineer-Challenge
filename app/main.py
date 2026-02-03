from fastapi import FastAPI

from app.api import routes

app = FastAPI(title="Ultrasound Report API", version="1.0.0")

app.include_router(routes.router)
