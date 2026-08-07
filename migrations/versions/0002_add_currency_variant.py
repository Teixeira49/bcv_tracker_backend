"""agrega variant a currencies y la incorpora a la clave de negocio

Migración de esquema **y de datos** (issue #73).

Hasta ahora la identidad de una cotización era ``(code, platform)`` y el lado de
la operación viajaba dentro del ``name`` ("Tether-Buy"), que no forma parte de
ninguna clave. Las fuentes que publican varias series bajo el mismo código
—compra/venta en los P2P y en Airtm, oficial/paralelo en DolarAPI— mandan todas
sus series en el mismo lote, así que la segunda escritura pisaba a la primera y
solo sobrevivía una fila por moneda.

Esta revisión:

1. Agrega ``variant`` (NOT NULL, centinela ``'na'``). No es nullable a propósito:
   PostgreSQL y SQLite tratan los NULL como distintos entre sí en un índice
   único, así que con NULL el UNIQUE del paso 3 no protegería a las fuentes de
   una sola serie.
2. **Backfill**: deduce la variante de cada fila a partir de su ``name``. Donde
   hay filas gemelas —dos filas con el mismo ``(code, platform)``, creadas en la
   primera corrida de esa fuente, cuando ninguna de las dos inserciones veía a la
   otra— la de ``id`` más bajo conserva la serie que indica su nombre (es la que
   el upsert venía actualizando) y la gemela pasa a la serie complementaria. Así
   la fila huérfana se **reutiliza** en vez de borrarse: ninguna fila se elimina.
   A la gemela se le copia además el valor vigente de su hermana, para que el
   primer ROC tras la migración se calcule contra un valor fresco y no contra el
   que quedó congelado cuando dejó de actualizarse.
3. Crea ``UNIQUE (code, platform, variant)``, para que el upsert no pueda volver
   a generar gemelas.

Si algún ``(code, platform)`` trae más filas de las que se pueden desambiguar, el
backfill **aborta** con un mensaje explícito en vez de dejar datos a medias y
morir después en el UNIQUE.

Revision ID: 0002_add_currency_variant
Revises: 0001_initial_schema
Create Date: 2026-08-07
"""
from collections import OrderedDict
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_add_currency_variant"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UNIQUE_NAME = "uq_currencies_code_platform_variant"

VARIANT_NA = "na"
VARIANT_BUY = "buy"
VARIANT_SELL = "sell"
VARIANT_OFICIAL = "oficial"
VARIANT_PARALELO = "paralelo"

# Serie <-> serie hermana. Sirve para asignarle a una fila gemela la variante que
# le falta al par cuando su nombre no la distingue (las gemelas quedaron todas
# con el nombre de la serie que sobrevivía a la escritura).
COMPLEMENT = {
    VARIANT_SELL: VARIANT_BUY,
    VARIANT_BUY: VARIANT_SELL,
    VARIANT_PARALELO: VARIANT_OFICIAL,
    VARIANT_OFICIAL: VARIANT_PARALELO,
}


def _variant_from_name(name: str) -> str:
    """Deduce la variante a partir del nombre que la fila traía guardado.

    Los P2P y Airtm guardaban el lado como sufijo ("Tether-sell", "Dolar-buy") y
    DolarAPI guardaba la fuente como nombre completo ("Oficial", "Paralelo"). El
    resto de fuentes (BCV, Yadio, Exchange Monitor) publican una sola serie por
    moneda y se quedan en el centinela.
    """
    label = (name or "").strip().lower()
    if label.endswith("-" + VARIANT_BUY):
        return VARIANT_BUY
    if label.endswith("-" + VARIANT_SELL):
        return VARIANT_SELL
    if label in (VARIANT_OFICIAL, VARIANT_PARALELO):
        return label
    return VARIANT_NA


def _backfill_variants(conn) -> None:
    """Asigna su variante a cada fila existente, reutilizando las gemelas."""
    rows = conn.execute(
        sa.text(
            'SELECT id, code, platform, name, value, "updateDate" '
            "FROM currencies ORDER BY code, platform, id"
        )
    ).fetchall()

    groups = OrderedDict()
    for row in rows:
        groups.setdefault((row.code, row.platform), []).append(row)

    for (code, platform), group in groups.items():
        if len(group) > 2:
            raise RuntimeError(
                f"No se puede deducir la variante de {code}/{platform}: tiene "
                f"{len(group)} filas y el backfill solo sabe desambiguar hasta dos "
                "(la serie del nombre y su complementaria). Revisa esas filas a "
                "mano antes de aplicar la migración."
            )

        survivor = group[0]  # id más bajo: la fila que el upsert venía actualizando
        assigned = {}

        for position, row in enumerate(group):
            variant = _variant_from_name(row.name)
            if position > 0:
                # Fila gemela: quedó con el nombre de la serie que ganaba la
                # escritura, así que la que le corresponde es la complementaria.
                variant = COMPLEMENT.get(variant, variant)

            if variant in assigned:
                raise RuntimeError(
                    f"Las filas {assigned[variant]} y {row.id} de {code}/{platform} "
                    f"resuelven a la misma variante '{variant}'; el UNIQUE las "
                    "rechazaría. Revisa sus nombres antes de aplicar la migración."
                )
            assigned[variant] = row.id

            if position == 0:
                conn.execute(
                    sa.text("UPDATE currencies SET variant = :variant WHERE id = :id"),
                    {"variant": variant, "id": row.id},
                )
            else:
                # Además de estrenar variante, la gemela adopta el valor vigente
                # de su hermana: llevaba congelada desde que dejó de actualizarse
                # y con un valor de hace semanas el primer ROC saldría disparado.
                conn.execute(
                    sa.text(
                        "UPDATE currencies SET variant = :variant, value = :value, "
                        'change = 0.0, "updateDate" = :updated WHERE id = :id'
                    ),
                    {
                        "variant": variant,
                        "value": survivor.value,
                        "updated": survivor.updateDate,
                        "id": row.id,
                    },
                )


def upgrade() -> None:
    op.add_column(
        "currencies",
        sa.Column("variant", sa.String(), nullable=False, server_default=VARIANT_NA),
    )

    _backfill_variants(op.get_bind())

    # batch_alter_table: SQLite no soporta ADD CONSTRAINT y Alembic necesita
    # recrear la tabla para aplicarlo (en PostgreSQL emite el ALTER directo).
    with op.batch_alter_table("currencies") as batch_op:
        batch_op.create_unique_constraint(UNIQUE_NAME, ["code", "platform", "variant"])


def downgrade() -> None:
    # Revierte exactamente lo que hace upgrade(): quita el UNIQUE y la columna.
    # Las filas gemelas sobreviven (nunca se borraron), pero vuelven a quedar
    # indistinguibles entre sí, que es el estado previo a esta revisión.
    with op.batch_alter_table("currencies") as batch_op:
        batch_op.drop_constraint(UNIQUE_NAME, type_="unique")

    op.drop_column("currencies", "variant")
