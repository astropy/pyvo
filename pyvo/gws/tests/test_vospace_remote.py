#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.sia2 against remote services
"""

import pytest

from pyvo.gws import VOSpaceService
from pyvo.gws import vospace
from pyvo.auth.authsession import AuthSession


CADC_VAULT_URL = 'https://ws-cadc.canfar.net/vault'
CADC_ARC_URL = 'https://ws-uv.canfar.net/arc'


@pytest.mark.remote_data
class TestVaultCadc():
    # Tests the VOSpace client against the CADC vault service

    def atest_service(self):
        vault = VOSpaceService(baseurl=CADC_VAULT_URL)
        self.check_capabilities(vault.capabilities)

        arc = VOSpaceService(baseurl=CADC_ARC_URL)
        self.check_capabilities(arc.capabilities)

    def test_get_node(self):
        session = AuthSession()
        session.credentials.set_client_certificate('TBO')
        vault = VOSpaceService(baseurl=CADC_VAULT_URL, session=session)
        node1 = vault.find_node('TBD')
        node2 = vault.find_node('TBD')
        assert node1 == node2

    def check_capabilities(self, capabilities):
        assert capabilities
        for cap in capabilities:
            if cap.standardid == vospace.VOS_NODES:
                return
        assert False, 'Nodes end point not found'
