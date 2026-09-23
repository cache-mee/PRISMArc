import enum
from datetime import UTC, datetime

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StaffRole(str, enum.Enum):
    OWNER_ADMIN = "owner_admin"
    STAFF = "staff"


class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False
    )
    role: Mapped[StaffRole] = mapped_column(
        Enum(
            StaffRole,
            name="staff_role",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), nullable=False
    )
