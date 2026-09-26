.. _pyvo-auth:

******************
Auth (`pyvo.auth`)
******************

This module contains submodules which help handle auth when
communicating with virtual observatory services.

OAuth2 Authentication Usage
===========================

Services that are OAuth2 protected can be accessed by
building a :class:`~pyvo.auth.oauth2.oauth2session.VOAuthSession` object and
passing it to a PyVO interface that accepts the usage of a `session` parameter
that it uses for requests. For example, using the device code grant to connect
to an TAP service that requires OAuth2 Authentication:

.. code-block:: python

    from pyvo.auth.oauth2.oauth2session import VOAuthSession
    from pyvo.dal import TAPService

    oauth_client = VOAuthSession(
        grant_types=["urn:ietf:params:oauth:grant-type:device_code"],
    )
    tap_service = TAPService("https://example.com/tap/", session=oauth_client)

    # When tap_service performs a request, stdout will prompt the user
    # to visit a URL and enter their user code to authorise the device
    print("Tables:")
    for table in tap_service.tables.keys():
        print(f" - {table}")

User will be prompted to authenticate using the grant type and print out the
tables:

.. code-block:: console
    Go to: https://example.com/cas/oauth2.0/device
    Enter code: Code-12345678
    Tables:
     - example_schema.sample_table
     - TAP_SCHEMA.schemas
     - TAP_SCHEMA.tables
     - TAP_SCHEMA.columns
     - TAP_SCHEMA.keys
     - TAP_SCHEMA.key_columns

Note that OAuth2 support requires the optional dependencies installed with
``pip install pyvo[oauth2]``.

Reference/API
=============

.. automodapi:: pyvo.auth
    :no-inheritance-diagram:

