from datetime import datetime
from typing import List

import dhosredis
import pytest
from flask import Flask
from flask_batteries_included.helpers.error_handler import ServiceUnavailableException
from jose import jwt
from pytest_mock import MockFixture

from dhos_connector_api.helpers.jwt import get_epr_service_adapter_headers, get_scope


class TestJwt:
    @pytest.mark.parametrize("dummy_scope", ["test-scope", None])
    def test_get_epr_service_adapter_headers(
        self, app: Flask, mocker: MockFixture, dummy_scope: List[str]
    ) -> None:
        mocker.patch.object(dhosredis, "get_value", return_value=dummy_scope)
        headers = get_epr_service_adapter_headers()
        authorisation = headers["Authorization"]
        assert authorisation.startswith("Bearer ")
        token = authorisation.split(" ", 1)[1]

        token_dict = jwt.decode(
            token,
            audience=app.config["EPR_SERVICE_ADAPTER_ISSUER"],
            issuer=app.config["EPR_SERVICE_ADAPTER_ISSUER"],
            key=app.config["EPR_SERVICE_ADAPTER_HS_KEY"],
        )
        assert (
            datetime.now().timestamp() + app.config["JWT_EXPIRY_IN_SECONDS"]
        ) - token_dict["exp"] < 3

    def test_scope(self, app: Flask) -> None:
        app.config["MOCK_EPR_SERVICE_ADAPTER_SCOPE"] = None
        with pytest.raises(ServiceUnavailableException):
            get_scope()
