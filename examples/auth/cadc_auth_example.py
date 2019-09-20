#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Example for authenticating with CADC TAP service
"""
import getpass

import requests
import pyvo
from pyvo.auth import authsession

# Gather login information
data = {
    'username': input('Username:'),
    'password': getpass.getpass('Password:')
}

headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'text/plain'
}

# Do the login and get the cookie
login_url = 'https://ws-cadc.canfar.net/ac/login'
response = requests.post(login_url, data=data, headers=headers)
response.raise_for_status()
cookie = '\"' + response.text + '\"'

# Configure the session and run the query
auth = authsession.AuthSession()
auth.credentials.set_cookie('CADC_SSO', cookie)
service = pyvo.dal.TAPService('https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/tap', auth)
job = service.search('SELECT * from TAP_SCHEMA.tables')
print(job)
