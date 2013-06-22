"""
PyVO is a package providing access to remote data and services of the 
Virtual observatory (VO) using Python.  

The pyvo module currently provides these main capabilities:
* find archives that provide particular data of a particular type and/or 
  relates to a particular topic
  *  regsearch()
* search an archive for datasets of a particular type
  *  imagesearch(), spectrumsearch()
* do simple searches on catalogs or databases
  *  conesearch(), linesearch()
* get information about an object via its name
  *  resolve(), object2pos(), object2sexapos()

Submodules provide additional functions and classes for greater control over
access to these services.

This module also exposes the exception classes raised by the above functions, 
of which DALAccessError is the root parent exception. 
"""
# make sure we have astropy
import astropy.io.votable
from . import registry
from .dal import ssa, sia, sla, scs

from .registry import search as regsearch
from .dal import imagesearch, spectrumsearch, conesearch, linesearch
from .dal import DALAccessError, DALProtocolError, DALFormatError,   \
                 DALServiceError, DALQueryError

from .nameresolver import *

__all__ = [ "imagesearch", "spectrumsearch", "conesearch", "linesearch", 
            "regsearch", "resolve", "object2pos", "object2sexapos" ]
