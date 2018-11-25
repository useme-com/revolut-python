from datetime import datetime, date
from decimal import Decimal
import json
import os
import responses
from unittest import TestCase

from revolut import (
    Client, Account,
    Counterparty, CounterpartyAccount,
    Transaction,
    exceptions, utils)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

class TestRevolut(TestCase):
    key = 'sand_mx4sDGo356ZndtVsOq16SBrilRuQc8DkSIS84ioMlfx'

    def _read(self, name):
        with open(os.path.join(DATA_DIR, name), 'r') as fh:
            return json.loads(fh.read())

    def test_key(self):
        cli = Client(self.key)
        self.assertFalse(cli.live)
        cli = Client('prod_mx4sDGo356ZndtVsOq16SBrilRuQc8DkSIS84ioMlfx')
        self.assertTrue(cli.live)
        self.assertRaises(ValueError, Client, 'whatever')
        self.assertRaises(ValueError, Client)

    @responses.activate
    def test_404(self):
        responses.add(responses.GET, 'https://sandbox-b2b.revolut.com/api/1.0/whatever',
            json={'message': 'The requested resource not found'}, status=404)

        cli = Client(self.key)
        self.assertRaises(exceptions.RevolutHttpError, cli._get, 'whatever')

    @responses.activate
    def test_accounts(self):
        refresh_id = 'be8932d2-bf0d-4311-808f-fe9439d592df'
        responses.add(responses.GET, 'https://sandbox-b2b.revolut.com/api/1.0/accounts',
            json=self._read('accounts.json'), status=200)
        responses.add(responses.GET,
            'https://sandbox-b2b.revolut.com/api/1.0/accounts/{}'.format(refresh_id),
            json=self._read('account-{}.json'.format(refresh_id)), status=200)

        cli = Client(self.key)
        accounts = cli.accounts
        self.assertEqual(6, len(accounts))
        self.assertIs(accounts, cli.accounts)
        refresh_acc = None
        for accid,acc in accounts.items():
            self.assertEqual(accid, acc.id)
            self.assertIsInstance(acc, Account)
            self.assertIsInstance(acc.balance, Decimal)
            self.assertIsInstance(acc.created_at, datetime)
            self.assertIsInstance(acc.updated_at, datetime)
            if acc.id == refresh_id:
                refresh_acc = acc
        acc = refresh_acc.refresh()
        self.assertIsInstance(acc, Account)
        self.assertEqual(repr(acc), '<Account {}>'.format(refresh_id))
        self.assertIsInstance(acc.balance, Decimal)
        self.assertIsInstance(acc.created_at, datetime)
        self.assertIsInstance(acc.updated_at, datetime)

    @responses.activate
    def test_counterparties(self):
        responses.add(responses.GET, 'https://sandbox-b2b.revolut.com/api/1.0/counterparties',
            json=self._read('counterparties.json'), status=200)

        cli = Client(self.key)
        counterparties = cli.counterparties
        self.assertEqual(2, len(counterparties))
        self.assertIs(counterparties, cli.counterparties)
        for cptid,cpt in counterparties.items():
            self.assertEqual(cptid, cpt.id)
            self.assertIsInstance(cpt, Counterparty)
            self.assertIsInstance(cpt.created_at, datetime)
            self.assertIsInstance(cpt.updated_at, datetime)
            for accid,acc in cpt.accounts.items():
                self.assertIsInstance(acc, CounterpartyAccount)
                self.assertEqual(accid, acc.id)

    @responses.activate
    def test_add_counterparty_personal(self):
        cpt_id = '6aa7d45f-ea8a-42cf-b69a-c53848d1ffd1'
        responses.add(responses.POST, 'https://sandbox-b2b.revolut.com/api/1.0/counterparty',
            json=self._read('counterparty-{}.json'.format(cpt_id)), status=200)
        responses.add(responses.GET, 'https://sandbox-b2b.revolut.com/api/1.0/counterparties',
            json=self._read('counterparties.json'), status=200)
        responses.add(responses.GET,
            'https://sandbox-b2b.revolut.com/api/1.0/counterparty/{}'.format(cpt_id),
            json=self._read('counterparty-{}.json'.format(cpt_id)), status=200)
        responses.add(responses.POST, 'https://sandbox-b2b.revolut.com/api/1.0/counterparty',
            json={'message': 'This counterparty already exists'}, status=422)
        responses.add(responses.POST, 'https://sandbox-b2b.revolut.com/api/1.0/counterparty',
            json={'message': 'This counterparty already exists'}, status=422)

        cli = Client(self.key)
        cpt = Counterparty(
            client=cli,
            profile_type='personal',
            name='Alice Tester',
            phone='+4412345678901')
        self.assertEqual(str(cpt), 'Id: NO ID personal Alice Tester +4412345678901')
        cpt.save()
        self.assertEqual(repr(cpt), '<Counterparty {}>'.format(cpt_id))
        self.assertEqual(str(cpt), 'Id: 6aa7d45f-ea8a-42cf-b69a-c53848d1ffd1 personal Alice Tester +4412345678901')
        self.assertIsInstance(cpt.created_at, datetime)
        self.assertIsInstance(cpt.updated_at, datetime)
        for accid,acc in cpt.accounts.items():
            self.assertIsInstance(acc, CounterpartyAccount)
            self.assertEqual(accid, acc.id)
        self.assertRaises(exceptions.CounterpartyAlreadyExists, cpt.save)
        self.assertIs(cpt, cpt.refresh())
        cpt = Counterparty(
            client=cli,
            profile_type='personal',
            name='Bob Tester',
            phone='+4412345678901')
        self.assertRaises(exceptions.CounterpartyAlreadyExists, cpt.save)

    @responses.activate
    def test_add_counterparty_business(self):
        cpt_id = 'a630f150-4a22-42d7-82f2-74d9c5da7c35'
        responses.add(responses.POST, 'https://sandbox-b2b.revolut.com/api/1.0/counterparty',
            json=self._read('counterparty-{}.json'.format(cpt_id)), status=200)
        responses.add(responses.GET, 'https://sandbox-b2b.revolut.com/api/1.0/counterparties',
            json=self._read('counterparties.json'), status=200)
        responses.add(responses.GET,
            'https://sandbox-b2b.revolut.com/api/1.0/counterparty/{}'.format(cpt_id),
            json=self._read('counterparty-{}.json'.format(cpt_id)), status=200)
        responses.add(responses.POST, 'https://sandbox-b2b.revolut.com/api/1.0/counterparty',
            json={'message': 'This counterparty already exists'}, status=422)
        responses.add(responses.POST, 'https://sandbox-b2b.revolut.com/api/1.0/counterparty',
            json={'message': 'This counterparty already exists'}, status=422)

        cli = Client(self.key)
        cpt = Counterparty(
            client=cli,
            profile_type='business',
            email='test@sandboxcorp.com')
        self.assertEqual(str(cpt), 'Id: NO ID business  test@sandboxcorp.com')
        cpt.save()
        self.assertEqual(repr(cpt), '<Counterparty {}>'.format(cpt_id))
        self.assertEqual(
            str(cpt),
            'Id: a630f150-4a22-42d7-82f2-74d9c5da7c35 business The sandbox corp test@sandboxcorp.com')
        self.assertIsInstance(cpt.created_at, datetime)
        self.assertIsInstance(cpt.updated_at, datetime)
        for accid,acc in cpt.accounts.items():
            self.assertIsInstance(acc, CounterpartyAccount)
            self.assertEqual(accid, acc.id)
        self.assertRaises(exceptions.CounterpartyAlreadyExists, cpt.save)
        self.assertIs(cpt, cpt.refresh())
        cpt = Counterparty(
            client=cli,
            profile_type='business',
            email='test@sandboxcorp.com')
        self.assertRaises(exceptions.CounterpartyAlreadyExists, cpt.save)

    def test_add_counterparty_invalid(self):
        cli = Client(self.key)
        cpt = Counterparty(client=cli, profile_type='whatever')
        self.assertRaises(ValueError, cpt.save)

    @responses.activate
    def test_transfer_internal(self):
        tx_id = 'd1a0d6e6-9290-4ac9-87e8-15697da5f7db'
        responses.add(responses.GET, 'https://sandbox-b2b.revolut.com/api/1.0/accounts',
            json=self._read('accounts.json'), status=200)
        responses.add(responses.GET, 'https://sandbox-b2b.revolut.com/api/1.0/counterparties',
            json=self._read('counterparties.json'), status=200)
        responses.add(responses.POST, 'https://sandbox-b2b.revolut.com/api/1.0/transfer',
            json=self._read('transfer-{}.json'.format(tx_id)), status=200)
        responses.add(responses.GET,
            'https://sandbox-b2b.revolut.com/api/1.0/transaction/{}'.format(tx_id),
            json=self._read('transaction-{}.json'.format(tx_id)), status=200)

        cli = Client(self.key)
        tx = cli.accounts['be8932d2-bf0d-4311-808f-fe9439d592df'].send(
                'c4ff8afa-54bb-4b2e-acb7-d0a95fb3b996',
                100, 'GBP',
                'req-{}'.format(datetime.now().isoformat()),
                reference='Transfer between own accounts')

    @responses.activate
    def test_pay_to_revolut(self):
        tx_id = 'a67b182e-91f0-4d03-9c04-8a5e24aff4b0'
        responses.add(responses.GET, 'https://sandbox-b2b.revolut.com/api/1.0/accounts',
            json=self._read('accounts.json'), status=200)
        responses.add(responses.GET, 'https://sandbox-b2b.revolut.com/api/1.0/counterparties',
            json=self._read('counterparties.json'), status=200)
        responses.add(responses.POST, 'https://sandbox-b2b.revolut.com/api/1.0/pay',
            json=self._read('pay-{}.json'.format(tx_id)), status=200)
        responses.add(responses.GET,
            'https://sandbox-b2b.revolut.com/api/1.0/transaction/{}'.format(tx_id),
            json=self._read('transaction-{}.json'.format(tx_id)), status=200)
        responses.add(responses.GET,
            'https://sandbox-b2b.revolut.com/api/1.0/transactions',
            json=[self._read('transaction-{}.json'.format(tx_id))], status=200)

        cli = Client(self.key)
        tx = cli.accounts['be8932d2-bf0d-4311-808f-fe9439d592df'].send(
                '2d689cbd-1dc5-4e1b-a1bb-bc2b17c75a6c',
                1, 'GBP',
                'req-{}'.format(datetime.now().isoformat()),
                reference='A test payment of 1 GBP')
        txns = cli.transactions(counterparty='2d689cbd-1dc5-4e1b-a1bb-bc2b17c75a6c')
        self.assertEqual(1, len(txns))
        self.assertIsInstance(txns[0], Transaction)
        self.assertEqual(tx.id, txns[0].id)
        self.assertEqual('<Transaction {}>'.format(tx.id), repr(txns[0]))

    @responses.activate
    def test_pay_to_revolut_with_conversion(self):
        tx_id = 'ab22ad5b-e8d7-40d9-b55c-adac6777e95b'
        responses.add(responses.GET, 'https://sandbox-b2b.revolut.com/api/1.0/accounts',
            json=self._read('accounts.json'), status=200)
        responses.add(responses.GET, 'https://sandbox-b2b.revolut.com/api/1.0/counterparties',
            json=self._read('counterparties.json'), status=200)
        responses.add(responses.POST, 'https://sandbox-b2b.revolut.com/api/1.0/pay',
            json=self._read('pay-{}.json'.format(tx_id)), status=200)
        responses.add(responses.GET,
            'https://sandbox-b2b.revolut.com/api/1.0/transaction/{}'.format(tx_id),
            json=self._read('transaction-{}.json'.format(tx_id)), status=200)
        responses.add(responses.GET,
            'https://sandbox-b2b.revolut.com/api/1.0/transactions',
            json=[self._read('transaction-{}.json'.format(tx_id))], status=200)

        cli = Client(self.key)
        tx = cli.accounts['be8932d2-bf0d-4311-808f-fe9439d592df'].send(
                'ed50b331-5b2c-42e4-afbe-0e883bc12e60',
                100, 'EUR',
                'req-{}'.format(datetime.now().isoformat()),
        reference='EUR from GBP')
        txns = cli.transactions(counterparty='ed50b331-5b2c-42e4-afbe-0e883bc12e60')
        self.assertEqual(1, len(txns))
        self.assertIsInstance(txns[0], Transaction)
        self.assertEqual(tx.id, txns[0].id)
        self.assertEqual('<Transaction {}>'.format(tx.id), repr(txns[0]))

class TestUtils(TestCase):
    def test_date(self):
        self.assertEqual(date(1977, 9, 5), utils._date('1977-9-5'))
        self.assertEqual(date(1977, 9, 5), utils._date('1977-9-05'))
        self.assertEqual(date(1977, 9, 5), utils._date('9-5-1977'))   # not in Fahrenheit, at least
        self.assertEqual(date(1977, 9, 5), utils._date('1977-09-05 12:56:00+00:00'))
        self.assertEqual(date(1977, 9, 5), utils._date(date(1977,9, 5)))
        self.assertEqual(date(1977, 9, 5), utils._date(datetime(1977, 9, 5, 12, 56, 0)))
