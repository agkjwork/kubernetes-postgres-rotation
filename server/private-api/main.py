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



def acquire_lock(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK,))
    conn.commit()


def release_lock(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK,))
    conn.commit()

def try_acquire_lock(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(%s)", (ADVISORY_LOCK,))
        return cur.fetchone()[0]

async def run_sync(fn, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(fn, *args))

KEYCLOAK_VERSION = "0.0.0"
VAULT_VERSION = "0.0.0" 
SCHEMA_VERSION= "0.0.0" # should i retrieve using alembic version instead
SCEHMA_MIGRATION_TYPE="upgrade"
SCHEMA_MIGRATION_VERSION="head"


def create_service_version_table(conn):
    # first check if table exists
    # if table does not exists,create it 
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS service (
            service_name VARCHAR(25) PRIMARY KEY,
            service_version VARCHAR(10) NULL);
        """)
    conn.commit()

def find_service_version_by_service_name(conn, service_name: str) -> int | None:
    with conn.cursor() as cur:
        # Try inserting the service with no version
        cur.execute("""
            INSERT INTO service (service_name)
            VALUES (%s)
            ON CONFLICT (service_name) DO NOTHING
            RETURNING service_version;
        """, (service_name,))
        
        row = cur.fetchone()
        if row is not None:
            # Newly inserted → version is None
            return row[0]

        # Already exists → fetch current version
        cur.execute("""
            SELECT service_version
            FROM service
            WHERE service_name = %s;
        """, (service_name,))
        return cur.fetchone()[0]  # Could be None
   

def set_service_version_by_service_name(conn, service_name: str, service_version: str) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE service
            SET service_version = %s
            WHERE service_name = %s
        """, (service_version, service_name,))
        if cur.rowcount == 0:
            raise ValueError(f"Service name not found: {service_name}")
        
        conn.commit()

def upgrade_vault(conn) -> None:
    while True:
        vault_version = find_service_version_by_service_name(conn,"vault")
        if vault_version is None:
            print("upgrade vault from None to 0.0.0", flush=True)
            set_service_version_by_service_name(conn, "vault", "0.0.0")
            continue

        if vault_version == VAULT_VERSION:
            print("Vault is already at target version, no upgrades needed.", flush=True)
            return

        if vault_version == "0.0.0":
            print("upgrading vault from 0.0.0 to 0.1.0", flush=True)
            set_service_version_by_service_name(conn, "vault", "0.1.0")

def upgrade_keycloak(conn) -> None:
    while True:
        keycloak_version = find_service_version_by_service_name(conn,"keycloak")
        if keycloak_version is None:
            print("upgrade vault from None to 0.0.0", flush=True)
            set_service_version_by_service_name(conn, "keycloak", "0.0.0")
            continue

        if keycloak_version == KEYCLOAK_VERSION:
            print("Keycloak is already at target version, no upgrades needed.", flush=True)
            return

        if keycloak_version == "0.0.0":
            print("upgrading keycloak from 0.0.0 to 0.1.0", flush=True)
            set_service_version_by_service_name(conn, "keycloak", "0.1.0")

def upgrade_schema(conn) -> None:
    while True:
        schema_version = find_service_version_by_service_name(conn,"schema")
        if schema_version is None:
            print(f"{SCEHMA_MIGRATION_TYPE} schema from None to 0.0.0", flush=True)
            run_migrations(SCEHMA_MIGRATION_TYPE, SCHEMA_MIGRATION_VERSION)
            set_service_version_by_service_name(conn, "schema", "0.0.0")
            continue

        if schema_version == SCHEMA_VERSION:
            print("Schema is already at target version, no upgrades needed.", flush=True)
            return

        if schema_version == "0.0.0":
            print(f"{SCEHMA_MIGRATION_TYPE} schema from 0.0.0 to 0.1.0", flush=True)
            set_service_version_by_service_name(conn, "schema", "0.1.0")
            

@app.on_event("startup")
async def startup_event():

    try:
        # create connection
        conn = await run_sync(get_conn)
        conn.autocommit = True

        # Acquire lock (sync)
        while True:
            got_lock = await run_sync(try_acquire_lock, conn)
            if got_lock:
                break
            print("attempting to acquire lock...")
            await asyncio.sleep(1)

        create_service_version_table(conn)
        #ensure_bootstrap_table(conn)


        # ------------------------------
        # |service_name|service_version|
        # ------------------------------
        # |   schema   |      0        |
        # |   keycloak |      0        |
        # |   vault    |      0        |
        # ------------------------------

        # versions of keycloak, vault and postgres is tagged to a image version
        # first check migration version in the db
        # if migration version in db is < current version
        # upgrade 
        # check if fail, to rollback helm 
        upgrade_vault(conn)
        upgrade_keycloak(conn)
        upgrade_schema(conn)



    finally:
        # Release lock (sync)
        print("UPGRADING COMPLETED",flush=True)
        await run_sync(release_lock, conn)
        conn.close()
        

