from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import mapped_column, DeclarativeBase, Mapped, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

from config import ENGINE

engine = create_async_engine(ENGINE, echo=True)
async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str] = mapped_column(nullable=True)

    useritems: Mapped[list["UserItem"]] = relationship("UserItem", back_populates="user")


class UserItem(Base):
    __tablename__ = 'useritems'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=True)
    username: Mapped[str] = mapped_column(nullable=True)
    date: Mapped[str] = mapped_column(default='')

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))

    user: Mapped["User"] = relationship("User", back_populates="useritems")


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
