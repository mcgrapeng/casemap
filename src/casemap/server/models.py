"""SQLAlchemy 2.x ORM schema for casemap server (SP-2)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Single metadata set for create_all()."""


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
    llm_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String, nullable=True)

    specs: Mapped[list[Spec]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Spec(Base):
    __tablename__ = "specs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    project: Mapped[Project] = relationship(back_populates="specs")
    graphs: Mapped[list[Graph]] = relationship(
        back_populates="spec", cascade="all, delete-orphan"
    )


class Graph(Base):
    __tablename__ = "graphs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    spec_id: Mapped[str] = mapped_column(
        ForeignKey("specs.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    graph_data: Mapped[str] = mapped_column(Text, nullable=False)
    svg_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    html_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    case_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    spec: Mapped[Spec] = relationship(back_populates="graphs")
    project: Mapped[Project] = relationship()
    cases: Mapped[list[Case]] = relationship(
        back_populates="graph", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_graphs_project_id", "project_id"),)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    graph_id: Mapped[str] = mapped_column(
        ForeignKey("graphs.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    steps: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    endpoint_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    graph: Mapped[Graph] = relationship(back_populates="cases")
    project: Mapped[Project] = relationship()
    status: Mapped[Status | None] = relationship(
        back_populates="case", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        Index("ix_cases_project_id", "project_id"),
        Index("ix_cases_graph_id", "graph_id"),
    )


class Status(Base):
    __tablename__ = "statuses"

    case_id: Mapped[str] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="human")

    case: Mapped[Case] = relationship(back_populates="status")
    project: Mapped[Project] = relationship()

    __table_args__ = (Index("ix_statuses_project_id", "project_id"),)


__all__ = ["Base", "Project", "Spec", "Graph", "Case", "Status"]


# Re-import here for ruff; UniqueConstraint kept available for future use.
_ = UniqueConstraint
