from infra.db import query, save
from domain.models import User


def create_user(name: str, email: str) -> User:
    user = User(name=name, email=email)
    save("users", {"name": name, "email": email})
    return user


def find_user(user_id: int) -> User:
    row = query("users", user_id)
    return User(name=row["name"], email=row["email"])
