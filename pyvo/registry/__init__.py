# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
a package for interacting with registries.  

The vao module supports the VAO-specific (non-standard) restful interfaces.
Additional modules will be added in the future to access standard interfaces.
"""
from .vao import *
__all__ = [ "search", "RegistryService", "RegistryQuery" ]
