from decimal import Decimal
import json
import logging
from urllib.parse import urljoin, urlencode
from . import exceptions, utils

_log = logging.getLogger(__name__)


class BaseClient:
    _session = None
    _requester = None  # requests.Session()
    timeout = 10
    base_url: str = ""

    def _request(self, func, path, data=None):
        url = urljoin(self.base_url, path)
        _log.debug("{}".format(path))
        if data is not None:
            _log.debug(
                "data: {}".format(
                    json.dumps(
                        data, cls=utils.JSONWithDecimalEncoder, indent=2, sort_keys=True
                    )
                )
            )
        rsp = func(url, data=json.dumps(data) if data else None, timeout=self.timeout)
        result = None
        if rsp.status_code != 204:
            result = rsp.json(parse_float=Decimal)
        if rsp.status_code < 200 or rsp.status_code >= 300:
            message = getattr(result, "message", "No message supplied")
            _log.error("HTTP {} for {}: {}".format(rsp.status_code, url, message))
            if rsp.status_code == 400:
                if "o pocket found" in message:
                    raise exceptions.NoPocketFound(message)
                if "BIC and IBAN does not match" in message:
                    raise exceptions.BICIBANMismatch(message)
                if "ould not interpret numbers after plus-sign" in message:
                    raise exceptions.InvalidPhoneNumber(message)
                if "equired fields are:" in message:
                    raise exceptions.MissingFields(message)
            if rsp.status_code == 401:
                raise exceptions.Unauthorized(rsp.status_code, message)
            if rsp.status_code == 403:
                raise exceptions.Forbidden(rsp.status_code, message)
            if rsp.status_code == 404:
                raise exceptions.NotFound(rsp.status_code, message)
            if rsp.status_code == 405:
                raise exceptions.MethodNotAllowed(rsp.status_code, message)
            if rsp.status_code == 406:
                raise exceptions.NotAccaptable(rsp.status_code, message)
            if rsp.status_code == 409:
                raise exceptions.RequestConflict(rsp.status_code, message)
            if rsp.status_code == 422:
                if "nsufficient balance" in message:
                    raise exceptions.InsufficientBalance(message)
                elif "ddress is required" in message:
                    raise exceptions.CounterpartyAddressRequired(message)
                elif "ounterparty already exists" in message:
                    raise exceptions.CounterpartyAlreadyExists(message)
            if rsp.status_code == 429:
                raise exceptions.TooManyRequests(rsp.status_code, message)
            if rsp.status_code == 500:
                raise exceptions.InternalServerError(rsp.status_code, message)
            if rsp.status_code == 503:
                raise exceptions.ServiceUnavailable(rsp.status_code, message)
            raise exceptions.RevolutHttpError(rsp.status_code, message)
        if result:
            _ppresult = json.dumps(
                result, cls=utils.JSONWithDecimalEncoder, indent=2, sort_keys=True
            )
            _log.debug("Result:\n{result}".format(result=_ppresult))
        return result

    def _get(self, path, data=None):
        path = (
            "{}?{}".format(path, urlencode(data, safe=":"))
            if data is not None
            else path
        )
        return self._request(self._requester.get, path)

    def _post(self, path, data=None):
        return self._request(self._requester.post, path, data or {})

    def _delete(self, path, data=None):
        return self._request(self._requester.delete, path, data or {})
