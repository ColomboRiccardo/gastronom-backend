import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Self-referential FK
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),  # Points to same table
        nullable=True  # NULL = top-level category
    )

    # Relationships
    parent: Mapped["Category | None"] = relationship(
        "Category",
        remote_side=[id],  # Required for self-referential
        back_populates="children"
    )
    children: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent"
    )