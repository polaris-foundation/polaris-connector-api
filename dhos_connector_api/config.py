from typing import Optional

from environs import Env
from flask import Flask


class Configuration:
    env = Env()
    EPR_SERVICE_ADAPTER_HS_KEY: str = env.str("EPR_SERVICE_ADAPTER_HS_KEY")
    EPR_SERVICE_ADAPTER_ISSUER: str = env.str("EPR_SERVICE_ADAPTER_ISSUER")
    SERVER_TIMEZONE: str = env.str("SERVER_TIMEZONE")
    HL7_TRANSFORMER_MODULE: str = env.str(
        "HL7_TRANSFORMER_MODULE", "dhos_connector_api.transformers.optimus_prime"
    )

    EPR_SERVICE_ADAPTER_URL_BASE: str = env.str("EPR_SERVICE_ADAPTER_URL_BASE")
    MIRTH_HOST_URL_BASE: str = env.str("MIRTH_HOST_URL_BASE", "")
    MIRTH_USERNAME: str = env.str("MIRTH_USERNAME", "")
    MIRTH_PASSWORD: str = env.str("MIRTH_PASSWORD", "")
    JWT_EXPIRY_IN_SECONDS: int = env.int("JWT_EXPIRY_IN_SECONDS", 600)

    MAX_REQUEST_FAILS: int = env.int("MAX_REQUEST_FAILS", 3)
    SMTP_HOST: Optional[str] = env.str("SMTP_HOST", None)
    SMTP_AUTH_PASS = env.str("SMTP_AUTH_PASS", None)
    SMTP_AUTH_USER = env.str("SMTP_AUTH_USER", None)
    EMAIL_SENDER = env.str("EMAIL_SENDER", None)
    EMAIL_RECIPIENT = env.str("EMAIL_RECIPIENT", None)
    MOCK_EPR_SERVICE_ADAPTER_SCOPE: Optional[str] = env.str(
        "MOCK_EPR_SERVICE_ADAPTER_SCOPE", None
    )
    CUSTOMER_CODE: str = env.str("CUSTOMER_CODE")
    DHOS_TRUSTOMER_API_HOST: str = env.str("DHOS_TRUSTOMER_API_HOST")
    POLARIS_API_KEY: str = env.str("POLARIS_API_KEY")
    TRUSTOMER_CONFIG_CACHE_TTL_SEC: int = env.int(
        "TRUSTOMER_CONFIG_CACHE_TTL_SEC", 60 * 60  # Cache for 1 hour by default.
    )


def init_config(app: Flask) -> None:
    app.config.from_object(Configuration)
