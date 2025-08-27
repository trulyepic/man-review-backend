from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import asyncio


from sqlalchemy import text

from app.routes import series_routes, auth, series_detail, reading_list_routes, issues_routes, forum_routes

from fastapi.responses import RedirectResponse, JSONResponse
from app.routes import series_routes, auth, series_detail

from app.database import Base, engine

# 🔒 Rate limiting setup

from app.limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

app = FastAPI(title="Toon Ranks API")

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down."}
    )

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
app.include_router(reading_list_routes.router)
app.include_router(issues_routes.router)
app.include_router(forum_routes.router)

# ✅ Run DB init on startup
@app.on_event("startup")
async def on_startup():
    # Tiny retry so a momentary DB disconnect doesn't crash the app.
    for attempt in range(2):
        try:
            async with engine.begin() as conn:
                # Ensure schema exists
                await conn.execute(text('CREATE SCHEMA IF NOT EXISTS "man_review";'))
                await conn.run_sync(Base.metadata.create_all)
            break  # success
        except Exception as e:
            if attempt == 0:
                # Log + retry once after a short pause
                print(f"[startup] DB init failed, retrying once: {e!r}")
                await asyncio.sleep(0.5)
            else:
                # On the second failure, don't crash the app.
                # Tables should already exist from previous runs.
                print(f"[startup] Skipping DB init due to error: {e!r}")
