from db.repository import find_by_id


def handle_request(action: str, entity_id: int):
    return find_by_id(entity_id)
