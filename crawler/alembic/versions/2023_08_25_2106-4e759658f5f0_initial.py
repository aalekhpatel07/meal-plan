"""Setup tables in the schema.

Revision ID: 4e759658f5f0
Revises: 
Create Date: 2023-08-25 21:06:24.055693

"""
from typing import Sequence, Union

import sqlalchemy
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e759658f5f0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scraped_recipe",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("create_date", sa.DateTime, server_default=sqlalchemy.text('NOW()')),
        sa.Column("payload", sa.JSON, nullable=True),
    )
    op.create_table(
        "ingredient",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("canonical_name", sa.String(255), nullable=False)
    )
    op.create_table(
        "measurement_unit",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False)
    )
    op.create_table(
        "recipe",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("instructions", sa.ARRAY(sa.Text), nullable=True),
        sa.Column("scraped_extra", sa.JSON, nullable=True)
    )

    op.create_table(
        "recipe_ingredient",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ingredient_id", sa.Integer, sa.ForeignKey("ingredient.id", ondelete='RESTRICT'), nullable=False),
        sa.Column("recipe_id", sa.Integer, sa.ForeignKey("recipe.id", ondelete='RESTRICT'), nullable=False),
        sa.Column(
            "measurement_unit_id",
            sa.Integer,
            sa.ForeignKey("measurement_unit.id", ondelete='RESTRICT'),
            nullable=False
        ),
        sa.Column("extra_notes", sa.String(255), nullable=True),
        sa.Column("quantity", sa.Float, nullable=True)
    )


def downgrade() -> None:
    op.drop_table('scraped_recipe')
    op.drop_table('recipe_ingredient')
    op.drop_table('recipe')
    op.drop_table('ingredient')
    op.drop_table('measurement_unit')
