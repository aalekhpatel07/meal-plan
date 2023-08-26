import typing

from sqlalchemy import select

from lib.recipes import (
    Session,
    RecipeRaw,
    Recipe,
    RecipeIngredient,
    Ingredient,
    MeasurementUnit
)
from tqdm import tqdm
from crawler import settings
import redis
import json


cache = redis.StrictRedis(
    host=settings.config["redis"]["host"],
    port=settings.config["redis"]["port"]
)


def get_ingredients(recipe_id: int) -> typing.Optional[typing.List[typing.Dict[str, typing.Any]]]:
    return json.loads(cache.get(f"chat_gpt3_parsed:{recipe_id}"))


def main():
    with Session(autoflush=True) as session:
        for raw in tqdm(session.scalars(select(RecipeRaw)).all()):
            ingredients_parsed = get_ingredients(raw)

        session.rollback()


def _get_or_create_ingredient(session, name: str) -> Ingredient:
    stmt = (
        select(Ingredient)
        .where(Ingredient.canonical_name == name)
    )
    row = session.scalar(stmt)
    if row:
        return row

    row = Ingredient(canonical_name=name)
    session.add(row)
    return row


def _get_or_create_measurement_unit(session, name: str) -> Ingredient:
    stmt = (
        select(MeasurementUnit)
        .where(MeasurementUnit.name == name)
    )
    row = session.scalar(stmt)
    if row:
        return row

    record = MeasurementUnit(name=name)
    session.add(record)
    return record


def parse_recipe(raw: RecipeRaw, session) -> Recipe:
    contents = dict(raw.payload)
    name = contents.pop("title", None)
    url = contents.pop("canonical_url", None)
    description = contents.pop("description", None)
    instructions = contents.pop("instructions_list", None)
    extra = contents

    # # Get the recipe by url initially.
    recipe_stmt = (
        select(Recipe)
        .where(Recipe.url == url)
    )

    recipe = session.scalar(recipe_stmt)
    if recipe:
        return recipe

    recipe = Recipe(
        id=raw.id,
        url=url,
        name=name,
        description=description,
        instructions=instructions,
        scraped_extra=extra
    )
    session.add(recipe)
    return recipe
