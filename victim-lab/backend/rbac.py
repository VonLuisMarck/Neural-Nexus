USERS = {
    "alice": {
        "password": "alice123",
        "role": "viewer",
        "scopes": ["doc:public:read"],
    },
    "bob": {
        "password": "bob123",
        "role": "analyst",
        "scopes": ["doc:public:read", "doc:sensitive:read"],
    },
    "carol": {
        "password": "carol123",
        "role": "admin",
        "scopes": ["doc:public:read", "doc:sensitive:read", "doc:secret:read"],
    },
    "mallory": {
        "password": "mallory123",
        "role": "attacker",
        "scopes": ["doc:public:read"],
    },
}

CLASSIFICATION_SCOPE_MAP = {
    "public": "doc:public:read",
    "sensitive": "doc:sensitive:read",
    "secret": "doc:secret:read",
}


def authenticate_user(username: str, password: str):
    user = USERS.get(username)
    if not user or user["password"] != password:
        return None
    return {
        "username": username,
        "role": user["role"],
        "scopes": user["scopes"],
    }


def user_has_scope(user, scope: str) -> bool:
    return scope in (user.get("scopes") or [])


def can_read_classification(user, classification: str) -> bool:
    required = CLASSIFICATION_SCOPE_MAP.get(classification)
    if not required:
        return False
    return user_has_scope(user, required)
