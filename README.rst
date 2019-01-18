Revolut API client for Python
=============================

|travis|_ |coveralls|_

.. |travis| image:: https://travis-ci.com/emesik/revolut-python.svg
.. _travis: https://travis-ci.com/emesik/revolut-python


.. |coveralls| image:: https://coveralls.io/repos/github/emesik/revolut-python/badge.svg
.. _coveralls: https://coveralls.io/github/emesik/revolut-python

A Python wrapper for Revolut API, Python 2.x and 3.x compatible.

Release 0.4, a working beta

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

Copyrights
----------

Released under the BSD 3-Clause License. See `LICENSE.txt`_.

Copyright (c) 2018 Michał Sałaban <michal@salaban.info>

.. _`LICENSE.txt`: LICENSE.txt
