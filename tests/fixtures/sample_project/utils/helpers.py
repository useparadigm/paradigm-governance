import json


def format_response(data: dict) -> str:
    return json.dumps(data)


def slugify(text: str) -> str:
    return text.lower().replace(" ", "-")
