# Licensed under a 3-clause BSD style license - see LICENSE.rst
from .sia import search as imagesearch
from .sia2 import search as imagesearch2
from .ssa import search as spectrumsearch
from .sla import search as linesearch
from .scs import search as conesearch
from .tap import search as tablesearch

from .query import DALService, DALQuery, DALResults, Record

from .sia import SIAService, SIAQuery, SIAResults, SIARecord
from .ssa import SSAService, SSAQuery, SSAResults, SSARecord
from .sla import SLAService, SLAQuery, SLAResults, SLARecord
from .scs import SCSService, SCSQuery, SCSResults, SCSRecord
from .tap import TAPService, TAPQuery, TAPResults, AsyncTAPJob


from .exceptions import (
    DALAccessError, DALProtocolError, DALFormatError, DALServiceError,
    DALQueryError)

__all__ = [
    "imagesearch", "spectrumsearch", "linesearch", "conesearch", "tablesearch",
    "DALService", "sia2", "imagesearch2",
    "SIAService", "SSAService", "SLAService", "SCSService", "TAPService",
    "DALQuery",  "SIAQuery", "SSAQuery", "SLAQuery", "SCSQuery", "TAPQuery",
    "DALResults",
    "SIAResults", "SSAResults", "SLAResults", "SCSResults", "TAPResults",
    "Record",
    "SIARecord", "SSARecord", "SLARecord", "SCSRecord",
    "AsyncTAPJob",
    "DALAccessError", "DALProtocolError", "DALFormatError", "DALServiceError",
    "DALQueryError"]
