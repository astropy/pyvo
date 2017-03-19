# Licensed under a 3-clause BSD style license - see LICENSE.rst
from .sia import search as imagesearch
from .ssa import search as spectrumsearch
from .sla import search as linesearch
from .scs import search as conesearch
from .tap import search as tablesearch

from .sia import SIAService, SIAQuery, SIARecord
from .ssa import SSAService, SSAQuery, SSARecord
from .sla import SLAService, SLAQuery, SLARecord
from .scs import SCSService, SCSQuery, SCSRecord
from .tap import TAPService, TAPQuery, AsyncTAPJob

from .query import (
    DALAccessError, DALProtocolError, DALFormatError, DALServiceError,
    DALQueryError)

__all__ = [
    "imagesearch", "spectrumsearch", "linesearch", "conesearch", "tablesearch",
    "SIAService", "SSAService", "SLAService", "SCSService",
    "TAPService", "AsyncTAPJob"]
