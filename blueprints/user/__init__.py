from flask import Blueprint

user_bp = Blueprint('user', __name__)

from blueprints.user import routes  # noqa
