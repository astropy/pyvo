# Licensed under a 3-clause BSD style license - see LICENSE.rst

# this contains imports plugins that configure py.test for astropy tests.
# by importing them here in conftest.py they are discoverable by py.test
# no matter how it is invoked within the source tree.

try:
    from astropy.tests.pytest_plugins import *
except Exception:  # astropy>=3.2
    pass
