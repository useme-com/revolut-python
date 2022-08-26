import dateutil.parser
from decimal import Decimal
import requests
from typing import Optional

from . import base, exceptions, utils


class BusinessClient(base.BaseClient, utils._SetEnv):
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


class Account(utils._UpdateFromKwargsMixin):
    client: BusinessClient
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
        if not isinstance(request_id, (str, bytes)) or len(request_id) > 40:
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


class Counterparty(utils._UpdateFromKwargsMixin):
    client: BusinessClient
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


class ExternalCounterparty(utils._UpdateFromKwargsMixin):
    """Describes a non-Revolut counterparty. Objects of this class should be used only to
    create such counterparties. The `.save()` method will return the resulting `Counterparty`
    object and the original `ExternalCounterparty` should be discarded afterwards."""

    id: Optional[str] = None
    client: BusinessClient
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


class CounterpartyAccount(utils._UpdateFromKwargsMixin):
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


class Transaction(utils._UpdateFromKwargsMixin):
    id: Optional[str] = None
    client: BusinessClient
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
