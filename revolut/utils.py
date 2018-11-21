import datetime
import dateutil.parser
import sys

if sys.version_info < (3,):
    _integer_types = (int, long,)
    _str_types = (str, bytes, unicode)
else:
    _integer_types = (int,)
    _str_types = (str, bytes)


def _obj2id(obj):
    return obj.id if hasattr(obj, 'id') else obj


def _date(v):
    if not isinstance(v, (datetime.date, datetime.datetime)):
        return dateutil.parser.parse(v).date()
    elif isinstance(v, datetime.datetime):
        return v.date()
    return v
