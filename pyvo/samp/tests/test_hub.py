# Licensed under a 3-clause BSD style license - see LICENSE.rst

import os
import time
import sys

import pytest

from pyvo.samp import conf
from pyvo.samp.hub import SAMPHubServer

CI = os.environ.get("CI", "false") == "true"
IS_MACOS = sys.platform == "darwin"


def setup_module(module):
    conf.use_internet = False


@pytest.mark.skipif(IS_MACOS and CI, reason="This test hangs on MacOS GHA.")
def test_SAMPHubServer():
    """Test that SAMPHub can be instantiated"""
    SAMPHubServer(web_profile=False, mode="multiple", pool_size=1)


@pytest.mark.skipif(IS_MACOS and CI, reason="This test hangs on MacOS GHA.")
@pytest.mark.slow
def test_SAMPHubServer_run():
    """Test that SAMPHub can be run"""
    hub = SAMPHubServer(web_profile=False, mode="multiple", pool_size=1)
    hub.start()
    time.sleep(1)
    hub.stop()


@pytest.mark.skipif(IS_MACOS and CI, reason="This test hangs on MacOS GHA.")
@pytest.mark.slow
def test_SAMPHubServer_run_repeated():
    """
    Test that SAMPHub can be restarted after it has been stopped, including
    when web profile support is enabled.
    """

    hub = SAMPHubServer(web_profile=True, mode="multiple", pool_size=1)
    hub.start()
    time.sleep(1)
    hub.stop()
    time.sleep(1)
    hub.start()
    time.sleep(1)
    hub.stop()
