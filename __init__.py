import os
from flask import Flask
from dotenv import load_dotenv
from extensions import db
from config import config

load_dotenv()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Static file caching (1 year for production)
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000

    # Fix DATABASE_URL for PostgreSQL (Render uses postgres:// but SQLAlchemy needs postgresql://)
    database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if database_url.startswith('postgres://'):
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace('postgres://', 'postgresql://', 1)

    # Initialize extensions
    db.init_app(app)

    # Register Jinja2 filters
    from utils import utc_to_ist
    app.jinja_env.filters['utc_to_ist'] = utc_to_ist

    # Register error handlers
    from flask import render_template as _rt
    @app.errorhandler(404)
    def page_not_found(e):
        return _rt('main/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        return _rt('main/404.html'), 500

    # Register blueprints
    from blueprints.main import main_bp
    from blueprints.auth import auth_bp
    from blueprints.user import user_bp
    from blueprints.admin.routes import admin_bp
    from blueprints.superadmin.routes import superadmin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(superadmin_bp)

    return app
