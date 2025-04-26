from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped


class Base(DeclarativeBase):
    pass


class ScrapedData(Base):
    __tablename__ = "scraped_data"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = Column(String, nullable=False)
    title: Mapped[str] = Column(String, nullable=False)
    company: Mapped[str] = Column(String, nullable=False)
    industry: Mapped[str] = Column(String, nullable=True)
    salary: Mapped[str] = Column(String, nullable=True)
    location: Mapped[str] = Column(String, nullable=False)
    programming_languages: Mapped[str] = Column(String, nullable=False)
    responsibilities: Mapped[str] = Column(String, nullable=True)
    requirements: Mapped[str] = Column(String, nullable=False)
    extras: Mapped[str] = Column(String, nullable=True)


class CleanedData(Base):
    __tablename__ = "cleaned_data"

    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = Column(String, nullable=False, unique=True)
    title: Mapped[str] = Column(String, nullable=False)
    company: Mapped[str] = Column(String, nullable=False)
    industry: Mapped[str] = Column(String, nullable=True)
    salary: Mapped[float] = Column(Integer, nullable=True)
    location: Mapped[str] = Column(String, nullable=False)
    programming_languages: Mapped[str] = Column(String, nullable=False)
    responsibilities: Mapped[str] = Column(String, nullable=True)
    requirements: Mapped[str] = Column(String, nullable=False)
    extras: Mapped[str] = Column(String, nullable=True)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.now, nullable=True)
