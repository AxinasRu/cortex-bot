import datetime

from sqlalchemy import ForeignKey, func, DateTime, Computed
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    def __repr__(self) -> str:
        return '\n'.join(map(
            lambda x: f"{x[0]}\t{x[1]}",
            self.__dict__.items()
        ))


class Queue(Base):
    __tablename__ = 'queue'
    id: Mapped[int] = mapped_column(primary_key=True, unique=True, index=True, nullable=False, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, server_default='in_work')


class Log(Base):
    __tablename__ = 'log'
    id: Mapped[int] = mapped_column(primary_key=True, unique=True, index=True, nullable=False)
    chat_id: Mapped[int] = mapped_column(nullable=False)
    user_id: Mapped[int] = mapped_column(nullable=False)
    datetime: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    message_id: Mapped['int'] = mapped_column(ForeignKey("messages.id"))
    message: Mapped['Message'] = relationship()


class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[int] = mapped_column(primary_key=True, unique=True, index=True, nullable=False)
    text: Mapped[str] = mapped_column(nullable=False, unique=True)
    translated: Mapped[str] = mapped_column(nullable=False)
    scan_sexual: Mapped[int] = mapped_column(nullable=False)
    scan_hate: Mapped[int] = mapped_column(nullable=False)
    scan_harassment: Mapped[int] = mapped_column(nullable=False)
    scan_self_harm: Mapped[int] = mapped_column(nullable=False)
    scan_sexual_minors: Mapped[int] = mapped_column(nullable=False)
    scan_hate_threatening: Mapped[int] = mapped_column(nullable=False)
    scan_violence_graphic: Mapped[int] = mapped_column(nullable=False)
    scan_self_harm_intent: Mapped[int] = mapped_column(nullable=False)
    scan_self_harm_instructions: Mapped[int] = mapped_column(nullable=False)
    scan_harassment_threatening: Mapped[int] = mapped_column(nullable=False)
    scan_violence: Mapped[int] = mapped_column(nullable=False)
    scan_summary: Mapped[int] = mapped_column(
        nullable=False,
        server_default=Computed(
            "scan_sexual + scan_hate + scan_harassment + scan_self_harm + scan_sexual_minors + "
            "scan_hate_threatening + scan_violence_graphic + scan_self_harm_intent + "
            "scan_self_harm_instructions + scan_harassment_threatening + scan_violence"
        )
    )
