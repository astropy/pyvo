# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This module provides access to astronomical name resolvers available
as web services.  A name resolver service, in its most basic form, is
one that can return a source's position in the sky given a recognized
name.  Such a service may also be able to provide other metadata as
well given a name.  

The default resolver currently defaults to the CDS Sesame resolver which 
includes 3 main functions
   *resolve()*:        given a name return a dictionary-like instance
                         containing data about the astronomical object with 
                         that name.
   *object2pos()*:     given a name return a 2-element tuple containing 
                         the right ascension and declination of the 
                         astronomical object with that name.
   *object2sexapos()*: given a name return a string with 
                         the right ascension and declination given in 
                         sexagesimal format.

All of these can take a list of names as well as input.  See their 
documentation for details.  

More detailed control the Sesame resolver service can be gotten via the 
SesameQuery class; import it from the .nameresolver.sesame module.  
"""
__all__ = [ "resolve", "object2pos", "object2sexapos" ]

from .sesame import resolve, object2pos, object2sexapos

# pull in the docuemtation for the class returned by resolve():
from .sesame import ObjectData
__all__.append("ObjectData")
