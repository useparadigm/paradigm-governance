from service.handler import handle_request


def list_users():
    return handle_request("list_users")


def get_user(user_id: int):
    return handle_request("get_user", user_id)
