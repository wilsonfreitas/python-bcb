"""Shared HTTP error handling tests."""

import httpx
import pytest

from bcb.exceptions import (
    BCBAPIError,
    BCBAPINotFoundError,
    BCBAPIServerError,
    BCBRateLimitError,
    ODataError,
    SGSError,
)
from bcb.http import raise_for_request_error, raise_for_status


def make_response(status_code: int) -> httpx.Response:
    request = httpx.Request("GET", "https://example.test/resource")
    return httpx.Response(status_code, request=request)


def test_raise_for_status_allows_expected_status() -> None:
    raise_for_status(make_response(200), context="Example")


@pytest.mark.parametrize(
    ("status_code", "error_cls"),
    [
        (429, BCBRateLimitError),
        (404, BCBAPINotFoundError),
        (500, BCBAPIServerError),
    ],
)
def test_raise_for_status_maps_common_http_statuses(
    status_code: int, error_cls: type[BCBAPIError]
) -> None:
    with pytest.raises(error_cls) as exc_info:
        raise_for_status(make_response(status_code), context="Example")

    assert exc_info.value.status_code == status_code


def test_raise_for_status_maps_generic_client_error() -> None:
    with pytest.raises(BCBAPIError) as exc_info:
        raise_for_status(make_response(400), context="Example")

    assert exc_info.value.status_code == 400
    assert "Example" in str(exc_info.value)


def test_raise_for_status_supports_endpoint_specific_exceptions() -> None:
    with pytest.raises(SGSError, match="SGS unavailable"):
        raise_for_status(
            make_response(503),
            context="SGS",
            server_error_cls=SGSError,
            server_error_message="SGS unavailable",
        )


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("connection failed"),
        httpx.TimeoutException("request timed out"),
    ],
)
def test_raise_for_request_error_maps_transport_failures(
    error: httpx.HTTPError,
) -> None:
    with pytest.raises(BCBAPIError) as exc_info:
        raise_for_request_error(error, context="Example")

    assert exc_info.value.status_code == 0
    assert "Example request failed" in str(exc_info.value)


def test_raise_for_request_error_supports_endpoint_specific_exceptions() -> None:
    with pytest.raises(ODataError, match="OData request failed"):
        raise_for_request_error(
            httpx.ConnectError("offline"),
            context="OData",
            error_cls=ODataError,
        )
