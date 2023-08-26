#!/usr/bin/env python
import dataclasses
import datetime
import json
import logging
import os
import sys
import typing
import re

import openai
from lib.recipes import (
    Session,
    RecipeRaw,
)
from crawler import settings
from sqlalchemy import select
from tqdm import tqdm
import redis
import structlog
import logging


cache = redis.StrictRedis(
    host=settings.config["redis"]["host"],
    port=settings.config["redis"]["port"]
)


logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.ERROR
)

structlog.configure()

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


def main():
    with Session(autoflush=True) as session:
        for raw in tqdm(session.scalars(select(RecipeRaw)).all()):
            parse_ingredients(raw)
        session.rollback()


IGNORE_INGREDIENTS = {
    "Butter",
    "Ice",
    "Salt"
}


def ask_chat_gpt_to_parse_ingredients(recipe_id: int, raw_ingredients: typing.Iterable[str], cache: redis.StrictRedis):
    """

    @return:
    """

    prompt = f"""Given the following free form ingredients for a recipe, transform each of these into four
    categories called "quantity" (as a float or null), a "unit", "canonical_name", and "extra_notes". Please 
    only return valid JSON data and no other text in the response.
    
    """

    for ingredient in raw_ingredients:
        prompt += "- " + ingredient + "\n"

    try:
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=1000
        )
    except openai.error.OpenAIError as err:
        logger.exception(f"OpenAI error: {err}", recipe_id=recipe_id)
        cache.rpush(f"chat_gpt_parse_error", recipe_id)
        raise

    choices = response.get("choices", [])
    if not len(choices):
        return None
    contents = choices[0]["text"]
    try:
        return json.loads(contents)
    except Exception:  # noqa
        return None


def skip_stop_words(raw_ingredient: str):
    ingredient_blocks = raw_ingredient.split(" ", 2)
    *measurements, raw_ingredient = ingredient_blocks
    if raw_ingredient.endswith("*"):
        # This is probably some ingredient that is expected in the pantry.
        return False
    if any(raw_ingredient.lower().endswith(common_item.lower()) for common_item in IGNORE_INGREDIENTS):
        return False
    return True


def parse_ingredients(recipe: RecipeRaw) -> typing.List[typing.Dict[str, typing.Any]]:
    """

    @param recipe:
    @return:
    """

    # Only look at english recipes for now.
    if not recipe.payload["language"].startswith("en-"):
        logger.error(
          "Rejecting recipe because it is not English",
          language=recipe.scraped_extra["language"],
          recipe=recipe.id
        )
        return []

    ingredients_to_parse = list(filter(
        skip_stop_words,
        map(str, recipe.payload["ingredients"])  # noqa
    ))
    if not len(ingredients_to_parse):
        return []

    parsed_ingredients = cache.get(f"chat_gpt3_parsed:{recipe.id}")
    if parsed_ingredients is None:
        parsed_ingredients = ask_chat_gpt_to_parse_ingredients(recipe.id, ingredients_to_parse, cache=cache)
        if not parsed_ingredients:
            logger.error(
                "GPT-3 failed to parse ingredients.",
                recipe=recipe.id,
                ingredients_to_parse=ingredients_to_parse
            )
        cache.setex(f"chat_gpt3_parsed:{recipe.id}", datetime.timedelta(days=180), json.dumps(parsed_ingredients))
    else:
        parsed_ingredients = json.loads(parsed_ingredients or [])

    return parsed_ingredients


if __name__ == '__main__':
    main()
