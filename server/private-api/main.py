from fastapi import FastAPI
import os
import asyncio
from functools import partial
import psycopg2
import psycopg2.extras
from src.alembic_migrations import run_migrations
import time
app = FastAPI()

POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PORT = os.environ["POSTGRES_PORT"]
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_HOST = os.environ["POSTGRES_HOST"]
ADVISORY_LOCK = int(os.environ["ADVISORY_LOCK"])

DSN = f"dbname={POSTGRES_DB} user={POSTGRES_USER} password={POSTGRES_PASSWORD} host={POSTGRES_HOST} port={POSTGRES_PORT}"


def get_conn():
    return psycopg2.connect(DSN, cursor_factory=psycopg2.extras.DictCursor)


def ensure_bootstrap_table(conn):
    
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bootstrap_flags (
                flag_name TEXT PRIMARY KEY,
                flag_set BOOLEAN NOT NULL
            )
        """)
    conn.commit()


def is_flag_set(conn, flagname: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT flag_set FROM bootstrap_flags WHERE flag_name = %s", (flagname,))
        row = cur.fetchone()
        return row is not None and row[0] is True

def set_flag(conn, flagname: str):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO bootstrap_flags(flag_name, flag_set)
            VALUES (%s, TRUE)
            ON CONFLICT (flag_name)
            DO UPDATE SET flag_set = EXCLUDED.flag_set
        """, (flagname,))
    conn.commit()


def acquire_lock(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK,))
    conn.commit()


def release_lock(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK,))
    conn.commit()


async def run_sync(fn, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(fn, *args))

def try_acquire_lock(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(%s)", (ADVISORY_LOCK,))
        return cur.fetchone()[0]


@app.on_event("startup")
async def startup_event():

    conn = await run_sync(get_conn)

    # Acquire lock (sync)
    while True:
        got_lock = await run_sync(try_acquire_lock, conn)
        if got_lock:
            break
        print("attempting to acquire lock...")
        await asyncio.sleep(1)

    ensure_bootstrap_table(conn)
    try:
        
        if not is_flag_set(conn, "migrations_bootstrapped"):
            run_migrations()
            print(f"alembic bootstrapping", flush=True)
            set_flag(conn, "migrations_bootstrapped")
        else:
            print(f"alembic bootstrapped already: {is_flag_set(conn, 'migrations_bootstrapped')}", flush=True)

        if not is_flag_set(conn, "keycloak_bootstrapped"):
            print(f"keycloak bootstrapping", flush=True)
            set_flag(conn, "keycloak_bootstrapped")
        else:
            print(f"keycloak bootstrapped already: {is_flag_set(conn, 'keycloak_bootstrapped')}", flush=True)

        if not is_flag_set(conn, "vault_bootstrapped"):
            print(f"vault bootstrapping", flush=True)
            set_flag(conn, "vault_bootstrapped")
        else:
            print(f"vault bootstrapped already: {is_flag_set(conn, 'vault_bootstrapped')}", flush=True)
        
        

    finally:
        # Release lock (sync)
        await run_sync(release_lock, conn)
        conn.close()
        print("BOOTSTRAPPING COMPLETED")

