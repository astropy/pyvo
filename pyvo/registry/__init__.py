# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
a package for interacting with registries.

The regtap module supports access to the IVOA Registries
"""
from . import regtap

search = regtap.search
ivoid2service = regtap.ivoid2service

__all__ = ["search"]
