import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Aseguramos que la raíz del repo esté en sys.path para poder importar `api.*`
# cuando Alembic se ejecuta desde el directorio del proyecto.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Cargamos las variables de entorno del .env (mismo mecanismo que api.main),
# para que DATABASE_URL esté disponible al correr `alembic` desde la CLI.
try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    # dotenv es opcional en CI/producción (las vars ya vienen inyectadas).
    pass

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# La URL de la BD es la MISMA fuente de verdad que usa la app (api.core.config):
# se toma de la variable de entorno DATABASE_URL en vez de hardcodearla en
# alembic.ini, para no versionar credenciales y no divergir del runtime.
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata objetivo para el 'autogenerate': el mismo Base que declara los
# modelos de la app, de modo que `alembic revision --autogenerate` detecte
# cambios reales del esquema (tablas currencies y platform_dates).
from api.models.bd_currency import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
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
