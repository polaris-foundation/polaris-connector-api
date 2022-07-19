import logging
from pathlib import Path

from behave import use_step_matcher
from behave.model import Feature, Scenario, Step
from behave.runner import Context
from clients import wiremock_client
from helpers.hl7 import get_message_from_file, message_to_body
from helpers.jwt import get_system_token
from reporting import init_report_portal
from she_logging import logger

faker_logger = logging.getLogger("faker")
faker_logger.setLevel(logging.WARN)  # faker is extremely noisy at DEBUG level

use_step_matcher("re")


def before_all(context: Context) -> None:
    init_report_portal(context)
    # set up EPR connector mock
    wiremock_client.post_hl7_message_mock(
        message_to_body(get_message_from_file("./resources/admit_ack.hl7")), 200
    )
    wiremock_client.post_mirth_wsdl_mock(
        Path("./resources/mirth.wsdl").read_text(), 200
    )
    wiremock_client.post_mirth_xsd_mock(Path("./resources/mirth.xsd").read_text(), 200)
    wiremock_client.post_mirth_soap_mock(
        Path("./resources/mirth_soap_envelope.xml").read_text(), 200
    )

    # cache jwt
    if not hasattr(context, "system_jwt"):
        context.system_jwt = get_system_token()
        logger.debug("system jwt: %s", context.system_jwt)


def before_feature(context: Context, feature: Feature) -> None:
    context.feature_id = context.behave_integration_service.before_feature(feature)


def before_scenario(context: Context, scenario: Scenario) -> None:
    context.scenario_id = context.behave_integration_service.before_scenario(
        scenario, feature_id=context.feature_id
    )


def before_step(context: Context, step: Step) -> None:
    context.step_id = context.behave_integration_service.before_step(
        step, scenario_id=context.scenario_id
    )


def after_step(context: Context, step: Step) -> None:
    context.behave_integration_service.after_step(step, step_id=context.step_id)


def after_scenario(context: Context, scenario: Scenario) -> None:
    context.behave_integration_service.after_scenario(
        scenario, scenario_id=context.scenario_id
    )


def after_feature(context: Context, feature: Feature) -> None:
    context.behave_integration_service.after_feature(
        feature, feature_id=context.feature_id
    )


def after_all(context: Context) -> None:
    context.behave_integration_service.after_all(launch_id=context.launch_id)
