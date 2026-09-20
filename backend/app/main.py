from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, daily_pulse, lessons, sandbox, users
from app.core.db import Base, engine
from app.models import *  # noqa: F401,F403 -- registers every model with Base.metadata before create_all

app = FastAPI(
    title="Cortex AI",
    description="Interactive AI training platform: role-based tracks, a daily agentic micro-learning pipeline, and an in-browser prompt sandbox.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # the Next.js dev server; add the deployed frontend origin here too
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(lessons.router)
app.include_router(daily_pulse.router)
app.include_router(sandbox.router)


@app.on_event("startup")
def on_startup():
    # SQLite + a small schema: create_all is fine for local dev. Once this
    # needs real migrations (adding a column without dropping data), switch
    # to `alembic upgrade head` here instead -- the alembic/ directory is
    # already scaffolded for that.
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    """This is an API-only backend -- the actual app UI lives on the Next.js
    frontend (http://localhost:3000 in dev). A bare 404 on `/` here reads as
    "the app is broken" to anyone who lands on this port directly, so this
    exists purely to point them at the right place and at the interactive
    API docs, rather than leaving the root route undefined."""
    return {
        "service": "Cortex AI API",
        "frontend": "http://localhost:3000",
        "docs": "/docs",
        "health": "/health",
    }
