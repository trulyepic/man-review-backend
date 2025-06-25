from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import series_routes, auth, series_detail
from app.database import Base, engine

app = FastAPI(title="Manga/Manhwa/Manhua Review API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(series_routes.router)
app.include_router(auth.router, prefix="/auth")
app.include_router(series_detail.router)

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)