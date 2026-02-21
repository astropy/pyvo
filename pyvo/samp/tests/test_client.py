# Licensed under a 3-clause BSD style license - see LICENSE.rst

import os
import sys
import pytest

# By default, tests should not use the internet.
from pyvo.samp import SAMPWarning, conf
from pyvo.samp.client import SAMPClient
from pyvo.samp.hub import SAMPHubServer
from pyvo.samp.hub_proxy import SAMPHubProxy
from pyvo.samp.integrated_client import SAMPIntegratedClient

CI = os.environ.get("CI", "false") == "true"
IS_MACOS = sys.platform == "darwin"


def setup_module(module):
    conf.use_internet = False


@pytest.mark.skipif(IS_MACOS and CI, reason="This test hangs on MacOS GHA.")
def test_SAMPHubProxy():
    """Test that SAMPHubProxy can be instantiated"""
    SAMPHubProxy()


@pytest.mark.skipif(IS_MACOS and CI, reason="This test hangs on MacOS GHA.")
@pytest.mark.slow
def test_SAMPClient():
    """Test that SAMPClient can be instantiated"""
    proxy = SAMPHubProxy()
    SAMPClient(proxy)


@pytest.mark.skipif(IS_MACOS and CI, reason="This test hangs on MacOS GHA.")
def test_SAMPIntegratedClient():
    """Test that SAMPIntegratedClient can be instantiated"""
    SAMPIntegratedClient()


@pytest.fixture
def samp_hub():
    """A fixture that can be used by client tests that require a HUB."""
    my_hub = SAMPHubServer()
    my_hub.start()
    yield
    my_hub.stop()


@pytest.mark.skipif(IS_MACOS and CI, reason="This test hangs on MacOS GHA.")
@pytest.mark.filterwarnings("ignore:unclosed <socket:ResourceWarning")
def test_SAMPIntegratedClient_notify_all(samp_hub):
    """Test that SAMP returns a warning if no receiver got the message."""
    client = SAMPIntegratedClient()
    client.connect()
    message = {"samp.mtype": "coverage.load.moc.fits"}
    with pytest.warns(SAMPWarning):
        client.notify_all(message)
    client.disconnect()


@pytest.mark.skipif(IS_MACOS and CI, reason="This test hangs on MacOS GHA.")
def test_reconnect(samp_hub):
    """Test that SAMPIntegratedClient can reconnect.
    This is a regression test for bug [#2673]
    https://github.com/astropy/astropy/issues/2673
    """
    my_client = SAMPIntegratedClient()
    my_client.connect()
    my_client.disconnect()
    my_client.connect()
