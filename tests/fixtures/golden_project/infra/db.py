from domain.models import User


def query(table: str, record_id: int) -> dict:
    return {"name": "test", "email": "test@example.com"}


def save(table: str, data: dict) -> int:
    return 1


def get_user_model() -> type:
    return User
