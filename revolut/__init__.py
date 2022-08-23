import dateutil.parser
from decimal import Decimal
import json
import logging
import requests
from urllib.parse import urljoin, urlencode
from . import exceptions, utils
from .session import BaseSession
from typing import Optional

__version__ = "0.9"

_log = logging.getLogger(__name__)


class BaseClient(utils._SetEnv):
    _session = None
    _requester = None  # requests.Session()
    timeout = 10

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


class BusinessClient(BaseClient):
    live = False
    _accounts = None
    _counterparties = None
    _cptbyaccount = None

    def __init__(self, session, timeout=None):
        self._set_env(session.access_token)
        self._session = session
        self.timeout = timeout
        self._requester = requests.Session()
        self._requester.headers.update(
            {"Authorization": "Bearer {}".format(self._session.access_token)}
        )

    @property
    def accounts(self):
        if self._accounts is not None:
            return self._accounts
        _accounts = {}
        data = self._get("accounts")
        for accdat in data:
            acc = Account(client=self, **accdat)
            _accounts[acc.id] = acc
        self._accounts = _accounts
        return self._accounts

    @property
    def counterparties(self):
        if self._counterparties is not None:
            return self._counterparties
        _counterparties = {}
        _cptbyaccount = {}
        data = self._get("counterparties")
        for cptdat in data:
            cpt = Counterparty(client=self, **cptdat)
            _counterparties[cpt.id] = cpt
            for cptaccid in cpt.accounts.keys():  # type: ignore
                _cptbyaccount[cptaccid] = cpt
        self._counterparties = _counterparties
        self._cptbyaccount = _cptbyaccount
        return self._counterparties

    def _refresh_counterparties(self):
        self._counterparties = self._cptbyaccount = {}
        _ = self.counterparties

    def transactions(
        self, counterparty=None, from_date=None, to_date=None, txtype=None
    ):
        transactions = []
        reqdata = {}
        if counterparty:
            reqdata["counterparty"] = utils._obj2id(counterparty)
        if from_date:
            reqdata["from"] = utils._date(from_date).isoformat()
        if to_date:
            reqdata["to"] = utils._date(to_date).isoformat()
        if txtype:
            if txtype not in (
                "atm",
                "card_payment",
                "card_refund",
                "card_chargeback",
                "card_credit",
                "exchange",
                "transfer",
                "loan",
                "fee",
                "refund",
                "topup",
                "topup_return",
                "tax",
                "tax_refund",
            ):
                raise ValueError("Invalid transaction type: {}".format(txtype))
            reqdata["type"] = txtype
        data = self._get("transactions", data=reqdata or None)
        for txdat in data:
            txn = Transaction(client=self, **txdat)
            transactions.append(txn)
        return transactions

    def transaction(self, id):
        data = self._get("transaction/{}".format(id))
        return Transaction(client=self, **data)

    # TODO: def transaction_by_request_id(self, request_id):


class MerchantClient(BaseClient):
    def __init__(self, session, timeout=None):
        self._set_env(session.access_token)
        self._session = session
        self.timeout = timeout
        self._requester = requests.Session()
        self._requester.headers.update(
            {"Authorization": "Bearer {}".format(self._session._access_token)}
        )

    def get_or_create_order(self, amount, currency, token, order_id):
        order = self.get_order(order_id)
        return order or self.create_order(amount, currency, token)

    def create_order(self, amount, currency, token):
        data = self._post(
            "orders",
            data={
                "amount": amount,
                "currency": currency,
                "merchant_order_ext_ref": token,
            }
            or None,
        )
        return Order(client=self, **data)

    def get_order(self, order_id):
        try:
            data = self._get(f"orders/{order_id}")
            return Order(client=self, **data)
        except Exception:
            return None

    def orders(self, from_date=None, to_date=None):
        orders = []
        reqdata = {}
        if from_date:
            reqdata["from_created_date"] = utils._datetime(from_date)
        if to_date:
            reqdata["to_created_date"] = utils._datetime(to_date)
        data = self._get(path="orders", data=reqdata)
        for txdat in data:
            txn = Order(client=self, **txdat)
            orders.append(txn)
        return orders

    def webhook(self, url, events):
        reqdata = {}
        if url:
            reqdata["url"] = url
        if events:
            reqdata["events"] = events
        data = self._post(f"webhooks", data=reqdata)


class _UpdateFromKwargsMixin(object):
    def _update(self, **kwargs):
        for k, v in kwargs.items():
            if not hasattr(self, k):
                raise ValueError(
                    "Excess keyword for {}: {} = {}".format(type(self), k, v)
                )
            setattr(self, k, v)


class Account(_UpdateFromKwargsMixin):
    client: Client
    id: Optional[str] = None
    name: Optional[str] = None
    currency: Optional[str] = None
    balance: Decimal = Decimal(0)
    state: Optional[str] = None
    public: bool = False
    created_at = None
    updated_at = None

    def __init__(self, **kwargs):
        self.client = kwargs.pop("client")
        self._update(**kwargs)

    def _update(self, **kwargs):
        super(Account, self)._update(**kwargs)
        self.created_at = (
            dateutil.parser.parse(self.created_at) if self.created_at else None
        )
        self.updated_at = (
            dateutil.parser.parse(self.updated_at) if self.updated_at else None
        )
        self.balance = Decimal(self.balance)

    def __repr__(self):
        return "<Account {}>".format(self.id)

    def __str__(self):
        return "Id: {}, {:.2f} {:3s}".format(self.id, self.balance, self.currency)

    def refresh(self):
        data = self.client._get("accounts/{}".format(self.id))
        self._update(**data)
        return self

    def details(self):
        return self.client._get("accounts/{}/bank-details".format(self.id))

    def send(self, dest, amount, currency, request_id, reference=None):
        amount = Decimal(amount)
        if not isinstance(request_id, utils._str_types) or len(request_id) > 40:
            raise ValueError("request_id must be a string of max. 40 chars")
        destid = str(utils._obj2id(dest))
        if (
            destid in self.client.accounts
            and currency == self.currency == self.client.accounts[destid].currency
        ):
            return self._transfer_internal(destid, amount, request_id, reference)
        _ = self.client.counterparties  # NOTE: make sure counterparties are loaded
        cpt, receiver = None, {}
        try:
            cpt = self.client._cptbyaccount[destid]  # type: ignore
            if cpt.accounts[destid].currency != currency:
                raise exceptions.CurrencyMismatch(
                    "Currency {} does not match the destination currency: {}".format(
                        currency, cpt.accounts[destid].currency
                    )
                )
            receiver = {"account_id": destid, "counterparty_id": cpt.id}
        except KeyError:
            pass
        if not cpt:
            try:
                cpt = self.client.counterparties[destid]
            except KeyError:
                raise exceptions.DestinationNotFound(
                    "Cannot find {:s} either among counterparties, their accounts or our own accounts".format(
                        destid
                    )
                )
            receiver = {"counterparty_id": cpt.id}
        reqdata = {
            "request_id": request_id,
            "account_id": self.id,
            "amount": "{:.2f}".format(amount),
            "currency": currency,
            "receiver": receiver,
        }
        if reference is not None:
            reqdata["reference"] = reference
        data = self.client._post("pay", reqdata)
        return self.client.transaction(data["id"])

    def _transfer_internal(self, destid, amount, request_id, reference):
        reqdata = {
            "request_id": request_id,
            "source_account_id": self.id,
            "target_account_id": destid,
            "amount": "{:.2f}".format(amount),
            "currency": self.currency,
        }
        if reference is not None:
            reqdata["reference"] = reference
        data = self.client._post("transfer", reqdata)
        return self.client.transaction(data["id"])


class Counterparty(_UpdateFromKwargsMixin):
    client: Client
    id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    profile_type: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    created_at = None
    updated_at = None
    accounts: Optional[dict] = None

    def __init__(self, **kwargs):
        self.client = kwargs.pop("client")
        self._update(**kwargs)

    def __repr__(self):
        return "<Counterparty {}>".format(self.id or "")

    def __str__(self):
        return "Id: {} {} {} {}".format(
            self.id or "NO ID",
            self.profile_type or "",
            self.name or "",
            self.email if self.profile_type == "business" else self.phone or "",
        ).strip()

    def _update(self, **kwargs):
        self.accounts = {}
        for accdat in kwargs.pop("accounts", []):
            Class = (
                CounterpartyAccount
                if accdat["type"] == "revolut"
                else CounterpartyExternalAccount
            )
            acc = Class(**accdat)
            self.accounts[acc.id] = acc
        super(Counterparty, self)._update(**kwargs)
        self.created_at = (
            dateutil.parser.parse(self.created_at) if self.created_at else None
        )
        self.updated_at = (
            dateutil.parser.parse(self.updated_at) if self.updated_at else None
        )

    def refresh(self):
        data = self.client._get("counterparty/{}".format(self.id))
        self._update(**data)
        return self

    def save(self):
        if self.id:
            raise exceptions.CounterpartyAlreadyExists(
                "The object's ID is set. It has been saved already."
            )
        if self.profile_type == "business":
            keyset = ("profile_type", "name", "email")
        elif self.profile_type == "personal":
            keyset = ("profile_type", "name", "phone")
        else:
            raise ValueError("Invalid profile type: {}".format(self.profile_type))
        try:
            data = self.client._post(
                "counterparty", data={k: getattr(self, k) for k in keyset}
            )
        except exceptions.RevolutHttpError as e:
            if e.status_code == 422:
                raise exceptions.CounterpartyAlreadyExists()
            raise
        self._update(**data)
        self.client._refresh_counterparties()
        return self

    def delete(self):
        if not self.id:
            raise ValueError("{} doesn't have an ID. Cannot delete.".format(self))
        self.client._delete("counterparty/{}".format(self.id))
        del self.client._counterparties[self.id]  # type: ignore
        self.id = None


class ExternalCounterparty(_UpdateFromKwargsMixin):
    """Describes a non-Revolut counterparty. Objects of this class should be used only to
    create such counterparties. The `.save()` method will return the resulting `Counterparty`
    object and the original `ExternalCounterparty` should be discarded afterwards."""

    id: Optional[str] = None
    client: Client
    account_no: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    individual_name: Optional[dict] = None
    bank_country: Optional[str] = None
    currency: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None

    def __init__(self, **kwargs):
        self.client = kwargs.pop("client")
        self._update(**kwargs)

    def __repr__(self):
        return "<ExternalCounterparty {}>".format(self.iban or self.account_no)

    def __str__(self):
        return "Id: {} {}".format(
            self.id or "NO ID",
            "{first_name} {last_name}".format(**self.individual_name)
            if self.individual_name
            else self.company_name,
        )

    def save(self):
        if self.id:
            raise exceptions.CounterpartyAlreadyExists(
                "The object's ID is set. It has been saved already."
            )
        if self.iban:
            iban_ctry = self.iban[:2]
            if iban_ctry.isalpha() and iban_ctry != self.bank_country:
                raise ValueError(
                    "Bank country {} doesn't match the IBAN prefix {}".format(
                        self.bank_country, iban_ctry
                    )
                )
        keyset = (
            "email",
            "phone",
            "company_name",
            "individual_name",
            "bank_country",
            "currency",
            "phone",
            "address",
            "iban",
            "bic",
        )
        reqdata = {}
        for k in keyset:
            v = getattr(self, k, None)
            if v:
                reqdata[k] = v
        data = self.client._post("counterparty", data=reqdata)
        self.id = data["id"]
        self.client._refresh_counterparties()
        cpt = Counterparty(client=self.client, id=self.id)
        return cpt.refresh()


class CounterpartyAccount(_UpdateFromKwargsMixin):
    id: Optional[str] = None
    name: Optional[str] = None
    currency: Optional[str] = None

    def __init__(self, **kwargs):
        self._check_type(kwargs.pop("type"))
        self._update(**kwargs)

    def __repr__(self):
        return "<CounterpartyAccount {}>".format(self.id)

    def _check_type(self, typ):
        assert typ == "revolut"


class CounterpartyExternalAccount(CounterpartyAccount):
    account_no: Optional[str] = None
    iban: Optional[str] = None
    sort_code: Optional[str] = None
    routing_number: Optional[str] = None
    bic: Optional[str] = None
    email: Optional[str] = None
    bank_country: Optional[str] = None
    recipient_charges: Optional[str] = None
    bsb_code: Optional[str] = None

    def __repr__(self):
        return "<CounterpartyExternalAccount {}>".format(self.id)

    def _check_type(self, typ):
        assert typ == "external"


class Transaction(_UpdateFromKwargsMixin):
    id: Optional[str] = None
    client: Client
    type: Optional[str] = None
    state: Optional[str] = None
    reason_code: Optional[str] = None
    created_at = None
    completed_at = None
    updated_at = None
    legs: Optional[list] = None
    request_id: Optional[str] = None
    reference: Optional[str] = None
    revertable: bool = False

    def __init__(self, **kwargs):
        self.client = kwargs.pop("client")
        self._update(**kwargs)
        self.legs = self.legs or []
        for leg in self.legs:
            if "amount" in leg and not isinstance(leg["amount"], Decimal):
                leg["amount"] = Decimal(leg["amount"])

    @property
    def direction(self):
        if len(self.legs) == 2:  # type: ignore
            return "both"
        else:
            if self.legs[0]["amount"] < 0:  # type: ignore
                return "out"
            else:
                return "in"

    def __repr__(self):
        return "<Transaction {}>".format(self.id)

    def _update(self, **kwargs):
        super(Transaction, self)._update(**kwargs)
        self.created_at = (
            dateutil.parser.parse(self.created_at) if self.created_at else None
        )
        self.updated_at = (
            dateutil.parser.parse(self.updated_at) if self.updated_at else None
        )
        self.completed_at = (
            dateutil.parser.parse(self.completed_at) if self.completed_at else None
        )


class Order(_UpdateFromKwargsMixin):
    id: str = ""
    client = None
    public_id: str = ""
    merchant_order_ext_ref: str = ""
    type: str = ""
    state: str = ""
    created_at = None
    updated_at = None
    capture_mode: str = ""
    value = Decimal(0)
    currency: str = ""
    order_amount: str = ""
    order_outstanding_amount: str = ""
    metadata: str = ""
    customer_id: str = ""
    email: str = ""
    completed_at: str = ""
    refunded_amount: str = ""
    payments: str = ""

    def __init__(self, **kwargs):
        self.client = kwargs.pop("client")
        self._update(**kwargs)

    def __repr__(self):
        return f"<Order {self.id}>"

    def _update(self, **kwargs):
        super(Order, self)._update(**kwargs)
        self.created_at = (
            dateutil.parser.parse(self.created_at) if self.created_at else None
        )
        self.updated_at = (
            dateutil.parser.parse(self.updated_at) if self.updated_at else None
        )
        self.completed_at = (
            dateutil.parser.parse(self.completed_at) if self.completed_at else ""
        )
        self.value = (
            utils._integertomoney(self.order_amount["value"])
            if self.order_amount
            else ""
        )
        self.currency = self.order_amount["currency"] if self.order_amount else ""


def Client(*args, **kwargs):
    import warnings

    warnings.warn(
        "revolut.Client() is deprecated and will be gone in >0.9.x; please change to revolut.BusinessClient() instead",
        DeprecationWarning,
    )
    return BusinessClient(*args, **kwargs)
