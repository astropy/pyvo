#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Example for using client certificate authentication with CADC TAP service
Tests for pyvo.extensions.authsession
"""
import pyvo
from pyvo.auth import authsession

certificate_path = input('Path to client certificate file:')
auth = authsession.AuthSession()
auth.credentials.set_client_certificate(certificate_path)
service = pyvo.dal.TAPService('https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/tap', auth)
job = service.search('SELECT * from TAP_SCHEMA.tables')
print(job)
