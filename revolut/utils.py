import datetime
import dateutil.parser
from decimal import Decimal
import json
import jwt


def _obj2id(obj):
    return obj.id if hasattr(obj, "id") else obj


def _date(v):
    if not isinstance(v, (datetime.date, datetime.datetime)):
        return dateutil.parser.parse(v).date()
    elif isinstance(v, datetime.datetime):
        return v.date()
    return v


def _datetime(v):
    if not isinstance(v, (datetime.date, datetime.datetime)):
        v = datetime.date.fromisoformat(v)
    return v.strftime("%Y-%m-%dT%H:%M:%S.%f%zZ")


def _integertomoney(value_int):
    return (Decimal(value_int) / Decimal(100)).quantize(Decimal("0.01"))


def _moneytointeger(value_decimal):
    return int((Decimal(value_decimal) * 100).quantize(Decimal("1")))


class _SetEnv(object):
    def _set_env(self, token):
        if token.startswith("oa_prod"):
            self.base_url = "https://b2b.revolut.com/api/1.0/"
            self.live = True
        elif token.startswith("oa_sand"):
            self.base_url = "https://sandbox-b2b.revolut.com/api/1.0/"
            self.live = False
        else:
            raise ValueError(
                "Token '{:s}' matches neither production nor sandbox environment.".format(
                    token
                )
            )


class _UpdateFromKwargsMixin(object):
    def _update(self, **kwargs):
        for k, v in kwargs.items():
            if not hasattr(self, k):
                raise ValueError(
                    "Excess keyword for {}: {} = {}".format(type(self), k, v)
                )
            setattr(self, k, v)


class JSONWithDecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(JSONWithDecimalEncoder, self).default(o)


def get_jwt(prvkey, issuer, client_id):
    """Generates JWT signed with the private key"""
    return jwt.encode(
        {"iss": issuer, "sub": client_id, "aud": "https://revolut.com"},
        prvkey,
        algorithm=("RS256"),
    )
