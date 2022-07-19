from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flask_batteries_included.helpers.apispec import (
    FlaskBatteriesPlugin,
    initialise_apispec,
    openapi_schema,
)
from marshmallow import EXCLUDE, INCLUDE, Schema, fields

dhos_connector_api_spec: APISpec = APISpec(
    version="1.0.0",
    openapi_version="3.0.3",
    title="DHOS Connector API",
    info={
        "description": "The DHOS Connector API is responsible for integration between DHOS and external sources of information."
    },
    plugins=[FlaskPlugin(), MarshmallowPlugin(), FlaskBatteriesPlugin()],
)

initialise_apispec(dhos_connector_api_spec)


EXAMPLE_MESSAGE = (
    "TVNIfF5+XFxcJnxjMDQ4MXxPWE9OfE9YT05fVElFX0FEVHxPWE9OfDIwMTcwNzMxMTQxMzQ4fHxBRFReQTAxfFE1NDkyOTE2ODJU"
    "NTUwNDU0MDU5WDE4MzkxQTEwOTZ8UHwyLjN8fHx8fHw4ODU5LzFcbkVWTnxBMDF8MjAxNzA3MzExNDEzMDB8fHxSQkZUSElSS0VM"
    "TFMyXlRoaXJrZWxsXlN0ZXBoZW5eXl5eXl5cIlwiXlBSU05MXl5eT1JHRFJeXCJcIlxuUElEfDF8MTA1MzIzODBeXl5OT0MtTVJO"
    "Xk1STl5cIlwifDEwNTMyMzgwXl5eTk9DLU1STl5NUk5eXCJcInx8WlpaRURVQ0FUSU9OXlNURVBIRU5eXl5eXkNVUlJFTlR8fDE5"
    "ODIxMTAzfDF8fFwiXCJ8Q2h1cmNoaWxsIEhvc3BpdGFsXk9sZCBSb2FkXk9YRk9SRF5cIlwiXk9YMyA3TEVeR0JSXkhPTUVeSGVh"
    "ZGluZ3Rvbl5cIlwiXl5eXl5eXl5cIlwifHx8fFwiXCJ8XCJcInxcIlwifDkwNDc4NTQ4OF5eXk5PQy1FbmNudHIgTnVtYmVyXkZJ"
    "Tk5CUl5cIlwifHx8fEN8fFwiXCJ8fFwiXCJ8XCJcInxcIlwifHxcIlwiXG5QRDF8fHxKRVJJQ0hPIEhFQUxUSCBDRU5UUkUgKEtF"
    "QVJMRVkpXl5LODQwMjZ8Rzg0MDQyMzFeQ0hJVkVSU15BTkRZXkFCRFVTXl5eXlwiXCJeRVhUSURcblpQSXwxfHx8fHx8fHxcIlwi"
    "fEc4NDA0MjMxXkNISVZFUlNeQU5EWV5BQkRVU3x8XCJcInxcIlwifFwiXCJ8XCJcInx8fHx8fHxcIlwiXG5QVjF8MXxJTlBBVElF"
    "TlR8Tk9DLVdhcmQgQl5EYXkgUm9vbV5DaGFpciA2Xk5PQ15eQkVEXk11c2N8MjJ8fFwiXCJeXCJcIl5cIlwiXlwiXCJeXl5cIlwi"
    "fEMxNTI0OTcwXkJ1cmdlXlBldGVyXkRlbmlzXl5Ncl5eXk5IU0NPTlNVTFROQlJeUFJTTkxeXl5OT05HUF5cIlwifjMzMzc5ODEw"
    "MzAzN15CdXJnZV5QZXRlcl5EZW5pc15eTXJeXl5EUk5CUl5QUlNOTF5eXk9SR0RSXlwiXCJ8dGVzdGNvbnN1bHRhbnReVGVzdF5U"
    "ZXN0Xl5eXl5eXCJcIl5QUlNOTF5eXk9SR0RSXlwiXCJ8fDExMHxcIlwifFwiXCJ8XCJcInwxOXxcIlwifFwiXCJ8fElOUEFUSUVO"
    "VHw5MDkxMjc4MDVeXlwiXCJeTk9DLUF0dGVuZGFuY2VeVklTSVRJRHxcIlwifHxcIlwifHx8fHx8fHx8fHx8fHxcIlwifFwiXCJ8"
    "XCJcInxOT0N8fEFDVElWRXx8fDIwMTcwNzMxMTQxMzAwXG5QVjJ8fDF8fHx8fFwiXCJ8fDIwMTcwNzMxMDAwMDAwfHx8fFwiXCJ8"
    "fHx8fHx8fFwiXCJ8XCJcInxeXjY0Nzg0Mw=="
)


@openapi_schema(dhos_connector_api_spec)
class MessageRequest(Schema):
    class Meta:
        title = "Message request"
        unknown = EXCLUDE
        ordered = True

    type = fields.String(
        required=True, metadata={"example": "HL7v2", "enum": ["HL7v2"]}
    )
    body = fields.String(
        required=True,
        metadata={"description": "Base64 encoded message", "example": EXAMPLE_MESSAGE},
    )


@openapi_schema(dhos_connector_api_spec)
class MessageUpdate(Schema):
    class Meta:
        title = "Message update"
        unknown = EXCLUDE
        ordered = True

    is_processed = fields.Boolean(
        required=True,
        metadata={
            "example": True,
            "description": "Set when the message has been processed",
        },
    )


@openapi_schema(dhos_connector_api_spec)
class CDAMessageRequest(Schema):
    class Meta:
        title = "Message request"
        unknown = INCLUDE
        ordered = True

    type = fields.String(
        required=True, metadata={"example": "HL7v3CDA", "enum": ["HL7v3CDA"]}
    )
    content = fields.String(
        required=True, metadata={"description": "HL7 v3 CDA message (XML string)"}
    )


@openapi_schema(dhos_connector_api_spec)
class MessageResponse(Schema):
    class Meta:
        title = "Message response"
        unknown = EXCLUDE
        ordered = True

    uuid = fields.String(
        required=True,
        metadata={
            "description": "Universally unique identifier for message",
            "example": "2c4f1d24-2952-4d4e-b1d1-3637e33cc161",
        },
    )
    type = fields.String(
        required=True, metadata={"example": "HL7v2", "enum": ["HL7v2"]}
    )
    body = fields.String(
        required=True,
        metadata={"description": "Base64 encoded response", "example": EXAMPLE_MESSAGE},
    )


@openapi_schema(dhos_connector_api_spec)
class MessageUUID(Schema):
    class Meta:
        title = "Message UUID"
        ordered = True

    message_uuid = fields.String(
        required=True,
        metadata={
            "description": "UUID for message",
            "example": "2c4f1d24-2952-4d4e-b1d1-3637e33cc161",
        },
    )


@openapi_schema(dhos_connector_api_spec)
class MessageControlId(Schema):
    class Meta:
        title = "Message Control ID"
        ordered = True

    message_control_id = fields.String(
        required=True,
        metadata={
            "description": "Message control ID",
            "example": "Q548420607T549582984A1096",
        },
    )


@openapi_schema(dhos_connector_api_spec)
class ObservationData(Schema):
    class Meta:
        unknown = INCLUDE
        ordered = True

    clinician = fields.Dict(
        required=False, metadata={"description": "Clinician who made the observations"}
    )
    encounter = fields.Dict(
        required=True, metadata={"description": "Encounter details"}
    )
    observation_set = fields.Dict(
        required=True, metadata={"description": "Observation set details"}
    )
    patient = fields.Dict(
        required=True, metadata={"description": "Patient name, address, identity etc."}
    )


@openapi_schema(dhos_connector_api_spec)
class ObservationAction(Schema):
    class Meta:
        unknown = EXCLUDE
        ordered = True

    data = fields.Nested(ObservationData, required=True)
    name = fields.String(
        required=True,
        metadata={
            "description": "The action to be performed",
            "example": "process_observation_set",
        },
    )


@openapi_schema(dhos_connector_api_spec)
class ProcessObservationSet(Schema):
    class Meta:
        title = "Process Observation Set Actions"
        unknown = EXCLUDE
        ordered = True

    actions = fields.List(fields.Nested(ObservationAction), required=True)
