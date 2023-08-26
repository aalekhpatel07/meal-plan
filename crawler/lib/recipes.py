import datetime
import typing

from sqlalchemy import Integer, String, ForeignKey, JSON, Table, Column, ARRAY, Text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy import create_engine
from crawler import settings
from urllib.parse import quote_plus
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base


def _get_engine_url():
    postgres_config = settings.config["postgres"]
    user = quote_plus(postgres_config["user"])
    password = quote_plus(postgres_config["password"])
    host = quote_plus(postgres_config["host"])
    port = quote_plus(postgres_config["port"])
    database = quote_plus(postgres_config["database"])
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


engine = create_engine(_get_engine_url(), echo=False)

Session = sessionmaker(engine)


Base = declarative_base(
    type_annotation_map={dict[str, typing.Any]: JSON, list[str]: ARRAY(Text)}
)


class RecipeRaw(Base):
    __tablename__ = "scraped_recipe"

    id: Mapped[int] = mapped_column(primary_key=True)
    create_date: Mapped[datetime.datetime]
    payload: Mapped[dict[str, typing.Any]]

    def __repr__(self):
        return f"Recipe(id={self.id!r}, create_date={self.create_date!r}payload={self.payload!r})"


class Recipe(Base):
    __tablename__ = "recipe"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str]
    url: Mapped[str]
    instructions: Mapped[list[str]]
    scraped_extra: Mapped[dict[str, typing.Any]]


class Ingredient(Base):
    __tablename__ = "ingredient"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_name: Mapped[str]

    def __repr__(self):
        return f"Ingredient(id={self.id!r}, canonical_name={self.canonical_name!r})"


class MeasurementUnit(Base):
    __tablename__ = "measurement_unit"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

    def __repr__(self):
        return f"Unit(id={self.id!r}, name={self.canonical_name!r})"


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredient"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id"))
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredient.id"))
    measurement_unit_id: Mapped[int] = mapped_column(ForeignKey("measurement_unit.id"))
    quantity: Mapped[float]
    extra_notes: Mapped[str]
