class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email


class Project:
    def __init__(self, title: str, owner: User):
        self.title = title
        self.owner = owner


class Team:
    def __init__(self, name: str):
        self.name = name
        self.members: list[User] = []


class Organization:
    def __init__(self, name: str):
        self.name = name


class Permission:
    def __init__(self, role: str, resource: str):
        self.role = role
        self.resource = resource


class AuditEntry:
    def __init__(self, action: str, actor: str):
        self.action = action
        self.actor = actor


class Settings:
    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value


class Notification:
    def __init__(self, message: str, target: str):
        self.message = message
        self.target = target
