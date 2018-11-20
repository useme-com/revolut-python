from datetime import datetime
from decimal import Decimal
import json
import os
from unittest import TestCase
try:
    from unittest.mock import patch, Mock
except ImportError:
    from mock import patch, Mock

from revolut import Client, Account, Counterparty, CounterpartyAccount, exceptions

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

class TestAll(TestCase):
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

    @patch('revolut.requests.get')
    def test_404(self, mock_get):
        mock_get.return_value.status_code = 404
        mock_get.return_value.json.return_value = {'message': 'The requested resource not found'}
        cli = Client(self.key)
        self.assertRaises(exceptions.RevolutHttpError, cli._get, 'whatever')

    @patch('revolut.requests.get')
    def test_accounts(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self._read('accounts.json')
        cli = Client(self.key)
        accounts = cli.accounts
        self.assertEqual(6, len(accounts))
        self.assertIs(accounts, cli.accounts)
        refresh_id = 'be8932d2-bf0d-4311-808f-fe9439d592df'
        refresh_acc = None
        for acc in accounts:
            self.assertIsInstance(acc, Account)
            self.assertIsInstance(acc.balance, Decimal)
            self.assertIsInstance(acc.created_at, datetime)
            self.assertIsInstance(acc.updated_at, datetime)
            if acc.id == refresh_id:
                refresh_acc = acc
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self._read('account-be8932d2-bf0d-4311-808f-fe9439d592df.json')
        acc = refresh_acc.refresh()
        self.assertIsInstance(acc, Account)
        self.assertIsInstance(acc.balance, Decimal)
        self.assertIsInstance(acc.created_at, datetime)
        self.assertIsInstance(acc.updated_at, datetime)

    @patch('revolut.requests.get')
    def test_counterparties(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self._read('counterparties.json')
        cli = Client(self.key)
        counterparties = cli.counterparties
        self.assertEqual(2, len(counterparties))
        self.assertIs(counterparties, cli.counterparties)
        for cpt in counterparties:
            self.assertIsInstance(cpt, Counterparty)
            self.assertIsInstance(cpt.created_at, datetime)
            self.assertIsInstance(cpt.updated_at, datetime)
            for acc in cpt.accounts:
                self.assertIsInstance(acc, CounterpartyAccount)

    @patch('revolut.requests.post')
    @patch('revolut.requests.get')
    def test_add_counterparty_personal(self, mock_get, mock_post):
        cli = Client(self.key)
        cpt = Counterparty(
            client=cli,
            profile_type='personal',
            name='Alice Tester',
            phone='+4412345678901')
        self.assertEqual(str(cpt), 'Id: NO ID personal Alice Tester +4412345678901')
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = self._read('counterparty-6aa7d45f-ea8a-42cf-b69a-c53848d1ffd1.json')
        cpt.save()
        self.assertEqual(str(cpt), 'Id: 6aa7d45f-ea8a-42cf-b69a-c53848d1ffd1 personal Alice Tester +4412345678901')
        self.assertIsInstance(cpt.created_at, datetime)
        self.assertIsInstance(cpt.updated_at, datetime)
        for acc in cpt.accounts:
            self.assertIsInstance(acc, CounterpartyAccount)
        self.assertRaises(exceptions.CounterpartyAlreadyExists, cpt.save)

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self._read('counterparty-6aa7d45f-ea8a-42cf-b69a-c53848d1ffd1.json')
        self.assertIs(cpt, cpt.refresh())

        cpt = Counterparty(
            client=cli,
            profile_type='personal',
            name='Bob Tester',
            phone='+4412345678901')
        mock_post.return_value.status_code = 422
        mock_post.return_value.json.return_value = {'message': 'This counterparty already exists'}
        self.assertRaises(exceptions.CounterpartyAlreadyExists, cpt.save)

    @patch('revolut.requests.post')
    @patch('revolut.requests.get')
    def test_add_counterparty_business(self, mock_get, mock_post):
        cli = Client(self.key)
        cpt = Counterparty(
            client=cli,
            profile_type='business',
            email='test@sandboxcorp.com')
        self.assertEqual(str(cpt), 'Id: NO ID business  test@sandboxcorp.com')
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = self._read('counterparty-a630f150-4a22-42d7-82f2-74d9c5da7c35.json')
        cpt.save()
        self.assertEqual(
            str(cpt),
            'Id: a630f150-4a22-42d7-82f2-74d9c5da7c35 business The sandbox corp test@sandboxcorp.com')
        self.assertIsInstance(cpt.created_at, datetime)
        self.assertIsInstance(cpt.updated_at, datetime)
        for acc in cpt.accounts:
            self.assertIsInstance(acc, CounterpartyAccount)
        self.assertRaises(exceptions.CounterpartyAlreadyExists, cpt.save)

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = self._read('counterparty-a630f150-4a22-42d7-82f2-74d9c5da7c35.json')
        self.assertIs(cpt, cpt.refresh())

        cpt = Counterparty(
            client=cli,
            profile_type='business',
            email='test@sandboxcorp.com')
        mock_post.return_value.status_code = 422
        mock_post.return_value.json.return_value = {'message': 'This counterparty already exists'}
        self.assertRaises(exceptions.CounterpartyAlreadyExists, cpt.save)

    def test_add_counterparty_invalid(self):
        cli = Client(self.key)
        cpt = Counterparty(client=cli, profile_type='whatever')
        self.assertRaises(ValueError, cpt.save)
