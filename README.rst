Revolut API client for Python
=============================

|travis|_ |coveralls|_

.. |travis| image:: https://travis-ci.com/emesik/revolut-python.svg
.. _travis: https://travis-ci.com/emesik/revolut-python


.. |coveralls| image:: https://coveralls.io/repos/github/emesik/revolut-python/badge.svg
.. _coveralls: https://coveralls.io/github/emesik/revolut-python

A Python wrapper for Revolut API, Python 2.x and 3.x compatible.

Release 0.8, a working beta

What is supported?
------------------

As listed in `Revolut docs`_:

.. _`Revolut docs`: https://revolutdev.github.io/business-api/

+------------------------------------+
| **Accounts**                       |
+------------------------------+-----+
| Get Accounts                 | yes |
+------------------------------+-----+
| Get Account                  | yes |
+------------------------------+-----+
| Get Account Details          | yes |
+------------------------------+-----+
| **Counterparties**                 |
+------------------------------+-----+
| Add Revolut Counterparty     | yes |
+------------------------------+-----+
| Add non-Revolut Counterparty | yes |
+------------------------------+-----+
| Delete Counterparty          | yes |
+------------------------------+-----+
| Get Counterparty             | yes |
+------------------------------+-----+
| Get Counterparties           | yes |
+------------------------------+-----+
| **Payments**                       |
+------------------------------+-----+
| Transfer                     | yes |
+------------------------------+-----+
| Create Payment               | yes |
+------------------------------+-----+
| Schedule Payment             | no  |
+------------------------------+-----+
| Check Payment Status         | yes |
+------------------------------+-----+
| Cancel Payment               | no  |
+------------------------------+-----+
| Get Transactions             | yes |
+------------------------------+-----+

Authorization
-------------

In September 2019 Revolut introduced much more complex authorization system based on OAuth2.
Since version 0.6 this module supports only the new authorization model and old access keys
become obsolete.

The flow
~~~~~~~~

This description should help you get through the auth mess. It assumes you want to run the module
in a non-interactive way (e.g. as a backend for a web service). Mobile applications will require
some additional research on your side.

    1. Make sure you have OpenSSL installed.
    2. Run `$ revolut_genkey.sh` to generate key pair. Answer questions about your organization.
    3. Two files will be generated: `prvkey.pem` and `pubkey.pem`. Store them in a safe place.
       The script will also print the contents of `pubkey.pem` to the console. This is your
       *X509 public key*.
    4. In Revolut panel go to *Settings / API* and click *Set up API access*.
    5. Paste the public key into the form field.
    6. If you don't know what *OAuth redirect URI* means and why you need it, enter some
       bullshit URL there. It'd be better, however, if it pointed to your domain. Submit the form.
    7. You'll land back in API settings, this time you will be presented with `client_id` and `iss`
       values needed in further steps.
    8. Click *Enable API access to your account*, continue with *Authorize*.
    9. Confirm with SMS code.
    10. After a couple of seconds you'll be redirected to the URL you have provided as *OAuth
        redirect*. Check the address bar. It will contain a *code* parameter. This is your
        `auth_code`.
    11. Run `$ revolut_getjwt.py prvkey.pem <iss> <client_id>`. The output will be your `jwt`.
    12. Run `$ revolut_gettokens.py <auth_code> <client_id> <jwt>`. The script will return
        `access_token` (with expiration time) and `refresh_token`.
        (If you do it too slowly, the auth code expires and you get "unauthorized_client" error.
        Return to step 8.)

Now you're almost done, with some pieces of data on your hand. There are two ways to continue:

    1. Create `revolut.session.TemporarySession` with the `access_token` and use it until the token
       expires.
    2. Create `revolut.session.RenewableSession` with `refresh_token`, `client_id` and `jwt`. It
       will be more durable, creating fresh `access_token` each time.

However, it seems that **after 90 days your API access expires anyway** and you'd have to click
*Refresh access* in the panel and restart the above process from point 8. Or whatever the EU
shitheads invented in PSD2.


Copyrights
----------

Released under the BSD 3-Clause License. See `LICENSE.txt`_.

Copyright (c) 2018 Michał Sałaban <michal@salaban.info>

.. _`LICENSE.txt`: LICENSE.txt
