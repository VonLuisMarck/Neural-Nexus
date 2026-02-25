from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from datetime import timedelta

from rbac import authenticate_user

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def init_jwt(app, secret_key: str):
    app.config["JWT_SECRET_KEY"] = secret_key
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
    jwt = JWTManager(app)
    return jwt


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    username = data.get("username", "")
    password = data.get("password", "")

    user = authenticate_user(username, password)
    if not user:
        return jsonify({"error": "invalid_credentials"}), 401

    identity = {
        "username": user["username"] if "username" in user else username,
        "role": user["role"],
        "scopes": user["scopes"],
    }
    access_token = create_access_token(identity=identity)
    return jsonify(
        {
            "access_token": access_token,
            "user": identity,
        }
    )


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    identity = get_jwt_identity()
    return jsonify(identity)
