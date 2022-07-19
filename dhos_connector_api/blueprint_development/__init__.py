from flask import Blueprint, Response, current_app, make_response
from flask_batteries_included.sqldb import db

development_blueprint = Blueprint("dhos/dev", __name__)


@development_blueprint.route("/drop_data", methods=["POST"])
def drop_data_route() -> Response:

    if current_app.config["ALLOW_DROP_DATA"] is not True:
        raise PermissionError("Cannot drop data in this environment")

    session = db.session
    session.execute("TRUNCATE TABLE hl7_message")
    session.commit()
    session.close()
    return make_response(204)
