# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Placeholder for compatibility constructs
"""
from distutils.version import LooseVersion
import astropy

__all__ = ['ASTROPY_LT_4_1']

ASTROPY_LT_4_1 = LooseVersion(astropy.__version__) < '4.1'
