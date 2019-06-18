#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.extensions.authsession
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import logging
import time

import pyvo
import pyvo.extensions.authsession
import pyvo.extensions.lsstauth

def test_authsession():
    auth = pyvo.extensions.authsession.AuthSession()

    provider = pyvo.extensions.lsstauth.LSSTAuth()
    auth.creds.add_authenticator('ivo://ivoa.net/sso#cookie', provider)
    auth.creds.anonymous_provider = provider

    service = pyvo.dal.TAPService("https://lsst-lsp-int.ncsa.illinois.edu/api/tap")
    auth.attach(service)
    logging.debug(auth.auth_urls)

    job = service.search('SELECT * from TAP_SCHEMA.tables')
    logging.debug(job)
