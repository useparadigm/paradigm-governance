def sanitize(value: str) -> str:
    return value.strip()


def format_response(data: dict) -> dict:
    return {"status": "ok", "data": data}
