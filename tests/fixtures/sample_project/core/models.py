class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email


class Project:
    def __init__(self, title: str, owner: User):
        self.title = title
        self.owner = owner


def validate_email(email: str) -> bool:
    return "@" in email
