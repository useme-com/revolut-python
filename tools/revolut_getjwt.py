#!/usr/bin/python
import sys
from revolut.utils import get_jwt

if len(sys.argv) < 4:
    print(
        "Usage: {:s} <prvkey.pem> <issuer> <client_id>".format(sys.argv[0]),
        file=sys.stderr,
    )
    sys.exit(1)

prvkey = open(sys.argv[1], "rb").read()
print(get_jwt(prvkey, *sys.argv[2:]).decode())
