from datetime import date, datetime
import dateutil.parser
from decimal import Decimal
import requests
from typing import Optional, Union

from . import base, utils


class Order(utils._UpdateFromKwargsMixin):
    id: str = ""
    client = None
    public_id: str = ""
    merchant_order_ext_ref: str = ""
    type: str = ""
    state: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    capture_mode: str = ""
    currency: str = ""
    order_amount: Optional[dict] = None
    order_outstanding_amount: Optional[dict] = None
    refunded_amount: Optional[dict] = None
    description: Optional[str] = None
    metadata: str = ""
    customer_id: Optional[str] = None
    email: Optional[str] = None
    phone: str = ""
    completed_at: Optional[datetime] = None
    payments: Optional[list] = None
    related: Optional[list] = None
    shipping_address: Optional[dict] = None
    checkout_url: str = ""

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
        self.shipping_address = kwargs.get("shipping_address", {})

    @property
    def currency(self) -> Optional[str]:
        """
        Returns the currency taken from ``self.order_amount["currency"]``.
        """
        return self.order_amount.get("currency", None)

    @currency.setter
    def currency(self, currency: str):
        """
        Sets the currency into ``self.order_amount["currency"]``.
        """
        self.order_amount["currency"] = currency

    @property
    def value(self) -> Optional[Decimal]:
        """
        Returns the value of the order taken from ``self.order_amount["value"]``
        and converted to ``Decimal``.
        """
        if self.order_amount.get("value") is None:
            return None
        return utils._integertomoney(self.order_amount["value"])

    @value.setter
    def value(self, val: Decimal):
        """
        Sets proper ``self.order_amount["value"]`` from given ``Decimal``.
        """
        self.order_amount["value"] = utils._moneytointeger(val)

    @property
    def outstanding_value(self) -> Optional[Decimal]:
        if (
            not self.order_outstanding_amount
            or self.order_outstanding_amount.get("value") is None
        ):
            return None
        return utils._integertomoney(self.order_outstanding_amount["value"])

    @property
    def refunded_value(self) -> Optional[Decimal]:
        if not self.refunded_amount or self.refunded_amount.get("value") is None:
            return None
        return utils._integertomoney(self.refunded_amount["value"])

    def save(self) -> None:
        data = {}
        for k in (
            "merchant_order_ext_ref",
            "currency",
            "description",
            "email",
            "customer_id",
            "capture_mode",
            "shipping_address",
        ):
            v = getattr(self, k)
            if v is not None and v != {}:
                data[k] = v
        data["amount"] = self.order_amount["value"]
        respdata = self.client._patch(f"orders/{self.id}", data)
        self._update(**respdata)


class MerchantClient(base.BaseClient):
    merchant_key: Optional[str] = None
    sandbox: bool = False

    def __init__(
        self,
        merchant_key: str,
        sandbox: bool = False,
        timeout: Optional[Union[int, float]] = None,
    ):
        """
        Client to the Merchant API. The authorization is based upon the secret key
        passed as ``merchant_key`` argument. The connection is stateless.

        As there's no simple distinction between production and sandbox, the environment
        is determined upon the state of the ``sandbox`` flag.
        """
        self.sandbox = sandbox
        if sandbox:
            self.base_url = "https://sandbox-merchant.revolut.com/api/1.0/"
        else:
            self.base_url = "https://merchant.revolut.com/api/1.0/"  # pragma: nocover
        self.merchant_key = merchant_key
        self.timeout = timeout
        self._requester = requests.Session()
        self._requester.headers.update(
            {"Authorization": "Bearer {}".format(self.merchant_key)}
        )

    def create_order(
        self, amount: Union[Decimal, int], currency: str, merchant_reference: str
    ) -> Order:
        """
        Creates an order with ``merchant_reference`` being a custom identifier.

        **WARNING:** The amount of the order has to be specified in regular currency units, even
        though Revolut uses integer denomination of 1/100th of the unit.
        """
        amount = utils._moneytointeger(amount)
        data = self._post(
            "orders",
            data={
                "amount": amount,
                "currency": currency,
                "merchant_order_ext_ref": merchant_reference,
            }
            or None,
        )
        return Order(client=self, **data)

    def get_order(self, order_id: str) -> Order:
        """
        Retrieves ``Order`` with the given ID.
        """
        data = self._get(f"orders/{order_id}")
        return Order(client=self, **data)

    def orders(
        self,
        from_date: Optional[Union[date, datetime]] = None,
        to_date: Optional[Union[date, datetime]] = None,
    ) -> [Order]:
        """
        Retrieves a list of ``Order``s, optionally within the given time span.
        """
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
        _ = self._post(f"webhooks", data=reqdata)
