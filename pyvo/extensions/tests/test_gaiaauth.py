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
import pyvo.extensions.gaiaauth

def test_gaiaauth():
    auth = pyvo.extensions.authsession.AuthSession()
    logging.debug(auth)

    provider = pyvo.extensions.gaiaauth.GaiaAuth()
    provider.login('user', 'pw')

    auth.creds.add_authenticator('anonymous', provider)

    service = pyvo.dal.TAPService('http://gea.esac.esa.int/tap-server/tap')
    auth.attach(service)
    logging.debug(auth.auth_urls)

    job = service.search('SELECT * from TAP_SCHEMA.tables')
    logging.debug(job)
