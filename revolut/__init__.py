import dateutil.parser
from decimal import Decimal
import json
import logging
import pprint
import requests
try:
    from urllib.parse import urljoin    # 3.x
except ImportError:
    from urlparse import urljoin        # 2.x
from . import exceptions

__version__ = '0.1'

_log = logging.getLogger(__name__)


class _UpdateFromKwargsMixin(object):
    def _update(self, **kwargs):
        for k,v in kwargs.items():
            if not hasattr(self, k):
                raise ValueError('Excess keyword for {}: {} = {}'.format(type(self), k,v))
            setattr(self, k, v)


class Client(object):
    key = None
    live = False
    _accounts = None
    _counterparties = None

    def __init__(self, key=None):
        self.key = key or self.key
        if not key:
            raise ValueError('No access key given.')
        if key.startswith('prod'):
            self.base_url = 'https://b2b.revolut.com/api/1.0/'
            self.live = True
        elif key.startswith('sand'):
            self.base_url = 'https://sandbox-b2b.revolut.com/api/1.0/'
            self.live = False
        else:
            raise ValueError(
                'The given key doesn\'t seem to match either production or sandbox environment.')

    def _request(self, func, path, data=None):
        url = urljoin(self.base_url, path)
        hdr = {'Authorization': 'Bearer {}'.format(self.key)}
        _log.debug('{}'.format(path))
        if data is not None:
            _log.debug('data: {}'.format(data))
        rsp = func(url, headers=hdr, data=json.dumps(data) if data else None)
        result = rsp.json()
        if rsp.status_code != 200:
            raise exceptions.RevolutHttpError(rsp.status_code, 'HTTP {} for {}: {}'.format(
                    rsp.status_code, url, result.get('message', 'No message supplied')))
        _ppresult = pprint.pformat(result)
        _log.debug(u'Result:\n{result}'.format(result=_ppresult))
        return result

    def _get(self, path):
        return self._request(requests.get, path)

    def _post(self, path, data=None):
        return self._request(requests.post, path, data or {})

    @property
    def accounts(self):
        if self._accounts is not None:
            return self._accounts
        self._accounts = {}
        data = self._get('accounts')
        for accdat in data:
            acc = Account(client=self, **accdat)
            self._accounts[acc.id] = acc
        return self._accounts

    @property
    def counterparties(self):
        if self._counterparties is not None:
            return self._counterparties
        self._counterparties = {}
        data = self._get('counterparties')
        for cptdat in data:
            cpt = Counterparty(client=self, **cptdat)
            self._counterparties[cpt.id] = cpt
        return self._counterparties


class Account(_UpdateFromKwargsMixin):
    client = None
    id = ''
    name = ''
    currency = ''
    balance = Decimal(0)
    state = ''
    public = False
    created_at = None
    updated_at = None

    def __init__(self, **kwargs):
        self.client = kwargs.pop('client')
        self._update(**kwargs)

    def _update(self, **kwargs):
        super(Account, self)._update(**kwargs)
        self.created_at = dateutil.parser.parse(self.created_at)
        self.updated_at = dateutil.parser.parse(self.updated_at)
        self.balance = Decimal(self.balance)

    def __str__(self):
        return 'Id: {}, {:.2f} {:3s}'.format(self.id, self.balance, self.currency)

    def refresh(self):
        data = self.client._get('accounts/{}'.format(self.id))
        self._update(**data)
        return self

    def details(self):
        return self.client._get('accounts/{}/bank-details'.format(self.id))


class Counterparty(_UpdateFromKwargsMixin):
    client = None
    id = None
    name = ''
    email = ''
    phone = ''
    profile_type = ''
    country = ''
    state = ''
    created_at = None
    updated_at = None
    accounts = None

    def __init__(self, **kwargs):
        self.client = kwargs.pop('client')
        self._update(**kwargs)

    def __str__(self):
        return 'Id: {} {} {} {}'.format(
            self.id or 'NO ID',
            self.profile_type,
            self.name,
            self.email if self.profile_type == 'business' else self.phone)

    def _update(self, **kwargs):
        self.accounts = set()
        for accdat in kwargs.pop('accounts', []):
            Class = CounterpartyAccount if accdat['type'] == 'revolut' else CounterpartyExternalAccount
            self.accounts.add(Class(**accdat))
        super(Counterparty, self)._update(**kwargs)
        self.created_at = dateutil.parser.parse(self.created_at) if self.created_at else None
        self.updated_at = dateutil.parser.parse(self.updated_at) if self.updated_at else None

    def refresh(self):
        data = self.client._get('counterparty/{}'.format(self.id))
        self._update(**data)
        return self

    def save(self):
        if self.id is not None:
            raise exceptions.CounterpartyAlreadyExists(
                'The object\'s ID is set. It has been saved already.')
        if self.profile_type == 'business':
            keyset = ('profile_type', 'name', 'email')
        elif self.profile_type == 'personal':
            keyset = ('profile_type', 'name', 'phone')
        else:
            raise ValueError('Invalid profile type: {}'.format(self.profile_type))
        try:
            data = self.client._post(
                'counterparty',
                data = {k: getattr(self, k) for k in keyset})
        except exceptions.RevolutHttpError as e:
            if e.status_code == 422:
                raise exceptions.CounterpartyAlreadyExists()
            raise
        self._update(**data)
        return self


class CounterpartyAccount(_UpdateFromKwargsMixin):
    id = None
    currency = ''

    def __init__(self, **kwargs):
        self._check_type(kwargs.pop('type'))
        self._update(**kwargs)

    def _check_type(self, typ):
        assert typ == 'revolut'


class CounterpartyExternalAccount(CounterpartyAccount):
    account_no = ''
    iban = ''
    sort_code = ''
    routing_number = ''
    bic = ''
    email = ''
    name = ''
    bank_country = ''
    recipient_charges = ''

    def _check_type(self, typ):
        assert typ == 'external'
