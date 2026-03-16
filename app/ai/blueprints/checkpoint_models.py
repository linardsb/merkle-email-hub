"""SQLAlchemy model for blueprint checkpoint persistence."""

from typing import Any

from sqlalchemy import Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.models import TimestampMixin


class BlueprintCheckpoint(Base, TimestampMixin):
    """Persisted checkpoint after a successful blueprint node execution."""

    __tablename__ = "blueprint_checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    blueprint_name: Mapped[str] = mapped_column(String(100), nullable=False)
    node_name: Mapped[str] = mapped_column(String(100), nullable=False)
    node_index: Mapped[int] = mapped_column(Integer, nullable=False)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    html_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256

    __table_args__ = (Index("ix_checkpoint_run_node", "run_id", "node_index"),)
