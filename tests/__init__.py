import inspect
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class JSONResponsesMixin(object):
    def _read(self, name):
        caller_name = inspect.getouterframes(inspect.currentframe(), 2)[1][3]
        with open(os.path.join(DATA_DIR, caller_name, name), "r") as fh:
            return json.loads(fh.read())
