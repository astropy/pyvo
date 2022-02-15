# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Placeholder for compatibility constructs
"""
from packaging.version import Version
import astropy

__all__ = ['ASTROPY_LT_4_1']

ASTROPY_LT_4_1 = Version(astropy.__version__) < Version('4.1')
