"""Ingest scraped data

Revision ID: 6ca5404325f5
Revises: 4e759658f5f0
Create Date: 2023-08-25 22:05:27.147379

"""
from typing import Sequence, Union
import json
from pathlib import Path

from alembic import op
from lib.recipes import RecipeRaw


# revision identifiers, used by Alembic.
revision: str = '6ca5404325f5'
down_revision: Union[str, None] = '4e759658f5f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    recipe_file = Path("data/recipes.json")
    with open(recipe_file, "r") as f:
        recipes = json.load(f)

    op.bulk_insert(
        RecipeRaw.__table__,
        recipes,
    )


def downgrade() -> None:
    op.execute("delete from scraped_recipe")
