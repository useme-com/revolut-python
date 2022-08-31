from datetime import datetime
from decimal import Decimal
import responses
from unittest import TestCase

from revolut.merchant import (
    MerchantClient,
    Order,
)

from . import JSONResponsesMixin


class TestRevolutMerchant(TestCase, JSONResponsesMixin):
    merchant_key = "sk_3TKDCGJff10gMl4nzrB0KPuwso7uZS9ASWTCebCz027E8bpRp67YK5m4gnMweCr5"

    @responses.activate
    def test_orders(self):
        ORDER_ID = "0f1e2ffc-6cd4-45be-8fb6-da3705cf321f"
        responses.add(
            responses.POST,
            "https://sandbox-merchant.revolut.com/api/1.0/orders",
            json=self._read("10-create_order.json"),
            status=200,
        )
        cli = MerchantClient(self.merchant_key, sandbox=True)
        order = cli.create_order(Decimal("12.34"), "PLN", "a test order in PLN")
        self.assertEqual(order.value, Decimal("12.34"))
        self.assertDictEqual(order.order_amount, {"value": 1234, "currency": "PLN"})
        self.assertEqual(order.id, ORDER_ID)
        self.assertIsInstance(order.created_at, datetime)
        self.assertIsInstance(order.updated_at, datetime)

        responses.add(
            responses.GET,
            "https://sandbox-merchant.revolut.com/api/1.0/orders",
            json=self._read("20-orders.json"),
            status=200,
        )
        orders = cli.orders()
        self.assertEqual(len(orders), 2)
        self.assertIsInstance(orders[0], Order)
        self.assertIsInstance(orders[1], Order)

        responses.add(
            responses.GET,
            f"https://sandbox-merchant.revolut.com/api/1.0/orders/{ORDER_ID}",
            json=self._read("30-order.json"),
            status=200,
        )
        self.assertEqual(order.value, Decimal("12.34"))
        self.assertDictEqual(order.order_amount, {"value": 1234, "currency": "PLN"})
        self.assertEqual(order.id, ORDER_ID)
        self.assertIsInstance(order.created_at, datetime)
        self.assertIsInstance(order.updated_at, datetime)
