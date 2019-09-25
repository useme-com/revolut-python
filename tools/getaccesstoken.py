#!/usr/bin/python
from __future__ import unicode_literals, print_function
import sys
from revolut.session import TokenProvider

if len(sys.argv) < 4:
    print("Usage: {:s} <auth_code> <client_id> <jwt>".format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)

tp = TokenProvider(*sys.argv[1:])
print("Access token:  {:s}".format(tp.access_token))
print("Expires:       {:s}".format(tp.access_token_expires.strftime("%Y-%m-%d %H:%M:%S")))
print("Refresh token: {:s}".format(tp.refresh_token))
