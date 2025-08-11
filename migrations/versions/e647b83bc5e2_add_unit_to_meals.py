"""add unit to meals"""

from alembic import op
import sqlalchemy as sa

# Revisiones
revision = "e647b83bc5e2"
down_revision = "d23ce32fee16"  # <-- CAMBIA ESTO por el id real de tu última migración
branch_labels = None
depends_on = None


def upgrade():
    # 1) Añadimos columna 'unit' (nullable de forma temporal)
    with op.batch_alter_table("meals", schema=None) as batch_op:
        batch_op.add_column(sa.Column("unit", sa.String(length=10), nullable=True))

    # 2) Backfill: copiar desde foods.default_unit
    # SQLite: hacemos un UPDATE con subselect
    op.execute("""
        UPDATE meals
        SET unit = (
            SELECT COALESCE(LOWER(default_unit), 'g')
            FROM foods
            WHERE foods.id = meals.food_id
        )
        WHERE unit IS NULL
    """)

    # 3) Hacer no nula y añadir CHECK constraint
    with op.batch_alter_table("meals", schema=None) as batch_op:
        batch_op.alter_column("unit", existing_type=sa.String(length=10), nullable=False)
        batch_op.create_check_constraint(
            "ck_meals_unit",
            "unit IN ('g','ml','unidad')"
        )


def downgrade():
    with op.batch_alter_table("meals", schema=None) as batch_op:
        batch_op.drop_constraint("ck_meals_unit", type_="check")
        batch_op.drop_column("unit")
