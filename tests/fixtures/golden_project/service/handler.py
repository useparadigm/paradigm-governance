from domain.models import User
from infra.db import query


def handle_request(action: str, entity_id: int = 0):
    if action == "get_user":
        row = query("users", entity_id)
        return User(name=row["name"], email=row["email"])
    return None
