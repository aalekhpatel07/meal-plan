#!/usr/bin/env python
import sys
import typing

from lib.recipes import Session, RecipeRaw
from sqlalchemy import select
from tqdm import tqdm
from pprint import pprint


def main():
    with Session() as session:
        for raw in tqdm(session.scalars(select(RecipeRaw)).all()):
            process_recipe(raw)
            break


def process_recipe(
    raw: RecipeRaw
):
    # breakpoint()
    pprint(raw.payload, indent=4)
    pass


if __name__ == '__main__':
    main()
