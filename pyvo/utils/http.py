# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
HTTP utils
"""
import requests
from ..version import version


def requests_session(useragent=None):
    if not useragent:
        useragent = 'python-pyvo/{}'.format(version)

    session = requests.Session()
    session.headers['User-Agent'] = useragent

    return session


session = requests_session()
