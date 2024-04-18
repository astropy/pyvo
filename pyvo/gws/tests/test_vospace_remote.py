#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.sia2 against remote services
"""

import pytest
import warnings
import contextlib

from pyvo.gws import VOSpaceService
from pyvo.gws import vospace
from pyvo.auth.authsession import AuthSession

import logging

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger(__name__)


CADC_VAULT_URL = 'https://ws-cadc.canfar.net/vault'
MACH275_VAULT_URL = 'https://mach275.cadc.dao.nrc.ca/clone/vault'

CADC_ARC_URL = 'https://ws-uv.canfar.net/arc'

import requests
from urllib3.exceptions import InsecureRequestWarning

old_merge_environment_settings = requests.Session.merge_environment_settings

@contextlib.contextmanager
def no_ssl_verification():
    opened_adapters = set()

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        # Verification happens only once per connection so we need to close
        # all the opened adapters once we're done. Otherwise, the effects of
        # verify=False persist beyond the end of this context manager.
        opened_adapters.add(self.get_adapter(url))

        settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
        settings['verify'] = False

        return settings

    requests.Session.merge_environment_settings = merge_environment_settings

    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', InsecureRequestWarning)
            yield
    finally:
        requests.Session.merge_environment_settings = old_merge_environment_settings

        for adapter in opened_adapters:
            try:
                adapter.close()
            except:
                pass
@pytest.mark.remote_data
class TestVaultCadc():
    # Tests the VOSpace client against the CADC vault service

    def atest_service(self):
        vault = VOSpaceService(baseurl=CADC_VAULT_URL)
        self.check_capabilities(vault.capabilities)

        arc = VOSpaceService(baseurl=CADC_ARC_URL)
        self.check_capabilities(arc.capabilities)

    def test_get_node(self):
        session = AuthSession(verify=False)
        session.credentials.set_client_certificate('/Users/adriand/.ssl/cadcproxy.pem')

        with ((no_ssl_verification())):
            vault1 =  VOSpaceService(baseurl=CADC_VAULT_URL, session=session)
            node1 = vault1.find_node('adriand')
            vault2 = VOSpaceService(baseurl=MACH275_VAULT_URL, session=session)
            node2 = vault2.find_node('adriand')
            # remove properties in core namespace

            assert node1 == node2

    def check_capabilities(self, capabilities):
        assert capabilities
        for cap in capabilities:
            if cap.standardid == vospace.VOS_NODES:
                return
        assert False, 'Nodes end point not found'
