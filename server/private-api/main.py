from fastapi import FastAPI
import os
import asyncpg
import asyncio
from functools import partial
from src.alembic_migrations import run_migrations

app = FastAPI()

POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PORT = os.environ["POSTGRES_PORT"]
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_HOST = os.environ["POSTGRES_HOST"]
ADVISORY_LOCK =os.environ["ADVISORY_LOCK"]

# asyncpg requires a non-sqlalchemy DSN
ASYNC_DSN = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


# -------------------------------------------------------------------
# Helpers for bootstrap flags
# -------------------------------------------------------------------
async def is_flag_set(conn, flagname: str) -> bool:
    row = await conn.fetchrow(
    "SELECT flag_set FROM bootstrap_flags WHERE flag_name = $1",
    flagname
    )
    return row and row["flag_set"] is True


async def set_flag(conn, flagname: str):
    await conn.execute(
    """
    INSERT INTO bootstrap_flags(flag_name, flag_set)
    VALUES ($1, TRUE)
    ON CONFLICT (flag_name)
    DO UPDATE SET flag_set = EXCLUDED.flag_set
    """,
    flagname
    )


# -------------------------------------------------------------------
# Async wrapper for alembic (runs blocking code in a thread)
# -------------------------------------------------------------------
async def run_migrations_async():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, run_migrations)


# -------------------------------------------------------------------
# Startup Event
# -------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    conn = await asyncpg.connect(ASYNC_DSN)

    # Acquire advisory lock (blocks until lock is free)
    await conn.execute("SELECT pg_advisory_lock($1)",int(ADVISORY_LOCK))

    # Ensure flags table exists
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS bootstrap_flags (
    flag_name TEXT PRIMARY KEY,
    flag_set BOOLEAN NOT NULL
    );
    """)    

    try:
        if not await is_flag_set(conn, "migrations_bootstrapped"):
            await run_migrations_async()
            print("boostrapping alembic")
            await set_flag(conn, "migrations_bootstrapped")
        # KEYCLOAK BOOTSTRAP
        if not await is_flag_set(conn, "keycloak_bootstrapped"):
            print("boostrapping keycloak")
            await set_flag(conn, "keycloak_bootstrapped")

        # VAULT BOOTSTRAP
        if not await is_flag_set(conn, "vault_bootstrapped"):
            print("boostrapping vault")
            await set_flag(conn, "vault_bootstrapped")

        # ALEMBIC MIGRATIONS
        

    finally:
        # Release advisory lock
        await conn.execute("SELECT pg_advisory_unlock($1)",int(ADVISORY_LOCK))
        await conn.close()
