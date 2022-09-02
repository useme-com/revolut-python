import warnings

from . import business

__version__ = "0.9.1"


def Client(*args, **kwargs):
    warnings.warn(
        "revolut.Client() is deprecated and will be gone in >0.9.x; please change to revolut.business.BusinessClient() instead",
        DeprecationWarning,
    )
    return business.BusinessClient(*args, **kwargs)


def warn_import(klass):
    def importer(*args, **kwargs):
        warnings.warn(
            f"revolut.{klass.__name__} is deprecated and will be gone in >0.9.x; please import as revolut.business.{klass.__name__} instead",
            DeprecationWarning,
        )
        return klass(*args, **kwargs)

    return importer


Account = warn_import(business.Account)
Counterparty = warn_import(business.Counterparty)
ExternalCounterparty = warn_import(business.ExternalCounterparty)
Transaction = warn_import(business.Transaction)
