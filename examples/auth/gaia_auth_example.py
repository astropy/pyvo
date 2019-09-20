#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Example for authenticating with Gaia TAP service
"""
import getpass
import requests

import pyvo
from pyvo.auth import securitymethods, authsession

# Gather login information
data = {
    'username': input('Username:'),
    'password': getpass.getpass('Password:')
}

headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'text/plain'
}

# Create a session and do the login.
# The cookie will end up in the cookie jar of the session.
login_url = 'http://gea.esac.esa.int/tap-server/login'
session = requests.Session()
response = session.post(login_url, data=data, headers=headers)
response.raise_for_status()

# Use this session with the auth cookie for all requests to Gaia.
auth = authsession.AuthSession()
auth.credentials.set(securitymethods.ANONYMOUS, session)
service = pyvo.dal.TAPService('http://gea.esac.esa.int/tap-server/tap', auth)
job = service.search('SELECT * from TAP_SCHEMA.tables')
print(job)
