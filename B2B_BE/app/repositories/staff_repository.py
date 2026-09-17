from sqlalchemy.orm import Session

from app.models.staff import Staff


def get_staff_by_phone_number(db: Session, phone_number: str) -> Staff | None:
    """Look up a Staff record by its exact, unique phone number."""
    return db.query(Staff).filter(Staff.phone_number == phone_number).one_or_none()


def get_staff_by_name(db: Session, name: str) -> Staff | None:
    """Look up a Staff record by its exact name.

    Mirrors ``get_staff_by_phone_number``. ``name`` is not guaranteed unique
    at the schema level (no unique constraint on ``staff.name``); this
    returns the first match, which is sufficient for this ticket's narrow
    scope of resolving ``ResolvedBookingCandidate.staff_name`` to a
    ``staff_id``.
    """
    return db.query(Staff).filter(Staff.name == name).first()
