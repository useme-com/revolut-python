from __future__ import unicode_literals
from datetime import datetime, timedelta
import json
import logging
import requests

try:  # pragma: nocover
    from urllib.parse import urljoin  # 3.x
except ImportError:  # pragma: nocover
    from urlparse import urljoin  # 2.x
from . import exceptions
from . import utils

__all__ = ("TemporarySession", "RenewableSession", "TokenProvider")

_log = logging.getLogger(__name__)


class BaseSession(utils._SetEnv):
    _access_token = None

    def refresh_access_token(self):
        raise NotImplementedError(
            "{} doesn't support refreshing an access token".format(type(self).__name__)
        )

    @property
    def access_token(self):
        return self._access_token


class TemporarySession(BaseSession):
    """Accepts access token and maintains a temporary session limited by the token's lifetime."""

    def __init__(self, access_token):
        self._set_env(access_token)
        self._access_token = access_token


class RenewableSession(BaseSession):
    """Maintains long-term session, allowing to refresh the access tokens.

    You may provide it with existing `access_token`. If missing, it will obtain a new one.
    """

    refresh_token = None

    def __init__(self, refresh_token, client_id, jwt, access_token=None):
        self._access_token = access_token or self._access_token
        self._set_env(refresh_token)
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.jwt = jwt

    def refresh_access_token(self):
        self._request_token()
        return self._access_token

    @property
    def access_token(self):
        if not self._access_token or (
            self.access_token_expires and datetime.utcnow() >= self.access_token_expires
        ):
            return self.refresh_access_token()
        return self._access_token

    def _request_token(self):
        self._do_request_token(
            grant_type="refresh_token", refresh_token=self.refresh_token
        )

    def _do_request_token(self, **params):
        data = {
            "client_id": self.client_id,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": self.jwt,
        }
        data.update(params)
        _log.debug(
            "{:s} request data: {}".format(
                type(self).__name__, json.dumps(data, indent=2, sort_keys=True)
            )
        )
        now = datetime.utcnow()
        rsp = requests.post(
            urljoin(self.base_url, "auth/token"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=data,
        )
        result = rsp.json()
        _log.debug(
            "{:s} result: {}".format(
                type(self).__name__, json.dumps(result, indent=2, sort_keys=True)
            )
        )
        if rsp.status_code != 200:
            message = result.get("error") or ""
            if "error_description" in result:
                message += ": {:s}".format(result["error_description"])
            raise exceptions.RevolutHttpError(rsp.status_code, message)
        self._access_token = result["access_token"]
        self.access_token_expires = now + timedelta(seconds=result["expires_in"])
        self.refresh_token = result.get("refresh_token", self.refresh_token)


class TokenProvider(RenewableSession):
    """Handles obtaining of access and refresh tokens pair, consuming auth code.

    While this class might be used as a regular session, please remember that the auth code cannot
    be used again. The proper way to continue is to store the obtained tokens and create either
    `TemporarySession` or `RenewableSession` object.
    """

    auth_code_spent = False

    def __init__(self, auth_code, client_id, jwt):
        self._set_env(auth_code)
        self.auth_code = auth_code
        self.client_id = client_id
        self.jwt = jwt
        self._request_token()

    @property
    def access_token(self):
        if not self._access_token:
            self._request_token()
        elif (
            self.access_token_expires and datetime.utcnow() >= self.access_token_expires
        ):
            return self.refresh_access_token()
        return self._access_token

    def _request_token(self):
        self._do_request_token(grant_type="authorization_code", code=self.auth_code)
        self.auth_code_spent = True
