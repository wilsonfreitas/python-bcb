import pytest

from bcb.exceptions import (
    BCBError,
    BCBAPIError,
    BCBAPINotFoundError,
    BCBRateLimitError,
    CurrencyNotFoundError,
    SGSError,
    ODataError,
)


def test_exception_hierarchy():
    assert issubclass(BCBAPIError, BCBError)
    assert issubclass(CurrencyNotFoundError, BCBError)
    assert issubclass(SGSError, BCBError)
    assert issubclass(ODataError, BCBError)
    assert issubclass(BCBError, Exception)


def test_bcb_api_error_with_status_code():
    err = BCBAPIError("request failed", 404)
    assert err.status_code == 404
    assert "request failed" in str(err)


def test_bcb_api_error_with_server_error():
    err = BCBAPIError("request failed", 500)
    assert err.status_code == 500
    assert "request failed" in str(err)


def test_bcb_api_not_found_error():
    err = BCBAPINotFoundError("endpoint not found", 404)
    assert err.status_code == 404
    assert isinstance(err, BCBAPIError)
    assert "endpoint not found" in str(err)


def test_bcb_rate_limit_error():
    err = BCBRateLimitError("rate limit exceeded", 429)
    assert err.status_code == 429
    assert isinstance(err, BCBAPIError)
    assert "rate limit exceeded" in str(err)


def test_currency_not_found_error():
    err = CurrencyNotFoundError("Unknown symbol: ZAR")
    assert isinstance(err, BCBError)
    assert "ZAR" in str(err)


def test_sgs_error():
    err = SGSError("BCB error: series not found")
    assert isinstance(err, BCBError)
    assert "series not found" in str(err)


def test_odata_error():
    err = ODataError("Invalid name: Foo")
    assert isinstance(err, BCBError)
    assert "Foo" in str(err)


def test_exceptions_are_catchable_as_bcb_error():
    with pytest.raises(BCBError):
        raise BCBAPIError("test", 500)

    with pytest.raises(BCBError):
        raise CurrencyNotFoundError("test")

    with pytest.raises(BCBError):
        raise SGSError("test")

    with pytest.raises(BCBError):
        raise ODataError("test")
