from sqlalchemy.orm import Session

from app.models.customer import Customer


def get_customer_by_phone(db: Session, phone_number: str) -> Customer | None:
    """Look up a Customer by phone number, or return ``None`` if none exists."""
    return db.query(Customer).filter(Customer.phone_number == phone_number).one_or_none()


def create_customer(db: Session, phone_number: str, name: str) -> Customer:
    """Insert a new Customer row and return it."""
    customer = Customer(phone_number=phone_number, name=name)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer
