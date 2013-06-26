# Licensed under a 3-clause BSD style license - see LICENSE.rst
from .sia import search as imagesearch
from .ssa import search as spectrumsearch
from .sla import search as linesearch
from .scs import search as conesearch

from .sia import SIAService, SIAQuery, SIARecord
from .ssa import SSAService, SSAQuery, SSARecord
from .sla import SLAService, SLAQuery, SLARecord
from .scs import SCSService, SCSQuery, SCSRecord

from .query import *

__all__ = [ "imagesearch", "spectrumsearch", "linesearch", "consesearch",
            "SIAService", "SSAService", "SLAService", "SCSService",
            "SIAResults", "SSAResults", "SLAResults", "SCSResults",
            "SIARecord",  "SSARecord",  "SLARecord",  "SCSRecord",
            "DALResults" ]

