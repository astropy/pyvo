"""
PyVO is a package providing access to remote data and services of the 
Virtual observatory (VO) using Python.  
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
