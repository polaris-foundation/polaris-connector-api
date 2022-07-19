from pathlib import Path

import connexion
import kombu_batteries_included
from connexion import FlaskApp
from flask import Flask
from flask_batteries_included import augment_app as fbi_augment_app
from flask_batteries_included.config import is_not_production_environment
from flask_batteries_included.sqldb import db, init_db

from dhos_connector_api import blueprint_api, blueprint_development
from dhos_connector_api.config import init_config
from dhos_connector_api.helpers.cli import add_cli_command


def create_app(
    testing: bool = False, use_pgsql: bool = True, use_sqlite: bool = False
) -> Flask:
    connexion_app: FlaskApp = connexion.App(
        __name__,
        specification_dir=Path(__file__).parent / "openapi",
        options={"swagger_ui": is_not_production_environment()},
    )
    connexion_app.add_api("openapi.yaml", strict_validation=True)
    app: Flask = fbi_augment_app(
        app=connexion_app.app,
        use_pgsql=use_pgsql,
        use_sqlite=use_sqlite,
        use_auth0=True,
        testing=testing,
    )

    # Configure the SQL database
    init_db(app=app, testing=testing)

    init_config(app)

    # Initialise k-b-i library to allow publishing to RabbitMQ.
    kombu_batteries_included.init()

    # Blueprint registration
    app.register_blueprint(blueprint_api.api_blueprint)
    app.logger.info("Registered API blueprint")

    if is_not_production_environment():
        app.register_blueprint(blueprint_development.development_blueprint)

    add_cli_command(app)

    if testing:
        with app.app_context():
            db.create_all()

    return app
