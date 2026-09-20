from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, daily_pulse, sandbox, users
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
