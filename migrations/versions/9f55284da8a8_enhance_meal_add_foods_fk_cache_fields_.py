# File: migrations/versions/9f55284da8a8_enhance_meal_add_foods_fk_cache_fields_.py

"""Enhance Meal: add foods FK, cache fields & constraint

Revision ID: 9f55284da8a8
Revises: bca06142ced1
Create Date: 2025-08-04 17:00:46.432348
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9f55284da8a8'
down_revision = 'bca06142ced1'
branch_labels = None
depends_on = None

def upgrade():
    # Garantiza que cualquier rastro previo de la tabla (meal o meals) sea removido
    op.execute('DROP TABLE IF EXISTS meal;')
    op.execute('DROP TABLE IF EXISTS meals;')

    # Crea la tabla 'meals' con la estructura definitiva
    op.create_table(
        'meals',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('food_id', sa.Integer(), sa.ForeignKey('foods.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('time', sa.Time(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('calories', sa.Integer(), nullable=False),
        sa.Column('protein', sa.Integer(), nullable=False),
        sa.Column('carbs', sa.Integer(), nullable=False),
        sa.Column('fats', sa.Integer(), nullable=False),
        sa.Column('meal_type', sa.String(length=20), nullable=False),
        sa.CheckConstraint('quantity > 0', name='check_meal_quantity_positive'),
    )


def downgrade():
    # En rollback, elimina la tabla 'meals'
    op.drop_table('meals')
