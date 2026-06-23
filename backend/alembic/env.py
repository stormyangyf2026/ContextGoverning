import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from environment
config.set_main_option(
    "sqlalchemy.url",
    os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
)

from app.models.base import Base
# Import all models to register them with Base metadata
import app.models.context     # noqa: F401
import app.models.entity      # noqa: F401
import app.models.relation    # noqa: F401
import app.models.user        # noqa: F401
import app.models.permission  # noqa: F401
import app.models.audit       # noqa: F401
import app.models.tag         # noqa: F401
import app.models.push_rule   # noqa: F401
import app.models.notification # noqa: F401
import app.models.push_log    # noqa: F401
import app.models.system_config # noqa: F401
import app.models.user_setting # noqa: F401
import app.models.config_change_log # noqa: F401
import app.models.workspace   # noqa: F401
import app.models.api_key     # noqa: F401
import app.models.jwt_config  # noqa: F401
import app.models.webhook_delivery_log # noqa: F401
import app.models.context_entity # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
