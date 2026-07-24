"""esquema inicial: tablas currencies y platform_dates

Refleja el esquema declarado por los modelos SQLAlchemy de la app
(``api/models/bd_currency.py``): las tablas ``currencies`` y ``platform_dates``.
Es la línea base de migraciones; a partir de aquí los cambios de esquema se
versionan con ``alembic revision --autogenerate``.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "currencies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("platform", sa.String(), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("change", sa.Float(), nullable=True),
        sa.Column("createDate", sa.DateTime(), nullable=False),
        sa.Column("updateDate", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_currencies_code"), "currencies", ["code"], unique=False)

    op.create_table(
        "platform_dates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("date", sa.String(), nullable=True),
        sa.Column("createDate", sa.DateTime(), nullable=False),
        sa.Column("updateDate", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform"),
    )


def downgrade() -> None:
    op.drop_table("platform_dates")
    op.drop_index(op.f("ix_currencies_code"), table_name="currencies")
    op.drop_table("currencies")
