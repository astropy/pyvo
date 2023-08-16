"""Configure Test Suite.

This file is used to configure the behavior of pytest when using the Astropy
test infrastructure. It needs to live inside the package in order for it to
get picked up when running the tests inside an interpreter using
`pyvo.test()`.

"""

import numpy as np
from astropy.utils import minversion

try:
    from pytest_astropy_header.display import PYTEST_HEADER_MODULES, TESTED_VERSIONS
    ASTROPY_HEADER = True
except ImportError:
    ASTROPY_HEADER = False

# Keep this until we require numpy to be >=2.0
if minversion(np, "2.0.0.dev0+git20230726"):
    np.set_printoptions(legacy="1.25")


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

        PYTEST_HEADER_MODULES.pop('Pandas', None)
        PYTEST_HEADER_MODULES.pop('h5py', None)
        PYTEST_HEADER_MODULES.pop('Scipy', None)
        PYTEST_HEADER_MODULES.pop('Matplotlib', None)

        from . import __version__
        TESTED_VERSIONS['pyvo'] = __version__
