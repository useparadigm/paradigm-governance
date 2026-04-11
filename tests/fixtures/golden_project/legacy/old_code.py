from domain.models import User
from infra.db import query


def legacy_get_user(user_id: int) -> User:
    row = query("users", user_id)
    return User(name=row["name"], email=row["email"])
