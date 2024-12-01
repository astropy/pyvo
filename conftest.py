# Licensed under a 3-clause BSD style license - see LICENSE.rst

# This file is the main file used when running tests with pytest directly,
# in particular if running e.g. ``pytest docs/``.

import os
import tempfile
import numpy as np
from astropy.utils import minversion

try:
    from pytest_astropy_header.display import PYTEST_HEADER_MODULES, TESTED_VERSIONS
    ASTROPY_HEADER = True
except ImportError:
    ASTROPY_HEADER = False

# Make sure we use temporary directories for the config and cache
# so that the tests are insensitive to local configuration.

os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp('astropy_config')
os.environ['XDG_CACHE_HOME'] = tempfile.mkdtemp('astropy_cache')

os.mkdir(os.path.join(os.environ['XDG_CONFIG_HOME'], 'astropy'))
os.mkdir(os.path.join(os.environ['XDG_CACHE_HOME'], 'astropy'))

# Note that we don't need to change the environment variables back or remove
# them after testing, because they are only changed for the duration of the
# Python process, and this configuration only matters if running pytest
# directly, not from e.g. an IPython session.

try:
    from pyvo import __version__ as version
except ImportError:
    version = 'unknown'


# Disable IERS auto download for testing (to support the local, non-remote-data scenario),
# revisit this config when minimum supported astropy is 5.1.
from astropy.utils.iers import conf as iers_conf
iers_conf.auto_download = False


def pytest_configure(config):
    """Configure Pytest with Astropy.

    Parameters
    ----------
    config : pytest configuration

    """
    if ASTROPY_HEADER:

        config.option.astropy_header = True

        # Customize the following lines to add/remove entries from the list of
        # packages for which version numbers are displayed when running the tests.
        PYTEST_HEADER_MODULES['Astropy'] = 'astropy'  # noqa
        PYTEST_HEADER_MODULES['requests'] = 'requests'  # noqa
        PYTEST_HEADER_MODULES['defusedxml'] = 'defusedxml'

        PYTEST_HEADER_MODULES.pop('Pandas', None)
        PYTEST_HEADER_MODULES.pop('h5py', None)
        PYTEST_HEADER_MODULES.pop('Scipy', None)
        PYTEST_HEADER_MODULES.pop('Matplotlib', None)

        TESTED_VERSIONS['pyvo'] = version
