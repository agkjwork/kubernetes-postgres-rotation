from alembic.config import Config
from alembic import command
import os
from alembic.config import Config
from alembic import command

def run_migrations():
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "../alembic.ini"))
    
    # Optional: set the database URL dynamically
    # alembic_cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

    command.upgrade(alembic_cfg, "head")

