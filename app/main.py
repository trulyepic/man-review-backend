from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.routes import series_routes, auth, series_detail
from app.database import Base, engine

app = FastAPI(title="Toon Ranks API")

# 🚨 Redirect www.toonranks.com → toonranks.com
@app.middleware("http")
async def redirect_www(request: Request, call_next):
    host = request.headers.get("host", "")
    if host.startswith("www."):
        # Remove www. and redirect
        new_url = request.url.replace(netloc=host.replace("www.", ""))
        return RedirectResponse(str(new_url), status_code=301)
    return await call_next(request)

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Include your routers
app.include_router(series_routes.router)
app.include_router(auth.router, prefix="/auth")
app.include_router(series_detail.router)

# ✅ Run DB init on startup
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
