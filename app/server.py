from fastapi import FastAPI
from fastapi.logger import logger
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app import routes
from app.db import db, init_surrealdb


@asynccontextmanager
async def lifespan(_: FastAPI):
    """FastAPI lifespan event."""
    try:
        await init_surrealdb()
        logger.info("Connected to database.")
        yield
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
    finally:
        await db.close()


app = FastAPI(
    title="Bronya",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.account, prefix="/api/account")
app.mount("/", StaticFiles(directory="dist", html=True), name="dist")
