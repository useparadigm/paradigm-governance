"""A service that creates a circular dependency: core -> db -> core."""
from db.repository import save_user
from core.models import User


def create_default_user():
    user = User(name="default", email="default@example.com")
    save_user(user)
    return user
