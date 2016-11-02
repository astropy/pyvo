# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
a package for interacting with registries.  

The vao module supports the VAO-specific (non-standard) restful interfaces.
The recently added regtap module supports access to the IVOA Registries
"""
import regtap
import vao

search = regtap.search

__all__ = ["search"]
