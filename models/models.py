from sqlalchemy import ForeignKey, String, Integer, Date, Table, Column
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, sessionmaker, relationship
from sqlalchemy import create_engine
import asyncio

engine = create_async_engine(url="sqlite+aiosqlite:///db.sqlite3")

async_session = async_sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


user_starfilm = Table(
    "user_starfilm",
    Base.metadata,
    Column("user_id", ForeignKey("user_table.id"), primary_key=True),
    Column("starfilm_id", ForeignKey("starfilm_table.id"), primary_key=True)
)


class User(Base):
    __tablename__ = "user_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(20))
    password: Mapped[str] = mapped_column(String(100))
    stars: Mapped[list["StarredFilm"]] = relationship(
        "StarredFilm", secondary=user_starfilm, back_populates='fans'
    )


class StarredFilm(Base):
    __tablename__ = "starfilm_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    film_id: Mapped[int] = mapped_column(Integer())
    imdb_id: Mapped[int] = mapped_column(Integer())
    film_name: Mapped[str] = mapped_column(String(40))
    year: Mapped[int] = mapped_column(Integer())
    film_length: Mapped[int] = mapped_column(Integer())
    film_poster: Mapped[str] = mapped_column(String())
    film_link: Mapped[str] = mapped_column(String())

    fans: Mapped[list["User"]] = relationship(
        "User", secondary=user_starfilm, back_populates="stars"
    )


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main():
    await init_db()


if __name__ == "__main__":
    asyncio.run(main())
