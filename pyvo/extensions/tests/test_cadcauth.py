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
import pyvo.extensions.cadcauth

def test_cadcauth():
    auth = pyvo.extensions.authsession.AuthSession()
    logging.debug(auth)

    provider = pyvo.extensions.cadcauth.CADCAuth()
    provider.login('user', 'pw')

    auth.creds.add_authenticator('ivo://ivoa.net/sso#cookie', provider)

    service = pyvo.dal.TAPService('https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/tap')
    auth.attach(service)
    logging.debug(auth.auth_urls)

    job = service.search('SELECT * from TAP_SCHEMA.tables')
    logging.debug(job)
