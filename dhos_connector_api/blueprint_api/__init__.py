import os
from typing import Dict, Optional

from flask import Blueprint, Response, current_app, jsonify, make_response, request
from flask_batteries_included.helpers import schema
from flask_batteries_included.helpers.security import protected_route
from flask_batteries_included.helpers.security.endpoint_security import scopes_present
from she_logging import logger

from dhos_connector_api.blueprint_api import receive_controller, transmit_controller
from dhos_connector_api.models.hl7_message import Hl7Message

api_blueprint = Blueprint("api", __name__)

# Set here to avoid app config issues with blueprints
# Default value set as the presence of this env var is validated elsewhere
EPR_SERVICE_ADAPTER_ISSUER = os.getenv("EPR_SERVICE_ADAPTER_ISSUER", None)
INTERNAL_ISSUER = os.getenv("PROXY_URL", None)
if INTERNAL_ISSUER is not None and not INTERNAL_ISSUER.endswith("/"):
    INTERNAL_ISSUER += "/"


@api_blueprint.route("/dhos/v1/message", methods=["POST"])
@protected_route(
    scopes_present(required_scopes="write:hl7_message"),
    allowed_issuers=[EPR_SERVICE_ADAPTER_ISSUER, INTERNAL_ISSUER],
)
def create_and_process_message(message_details: dict) -> Response:
    """---
    post:
      summary: Submit a new message
      description: >-
        Submit a new HL7 message to the platform.
        The message will be processed asynchronously, but ACKed synchronously.
      tags: [message]
      requestBody:
          description: "JSON body containing base64-encoded HL7 message"
          required: true
          content:
            application/json:
                schema:
                    $ref: '#/components/schemas/MessageRequest'
                    x-body-name: message_details
      responses:
        '200':
            description: "Message response"
            content:
                application/json:
                    schema: MessageResponse
        default:
            description: >-
                Error, e.g. 400 Bad Request, 503 Service Unavailable
            content:
              application/json:
                schema: Error
    """
    message_body: str = message_details["body"]

    return jsonify(
        receive_controller.create_and_process_hl7_message(body_b64=message_body)
    )


@api_blueprint.route("/dhos/v1/message/<message_uuid>", methods=["PATCH"])
@protected_route(
    scopes_present(required_scopes="write:hl7_message"), allowed_issuers=INTERNAL_ISSUER
)
def update_message(message_uuid: str, update_details: dict) -> Response:
    """---
    patch:
      summary: Update a message
      description: >-
        Marks an existing message as processed
      tags: [message]
      parameters:
        - in: path
          required: true
          schema: MessageUUID
      requestBody:
          description: "JSON body containing base64-encoded HL7 message"
          required: true
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MessageUpdate'
                x-body-name: update_details
      responses:
        '204':
            description: "Successful update"
        default:
            description: >-
                Error, e.g. 400 Bad Request, 404 Not Found, 503 Service Unavailable
            content:
              application/json:
                schema: Error
    """
    receive_controller.update_hl7_message(message_uuid, update_details)
    return make_response("", 204)


@api_blueprint.route("/dhos/v1/oru_message", methods=["POST"])
@protected_route(
    scopes_present(required_scopes="write:hl7_message"), allowed_issuers=INTERNAL_ISSUER
)
def create_oru_message() -> Response:
    """---
    post:
      summary: Generate an ORU message
      description: >-
        Generates an ORU message based on the provided data
      tags: [message]
      requestBody:
          description: >-
            JSON body containing process_obs_set action with
            patient, clinician, encounter, obs_set data
          required: true
          content:
            application/json:
              schema: ProcessObservationSet
      responses:
        '204':
            description: "Successful generation of ORU"
        default:
            description: >-
                Error, e.g. 400 Bad Request, 503 Service Unavailable
            content:
              application/json:
                schema: Error
    """
    if not request.is_json:
        raise ValueError("Request requires a JSON body")

    message_details = schema.post(required={"actions": [dict]}, optional={})
    data: Optional[Dict] = next(
        (
            a["data"]
            for a in message_details.get("actions", [])
            if a["name"] == "process_observation_set"
        ),
        None,
    )

    if data is None:
        raise ValueError(
            "Request requires a 'process_observation_set' action with data"
        )
    transmit_controller.create_oru_message(data)
    return make_response("", 204)


@api_blueprint.route("/dhos/v1/message/<message_uuid>", methods=["GET"])
@protected_route(
    scopes_present(required_scopes="read:hl7_message"), allowed_issuers=INTERNAL_ISSUER
)
def get_hl7_message(message_uuid: str) -> Response:
    """---
    get:
      summary: Get a message by UUID
      description: >-
        Returns a single message with the specified UUID or error 404 if there is no such message
      tags: [message]
      parameters:
        - in: path
          required: true
          schema: MessageUUID
      responses:
        '200':
            description: "Message response"
            content:
                application/json:
                    schema: MessageResponse
        default:
            description: >-
                Error, e.g. 400 Bad Request, 404 Not Found
            content:
              application/json:
                schema: Error
    """
    return jsonify(receive_controller.get_hl7_message(message_uuid))


@api_blueprint.route("/dhos/v1/message/search/<message_control_id>", methods=["GET"])
@protected_route(
    scopes_present(required_scopes="read:hl7_message"), allowed_issuers=INTERNAL_ISSUER
)
def get_hl7_message_by_message_control_id(message_control_id: str) -> Response:
    """---
    get:
      summary: Get a message by message control id
      description: >-
        Returns a list of messages with the specified message control id. If there are
        no matching messages the call is successful and the list is empty.
      tags: [message]
      parameters:
        - in: path
          required: true
          schema: MessageControlId
      responses:
        '200':
            description: "An array with zero or more matching messages"
            content:
              application/json:
                schema:
                  type: array
                  items: MessageResponse
        default:
            description: >-
                Error, e.g. 400 Bad Request
            content:
              application/json:
                schema: Error
    """
    return jsonify(
        receive_controller.get_hl7_message_by_message_control_id(message_control_id)
    )


@api_blueprint.route("/dhos/v1/message/search", methods=["GET"])
@protected_route(
    scopes_present(required_scopes="read:hl7_message"), allowed_issuers=INTERNAL_ISSUER
)
def get_hl7_message_by_identifier(identifier_type: str, identifier: str) -> Response:
    """---
    get:
      summary: Get a message by identifier
      description: >-
        Returns a list of messages with the specified identifier. If there are
        no matching messages the call is successful and the list is empty.
      tags: [message]
      parameters:
        - name: identifier_type
          in: query
          required: true
          example: MRN
          schema:
            type: string
        - name: identifier
          in: query
          example: 1112225
          required: true
          schema:
            type: string
      responses:
        '200':
            description: "An array with zero or more matching messages"
            content:
              application/json:
                schema:
                  type: array
                  items: MessageResponse
        default:
            description: >-
                Error, e.g. 400 Bad Request
            content:
              application/json:
                schema: Error
    """
    return jsonify(
        receive_controller.get_hl7_message_by_identifier(
            identifier_type=identifier_type, identifier=identifier
        )
    )


@api_blueprint.route("/dhos/v1/cda_message", methods=["POST"])
@protected_route(
    scopes_present(required_scopes="write:hl7_message"), allowed_issuers=INTERNAL_ISSUER
)
def create_cda_message() -> Response:
    """---
    post:
      summary: Forward an HL7 v3 CDA message to trust
      description: >-
        Creates a CDA message and attempts to forward it to the Trust.
        If forwarding fails the message is posted to the failed request queue to be retried later.
      tags: [message]
      requestBody:
          description: "JSON body containing XML HL7 v3 CDA message"
          required: true
          content:
            application/json:
                schema: CDAMessageRequest
      responses:
        '201':
            description: "Message created successfully"
        default:
            description: >-
                Error, e.g. 400 Bad Request, 501 Not configured for this trust
            content:
              application/json:
                schema: Error
    """
    if not request.is_json:
        raise ValueError("Request requires a JSON body")

    _json = schema.post(required={"content": str, "type": str}, optional={})

    if _json["type"] != "HL7v3CDA":
        raise ValueError("Unsupported CDA message type %s", _json["type"])

    mirth_url_base = current_app.config["MIRTH_HOST_URL_BASE"]
    if not mirth_url_base:
        logger.warning("Not sending CDA message due to config")
        return make_response("", 501)

    message_uuid: str = transmit_controller.create_and_save_cda_message(
        cda_message=_json["content"]
    )

    # We track failed requests to Mirth by message uuid.
    try:
        transmit_controller.post_hl7_message(hl7_message_uuid=message_uuid)
    except OSError:
        # We pass over this error because if we return an error code, rabbit will retry :(
        logger.warning(
            "Failed to send ORU message, will be handled by failed request queue",
            extra={"hl7_message_uuid": message_uuid},
        )

    return make_response("", 201)
