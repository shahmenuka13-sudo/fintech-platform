import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# To make sure Alembic can find your models, add the project root to sys.path
import sys
import os
# Assuming env.py is in fingyan_financial_platform/backend/alembic
# os.path.dirname(__file__) -> .../backend/alembic
# os.path.join(..., '..') -> .../backend
# os.path.join(..., '..', '..') -> .../fingyan_financial_platform (project's named root folder)
# os.path.join(..., '..', '..', '..') -> the directory CONTAINING fingyan_financial_platform
# We want to add the directory that *contains* `fingyan_financial_platform` package.
# Or, if `fingyan_financial_platform` is the top-level of our code structure that we want in PYTHONPATH:
PROJECT_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)
# Now an import like `from backend.models.db_models import Base` should work if alembic is run
# from a context where `fingyan_financial_platform` is the current directory, or if `PROJECT_ROOT`
# is the `fingyan_financial_platform` directory itself.

# Let's adjust PROJECT_ROOT to be the parent of `fingyan_financial_platform` directory
# so that `from fingyan_financial_platform.backend...` works.
PROJECT_PARENT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, PROJECT_PARENT_DIR)

from fingyan_financial_platform.backend.models.db_models import Base as TargetBase

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line needs to be placed early!
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata
target_metadata = TargetBase.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_database_url():
    """
    Constructs database URL prioritizing environment variables:
    1. DATABASE_URL (e.g., "postgresql://user:pass@host:port/db")
    2. Component POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST / POSTGRES_HOST_ALEMBIC, POSTGRES_PORT, POSTGRES_DB
    3. sqlalchemy.url from alembic.ini (as a last resort)
    """
    # 1. Try DATABASE_URL environment variable first
    db_url_env = os.getenv("DATABASE_URL")
    if db_url_env:
        print(f"Using DATABASE_URL env var for Alembic: {db_url_env}")
        return db_url_env

    # 2. Try constructing from component environment variables
    # These are expected to be set in the environment running alembic.
    # `POSTGRES_HOST_ALEMBIC` is an override for `POSTGRES_HOST` if present (for local alembic runs)
    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")

    db_host_alembic = os.getenv("POSTGRES_HOST_ALEMBIC")
    db_host_docker = os.getenv("POSTGRES_HOST") # Standard host for app (e.g., "postgres_db")
    db_host = db_host_alembic if db_host_alembic else db_host_docker # Prioritize alembic specific host

    db_port = os.getenv("POSTGRES_PORT")
    db_name = os.getenv("POSTGRES_DB")

    if all([db_user, db_password, db_host, db_port, db_name]):
        constructed_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        print(f"Constructed DATABASE_URL from component env vars for Alembic (host: {db_host}): {constructed_url}")
        return constructed_url
    else:
        missing_vars = [var for var, val in [
            ("POSTGRES_USER", db_user), ("POSTGRES_PASSWORD", db_password),
            ("POSTGRES_HOST/POSTGRES_HOST_ALEMBIC", db_host),
            ("POSTGRES_PORT", db_port), ("POSTGRES_DB", db_name)
        ] if not val]
        print(f"Component env vars not all set for DB URL construction. Missing or empty: {missing_vars}. "
              "Will try alembic.ini next.")

    # 3. Fallback to sqlalchemy.url from alembic.ini
    # This will typically use the docker-compose service name (e.g., 'postgres_db')
    # and might only work if alembic is run within that docker network or if it's resolvable.
    db_url_from_ini = config.get_main_option("sqlalchemy.url")
    if db_url_from_ini:
        print(f"Falling back to alembic.ini sqlalchemy.url for Alembic: {db_url_from_ini}")
        return db_url_from_ini

    # If no URL could be determined
    raise ValueError(
        "Database URL could not be determined. Please set DATABASE_URL or "
        "all of POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST (or POSTGRES_HOST_ALEMBIC), "
        "POSTGRES_PORT, POSTGRES_DB environment variables, "
        "or ensure sqlalchemy.url is correctly set in alembic.ini."
    )

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get the database URL
    db_url = get_database_url()

    # Create a new SQLAlchemy configuration dictionary
    # This will be used by engine_from_config
    cfg = config.get_section(config.config_ini_section)
    if cfg is None:
        cfg = {} # Ensure cfg is a dictionary
    cfg["sqlalchemy.url"] = db_url # Override URL from alembic.ini with the one from env var

    connectable = engine_from_config(
        cfg, # Use the modified configuration
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
