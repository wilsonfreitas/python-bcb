import pytest

from bcb.exceptions import (
    BCBError,
    BCBAPIError,
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


def test_bcb_api_error_without_status_code():
    err = BCBAPIError("request failed")
    assert err.status_code is None
    assert "request failed" in str(err)


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
