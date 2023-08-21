import typing

from sqlalchemy import Integer, String, ForeignKey, JSON, Table, Column
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
    postgres_config = settings.config['postgres']
    user = quote_plus(postgres_config['user'])
    password = quote_plus(postgres_config['password'])
    host = quote_plus(postgres_config['host'])
    port = quote_plus(postgres_config['port'])
    database = quote_plus(postgres_config['database'])
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


engine = create_engine(
    _get_engine_url(),
    echo=True
)

Session = sessionmaker(engine)


Base = declarative_base(
    type_annotation_map={
        dict[str, typing.Any]: JSON
    }
)


class RecipeRaw(Base):
    __tablename__ = 'recipes'

    id: Mapped[int] = mapped_column(primary_key=True)
    payload: Mapped[dict[str, typing.Any]]

    def __repr__(self):
        return f"Recipe(id={self.id!r}, payload={self.payload!r})"


class Recipe(Base):
    __tablename__ = 'recipe_parsed'

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_url: Mapped[str]
    category: Mapped["Category"] = ForeignKey("Category.id")
    # category_id: Mapped[int] = mapped_column(ForeignKey("category.id"))
    # category:  Mapped["Category"] = relationship(back_populates="recipes")
    # ingredients: Mapped[typing.List["RecipeIngredient"]] = relationship(back_populates="recipe", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = 'category'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    # recipes: Mapped[typing.List["Recipe"]] = relationship("Recipe", back_populates="category")



class Ingredient(Base):
    __tablename__ = 'ingredient'

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_name: Mapped[str]
    variant: Mapped[str]
    # recipes: Mapped[typing.List["RecipeIngredient"]] = relationship(back_populates="ingredient", cascade="all, delete-orphan")

    def __repr__(self):
        return f"Ingredient(id={self.id!r}, canonical_name={self.canonical_name!r}, variant={self.variant!r})"


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredient"
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe_parsed.id"), primary_key=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredient.id"), primary_key=True)

    quantity: Mapped[float]

    # recipe: Mapped["Recipe"] = relationship(back_populates="recipes")
    # ingredient: Mapped["Ingredient"] = relationship(back_populates="ingredients")
