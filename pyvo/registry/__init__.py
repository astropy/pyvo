# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
a package for interacting with registries.

The regtap module supports access to the IVOA Registries
"""
from .regtap import search, ivoid2service, get_RegTAP_query

from .rtcons import (Constraint,
    Freetext, Author, Servicetype, Waveband, Datamodel, Ivoid,
    UCD, Spatial, Spectral, Temporal)

__all__ = ["search", "get_RegTAP_query", "Freetext", "Author",
    "Servicetype", "Waveband", "Datamodel", "Ivoid", "UCD",
    "Spatial", "Spectral", "Temporal"]
