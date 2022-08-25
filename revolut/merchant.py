from datetime import datetime
import dateutil.parser
from decimal import Decimal
import requests
from typing import Optional

from . import base, utils


class MerchantClient(base.BaseClient):
    merchant_key: Optional[str] = None
    sandbox: bool = False

    def __init__(self, merchant_key, sandbox=False, timeout=None):
        self.sandbox = sandbox
        if sandbox:
            self.base_url = "https://sandbox-merchant.revolut.com/api/1.0/"
        else:
            self.base_url = "https://merchant.revolut.com/api/1.0/"
        self.merchant_key = merchant_key
        self.timeout = timeout
        self._requester = requests.Session()
        self._requester.headers.update(
            {"Authorization": "Bearer {}".format(self.merchant_key)}
        )

    def create_order(self, amount, currency, reference):
        amount = utils._moneytointeger(amount)
        data = self._post(
            "orders",
            data={
                "amount": amount,
                "currency": currency,
                "merchant_order_ext_ref": reference,
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
        _ = self._post(f"webhooks", data=reqdata)


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
    value = Decimal(0)
    currency: str = ""
    order_amount: str = ""
    order_outstanding_amount: str = ""
    metadata: str = ""
    customer_id: str = ""
    email: str = ""
    completed_at: Optional[datetime] = None
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