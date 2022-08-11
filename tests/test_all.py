from datetime import datetime, date
from decimal import Decimal
import inspect
import json
import operator
import os
import responses
from unittest import TestCase

from revolut import (
    Client,
    Account,
    Counterparty,
    ExternalCounterparty,
    CounterpartyAccount,
    Transaction,
    exceptions,
    utils,
)
from revolut.session import TemporarySession, RenewableSession, TokenProvider

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class JSONResponsesMixin(object):
    def _read(self, name):
        caller_name = inspect.getouterframes(inspect.currentframe(), 2)[1][3]
        with open(os.path.join(DATA_DIR, caller_name, name), "r") as fh:
            return json.loads(fh.read())


class TestTokens(TestCase, JSONResponsesMixin):
    client_id = "rmPBoIc-LR3ObABUn-NKHq6WyEoCr6Lh__DFohuMRVM"
    auth_code = "oa_prod_gg-_wDV66wYfKKpnF4RIrpOZs2oPTwNp4TXOra5pS0g"
    jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9l"
        "IiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    refresh_token = "oa_prod_gg-_wDV66wYfKKpnF4RIrpOZs2oPTwNp4TXOra5pS0g"
    request_url = "https://b2b.revolut.com/api/1.0/auth/token"

    @responses.activate
    def test_get_tokens_by_auth_code(self):
        responses.add(
            responses.POST,
            self.request_url,
            json=self._read("token-authorization_code.json"),
            status=200,
        )
        tpr = TokenProvider(self.auth_code, self.client_id, self.jwt)
        self.assertIn("grant_type=authorization_code", responses.calls[0].request.body)
        self.assertIsNotNone(tpr.access_token)
        self.assertIsNotNone(tpr.refresh_token)

    @responses.activate
    def test_refresh_token_via_renewable_session(self):
        responses.add(
            responses.POST,
            self.request_url,
            json=self._read("token-refresh_token.json"),
            status=200,
        )
        sess = RenewableSession(self.refresh_token, self.client_id, self.jwt)
        self.assertIsNotNone(sess.access_token)
        self.assertIn("grant_type=refresh_token", responses.calls[0].request.body)


class TestRevolut(TestCase, JSONResponsesMixin):
    access_token = "oa_sand_lI35rv-tpvl0qsKa5OJGW5yiiXtKg7uZYB6b0jmLSCk"

    def test_key(self):
        tssn = TemporarySession(self.access_token)
        cli = Client(tssn)
        self.assertFalse(cli.live)
        pssn = TemporarySession("oa_prod_mx4sDGo356ZndtVsOq16SBrilRuQc8DkSIS84ioMlfx")
        cli = Client(pssn)
        self.assertTrue(cli.live)

    @responses.activate
    def test_404(self):
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/whatever",
            json={"message": "The requested resource not found"},
            status=404,
        )

        tssn = TemporarySession(self.access_token)
        cli = Client(tssn)
        self.assertRaises(exceptions.RevolutHttpError, cli._get, "whatever")

    @responses.activate
    def test_accounts(self):
        refresh_id = "be8932d2-bf0d-4311-808f-fe9439d592df"
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/accounts",
            json=self._read("10-accounts.json"),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/accounts/{}".format(refresh_id),
            json=self._read("20-account-{}.json".format(refresh_id)),
            status=200,
        )

        tssn = TemporarySession(self.access_token)
        cli = Client(tssn)
        accounts = cli.accounts
        self.assertEqual(6, len(accounts))
        self.assertIs(accounts, cli.accounts)
        refresh_acc = None
        for accid, acc in accounts.items():
            self.assertEqual(accid, acc.id)
            self.assertIsInstance(acc, Account)
            self.assertIsInstance(acc.balance, Decimal)
            self.assertIsInstance(acc.created_at, datetime)
            self.assertIsInstance(acc.updated_at, datetime)
            if acc.id == refresh_id:
                refresh_acc = acc
        acc = refresh_acc.refresh()
        self.assertIsInstance(acc, Account)
        self.assertEqual(repr(acc), "<Account {}>".format(refresh_id))
        self.assertIsInstance(acc.balance, Decimal)
        self.assertIsInstance(acc.created_at, datetime)
        self.assertIsInstance(acc.updated_at, datetime)

    @responses.activate
    def test_counterparties(self):
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparties",
            json=self._read("10-counterparties.json"),
            status=200,
        )

        tssn = TemporarySession(self.access_token)
        cli = Client(tssn)
        counterparties = cli.counterparties
        self.assertEqual(2, len(counterparties))
        self.assertIs(counterparties, cli.counterparties)
        for cptid, cpt in counterparties.items():
            self.assertEqual(cptid, cpt.id)
            self.assertIsInstance(cpt, Counterparty)
            self.assertIsInstance(cpt.created_at, datetime)
            self.assertIsInstance(cpt.updated_at, datetime)
            for accid, acc in cpt.accounts.items():
                self.assertIsInstance(acc, CounterpartyAccount)
                self.assertEqual(accid, acc.id)

    @responses.activate
    def test_delete_counterparty(self):
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparties",
            json=self._read("10-counterparties.json"),
            status=200,
        )
        tssn = TemporarySession(self.access_token)
        cli = Client(tssn)
        counterparties = list(
            sorted(cli.counterparties.items(), key=operator.itemgetter(0))
        )
        for cptid, cpt in counterparties:
            responses.add(
                responses.DELETE,
                "https://sandbox-b2b.revolut.com/api/1.0/counterparty/{}".format(
                    cpt.id
                ),
                status=204,
            )
        for cptid, cpt in counterparties:
            cpt.delete()
            self.assertIsNone(cpt.id)
            self.assertRaises(ValueError, cpt.delete)
            self.assertNotIn(cptid, cli.counterparties)

    @responses.activate
    def test_add_counterparty_personal(self):
        cpt_id = "6aa7d45f-ea8a-42cf-b69a-c53848d1ffd1"
        responses.add(
            responses.POST,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparty",
            json=self._read("10-counterparty-{}.json".format(cpt_id)),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparties",
            json=self._read("20-counterparties.json"),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparty/{}".format(cpt_id),
            json=self._read("30-counterparty-{}.json".format(cpt_id)),
            status=200,
        )
        responses.add(
            responses.POST,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparty",
            json={"message": "This counterparty already exists"},
            status=422,
        )
        responses.add(
            responses.POST,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparty",
            json={"message": "This counterparty already exists"},
            status=422,
        )

        tssn = TemporarySession(self.access_token)
        cli = Client(tssn)
        cpt = Counterparty(
            client=cli,
            profile_type="personal",
            name="Alice Tester",
            phone="+4412345678901",
        )
        self.assertEqual(str(cpt), "Id: NO ID personal Alice Tester +4412345678901")
        cpt.save()
        self.assertEqual(repr(cpt), "<Counterparty {}>".format(cpt_id))
        self.assertEqual(
            str(cpt),
            "Id: 6aa7d45f-ea8a-42cf-b69a-c53848d1ffd1 personal Alice Tester +4412345678901",
        )
        self.assertIsInstance(cpt.created_at, datetime)
        self.assertIsInstance(cpt.updated_at, datetime)
        for accid, acc in cpt.accounts.items():
            self.assertIsInstance(acc, CounterpartyAccount)
            self.assertEqual(accid, acc.id)
        self.assertRaises(exceptions.CounterpartyAlreadyExists, cpt.save)
        self.assertIs(cpt, cpt.refresh())
        cpt = Counterparty(
            client=cli,
            profile_type="personal",
            name="Bob Tester",
            phone="+4412345678901",
        )
        self.assertRaises(exceptions.CounterpartyAlreadyExists, cpt.save)

    @responses.activate
    def test_add_counterparty_business(self):
        cpt_id = "a630f150-4a22-42d7-82f2-74d9c5da7c35"
        responses.add(
            responses.POST,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparty",
            json=self._read("10-counterparty-{}.json".format(cpt_id)),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparties",
            json=self._read("20-counterparties.json"),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparty/{}".format(cpt_id),
            json=self._read("30-counterparty-{}.json".format(cpt_id)),
            status=200,
        )
        responses.add(
            responses.POST,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparty",
            json={"message": "This counterparty already exists"},
            status=422,
        )
        responses.add(
            responses.POST,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparty",
            json={"message": "This counterparty already exists"},
            status=422,
        )

        tssn = TemporarySession(self.access_token)
        cli = Client(tssn)
        cpt = Counterparty(
            client=cli, profile_type="business", email="test@sandboxcorp.com"
        )
        self.assertEqual(str(cpt), "Id: NO ID business  test@sandboxcorp.com")
        cpt.save()
        self.assertEqual(repr(cpt), "<Counterparty {}>".format(cpt_id))
        self.assertEqual(
            str(cpt),
            "Id: a630f150-4a22-42d7-82f2-74d9c5da7c35 business The sandbox corp test@sandboxcorp.com",
        )
        self.assertIsInstance(cpt.created_at, datetime)
        self.assertIsInstance(cpt.updated_at, datetime)
        for accid, acc in cpt.accounts.items():
            self.assertIsInstance(acc, CounterpartyAccount)
            self.assertEqual(accid, acc.id)
        self.assertRaises(exceptions.CounterpartyAlreadyExists, cpt.save)
        self.assertIs(cpt, cpt.refresh())
        cpt = Counterparty(
            client=cli, profile_type="business", email="test@sandboxcorp.com"
        )
        self.assertRaises(exceptions.CounterpartyAlreadyExists, cpt.save)

    @responses.activate
    def test_add_counterparty_external(self):
        cpt_id = "d7d28bee-d895-4e14-a212-813babffdd8f"
        responses.add(
            responses.POST,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparty",
            json=self._read("10-counterparty-{}.json".format(cpt_id)),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparties",
            json=self._read("20-counterparties.json"),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparty/{}".format(cpt_id),
            json=self._read("30-counterparty-{}.json".format(cpt_id)),
            status=200,
        )
        responses.add(
            responses.POST,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparty",
            json={"message": "This counterparty already exists"},
            status=422,
        )

        tssn = TemporarySession(self.access_token)
        cli = Client(tssn)
        cpt = ExternalCounterparty(
            client=cli,
            company_name="Kogucik S.A.",
            bank_country="PL",
            currency="PLN",
            phone="+48123456789",
            email="michal@salaban.info",
            address={
                "street_line1": "The Street Address Line 1",
                "street_line2": "The Street Address Line 2",
                "region": "The Region",
                "city": "The City",
                "country": "PL",
                "postcode": "53-405",
            },
            iban="PL50102055581111148825600052",
            bic="BPKOPLPW",
        )
        self.assertEqual(str(cpt), "Id: NO ID Kogucik S.A.")
        ncpt = cpt.save()
        self.assertEqual(cpt.id, cpt_id)
        self.assertIsInstance(ncpt, Counterparty)
        self.assertEqual(repr(ncpt), "<Counterparty {}>".format(cpt_id))
        self.assertIsNone(ncpt.profile_type)
        self.assertEqual(
            str(ncpt), "Id: d7d28bee-d895-4e14-a212-813babffdd8f  Kogucik S.A."
        )
        self.assertIsInstance(ncpt.created_at, datetime)
        self.assertIsInstance(ncpt.updated_at, datetime)
        for accid, acc in ncpt.accounts.items():
            self.assertIsInstance(acc, CounterpartyAccount)
            self.assertEqual(accid, acc.id)

    def test_add_counterparty_invalid(self):
        tssn = TemporarySession(self.access_token)
        cli = Client(tssn)
        cpt = Counterparty(client=cli, profile_type="whatever")
        self.assertRaises(ValueError, cpt.save)

    @responses.activate
    def test_transfer_internal(self):
        tx_id = "d1a0d6e6-9290-4ac9-87e8-15697da5f7db"
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/accounts",
            json=self._read("10-accounts.json"),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparties",
            json=self._read("20-counterparties.json"),
            status=200,
        )
        responses.add(
            responses.POST,
            "https://sandbox-b2b.revolut.com/api/1.0/transfer",
            json=self._read("30-transfer-{}.json".format(tx_id)),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/transaction/{}".format(tx_id),
            json=self._read("40-transaction-{}.json".format(tx_id)),
            status=200,
        )

        tssn = TemporarySession(self.access_token)
        cli = Client(tssn)
        tx = cli.accounts["be8932d2-bf0d-4311-808f-fe9439d592df"].send(
            "c4ff8afa-54bb-4b2e-acb7-d0a95fb3b996",
            100,
            "GBP",
            "req-{}".format(datetime.now().isoformat()),
            reference="Transfer between own accounts",
        )
        self.assertIsInstance(tx.legs[0]["amount"], Decimal)
        self.assertIsInstance(tx.legs[1]["amount"], Decimal)

    @responses.activate
    def test_pay_to_revolut(self):
        tx_id = "a67b182e-91f0-4d03-9c04-8a5e24aff4b0"
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/accounts",
            json=self._read("10-accounts.json"),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparties",
            json=self._read("20-counterparties.json"),
            status=200,
        )
        responses.add(
            responses.POST,
            "https://sandbox-b2b.revolut.com/api/1.0/pay",
            json=self._read("30-pay-{}.json".format(tx_id)),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/transaction/{}".format(tx_id),
            json=self._read("40-transaction-{}.json".format(tx_id)),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/transactions",
            json=[self._read("50-transaction-{}.json".format(tx_id))],
            status=200,
        )

        tssn = TemporarySession(self.access_token)
        cli = Client(tssn)
        tx = cli.accounts["be8932d2-bf0d-4311-808f-fe9439d592df"].send(
            "2d689cbd-1dc5-4e1b-a1bb-bc2b17c75a6c",
            1,
            "GBP",
            "req-{}".format(datetime.now().isoformat()),
            reference="A test payment of 1 GBP",
        )
        self.assertIsInstance(tx.legs[0]["amount"], Decimal)

        txns = cli.transactions(counterparty="2d689cbd-1dc5-4e1b-a1bb-bc2b17c75a6c")
        self.assertEqual(1, len(txns))
        self.assertIsInstance(txns[0], Transaction)
        self.assertEqual(tx.id, txns[0].id)
        self.assertEqual("<Transaction {}>".format(tx.id), repr(txns[0]))

    @responses.activate
    def test_pay_to_revolut_with_conversion(self):
        tx_id = "ab22ad5b-e8d7-40d9-b55c-adac6777e95b"
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/accounts",
            json=self._read("10-accounts.json"),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparties",
            json=self._read("20-counterparties.json"),
            status=200,
        )
        responses.add(
            responses.POST,
            "https://sandbox-b2b.revolut.com/api/1.0/pay",
            json=self._read("30-pay-{}.json".format(tx_id)),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/transaction/{}".format(tx_id),
            json=self._read("40-transaction-{}.json".format(tx_id)),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/transactions",
            json=[self._read("50-transaction-{}.json".format(tx_id))],
            status=200,
        )

        tssn = TemporarySession(self.access_token)
        cli = Client(tssn)
        tx = cli.accounts["be8932d2-bf0d-4311-808f-fe9439d592df"].send(
            "ed50b331-5b2c-42e4-afbe-0e883bc12e60",
            100,
            "EUR",
            "req-{}".format(datetime.now().isoformat()),
            reference="EUR from GBP",
        )
        self.assertIsInstance(tx.legs[0]["amount"], Decimal)

        txns = cli.transactions(counterparty="ed50b331-5b2c-42e4-afbe-0e883bc12e60")
        self.assertEqual(1, len(txns))
        self.assertIsInstance(txns[0], Transaction)
        self.assertEqual(tx.id, txns[0].id)
        self.assertEqual("<Transaction {}>".format(tx.id), repr(txns[0]))

    @responses.activate
    def test_transfer_to_counterparty_personal(self):
        cpt_id = "0ff7abd1-ee59-431c-aed1-3d6d419b434d"
        tx_id = "60d2eff2-e8e1-a82d-81bb-deabff41e739"
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/accounts",
            json=self._read("10-accounts.json"),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/counterparties",
            json=self._read("20-counterparties.json"),
            status=200,
        )
        responses.add(
            responses.POST,
            "https://sandbox-b2b.revolut.com/api/1.0/pay",
            json=self._read("30-pay.json"),
            status=200,
        )
        responses.add(
            responses.GET,
            "https://sandbox-b2b.revolut.com/api/1.0/transaction/{:s}".format(tx_id),
            json=self._read("40-transaction-{}.json".format(tx_id)),
            status=200,
        )
        tssn = TemporarySession(self.access_token)
        cli = Client(tssn)
        cpt = cli.counterparties[cpt_id]
        cli.accounts["6ed7aa7c-64d6-4e6f-a52c-6f480a4c94b8"].send(
            cpt.id,
            10,
            "PLN",
            "req-{}".format(datetime.now().isoformat()),
        )


class TestUtils(TestCase):
    def test_date(self):
        self.assertEqual(date(1977, 9, 5), utils._date("1977-9-5"))
        self.assertEqual(date(1977, 9, 5), utils._date("1977-9-05"))
        self.assertEqual(
            date(1977, 9, 5), utils._date("9-5-1977")
        )  # not in Fahrenheit, at least
        self.assertEqual(date(1977, 9, 5), utils._date("1977-09-05 12:56:00+00:00"))
        self.assertEqual(date(1977, 9, 5), utils._date(date(1977, 9, 5)))
        self.assertEqual(date(1977, 9, 5), utils._date(datetime(1977, 9, 5, 12, 56, 0)))
