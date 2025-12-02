from src.alembic_migrations import run_migrations

# here will call the migration script
# there can be multiple calls to the db depending on replicas
# so will have to wait for postgres to spin up first, then will call 



if __name__ == "__main__":
    run_migrations()

