from utils.helpers import sanitize


def find_by_id(entity_id: int):
    clean_id = sanitize(entity_id)
    return {"id": clean_id, "name": "test"}
