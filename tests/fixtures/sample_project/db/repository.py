from core.models import User, Project


def save_user(user: User) -> None:
    pass


def get_user(user_id: int) -> User:
    return User(name="test", email="test@example.com")


def save_project(project: Project) -> None:
    pass
