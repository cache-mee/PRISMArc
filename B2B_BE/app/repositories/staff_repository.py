from sqlalchemy.orm import Session

from app.models.staff import Staff


def get_staff_by_phone_number(db: Session, phone_number: str) -> Staff | None:
    """Look up a Staff record by its exact, unique phone number."""
    return db.query(Staff).filter(Staff.phone_number == phone_number).one_or_none()
