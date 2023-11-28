from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    def __repr__(self) -> str:
        return '\t|\t'.join(map(str, self.__dict__.values()))


class Chat(Base):
    __tablename__ = 'chats'
    id: Mapped[int] = mapped_column(primary_key=True, unique=True, index=True, nullable=False)


class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[int] = mapped_column(primary_key=True, unique=True, index=True, nullable=False)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"))
    chat: Mapped["Chat"] = relationship(back_populates="messages")
    user_id: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(nullable=False)
    scan_result: Mapped[str] = mapped_column(nullable=False)


class Admin(Base):
    __tablename__ = 'admins'
    id: Mapped[int] = mapped_column(primary_key=True, unique=True, index=True, nullable=False)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"))
    chat: Mapped["Chat"] = relationship(back_populates="admins")
    user_id: Mapped[int] = mapped_column()
