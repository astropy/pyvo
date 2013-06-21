# make sure we have astropy
import astropy.io.votable
from . import registry
from .dal import ssa, sia, sla, scs

from .registry import search as regsearch
from .dal import imagesearch, spectrumsearch, conesearch, linesearch
from .dal import DalAccessError, DalProtocolError, DalFormatError,   \
                 DalServiceError, DalQueryError

from .nameresolver import *

__all__ = [ "imagesearch", "spectrumsearch", "conesearch", "linesearch", 
            "regsearch", "resolve", "object2pos", "object2sexapos" ]
