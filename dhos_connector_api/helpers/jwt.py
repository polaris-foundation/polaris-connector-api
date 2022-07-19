import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import dhosredis
from flask import current_app as app
from flask_batteries_included.config import is_production_environment
from flask_batteries_included.helpers.error_handler import ServiceUnavailableException
from jose import jwt as jose_jwt
from she_logging import logger
from she_logging.request_id import current_request_id


def get_epr_service_adapter_headers() -> Dict[str, str]:

    key, alg = get_key()
    hs_issuer: str = app.config["EPR_SERVICE_ADAPTER_ISSUER"]
    scope: str = get_scope()

    jwt_token: str = jose_jwt.encode(
        {
            "iss": hs_issuer,
            "aud": hs_issuer,
            "scope": scope,
            "exp": _generate_expiry_after_seconds(app.config["JWT_EXPIRY_IN_SECONDS"]),
        },
        key,
        algorithm=alg,
    )

    headers: Dict = {
        "Accept": "application/json",
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json",
        "X-Request-ID": current_request_id() or str(uuid.uuid4()),
    }

    logger.debug(
        "Created headers for EPR service adapter request", extra={"headers": headers}
    )

    return headers


def _generate_expiry_after_seconds(seconds: int) -> datetime:
    td = timedelta(seconds=seconds)
    now = datetime.utcnow()
    return now + td


def get_key() -> Tuple[str, str]:
    return app.config["EPR_SERVICE_ADAPTER_HS_KEY"], "HS512"


def get_scope() -> str:
    scope: Optional[str] = dhosredis.get_value(
        key="CACHED_EPR_SERVICE_ADAPTER_SCOPE", default=None
    )
    if scope is None:
        message: str = "Could not retrieve system scope from redis"
        if (
            is_production_environment()
            or app.config.get("MOCK_EPR_SERVICE_ADAPTER_SCOPE") is None
        ):
            logger.debug("is_production_environment: %s", is_production_environment())
            logger.debug(
                "MOCK_EPR_SERVICE_ADAPTER_SCOPE: %s",
                app.config.get("MOCK_EPR_SERVICE_ADAPTER_SCOPE"),
            )
            raise ServiceUnavailableException(message)

        # We're in a lower environment and mock scopes have been provided.
        logger.warning(
            "Couldn't build scope from Auth0, using provided mock epr service adapter scope instead"
        )
        return app.config["MOCK_EPR_SERVICE_ADAPTER_SCOPE"]
    return scope
