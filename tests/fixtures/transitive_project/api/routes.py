from service.handler import handle_request


def get_user(user_id: int):
    return handle_request("get_user", user_id)
