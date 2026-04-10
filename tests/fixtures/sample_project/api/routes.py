from core.models import User
from db.repository import save_user, get_user
from utils.helpers import format_response


def create_user(name: str, email: str):
    user = User(name=name, email=email)
    save_user(user)
    return format_response({"id": 1, "name": name})


def get_user_route(user_id: int):
    user = get_user(user_id)
    return format_response({"name": user.name})
