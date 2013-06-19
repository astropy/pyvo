from .sia import search as imagesearch
from .ssa import search as spectrumsearch
from .sla import search as linesearch
from .    import conesearch as scs
from .conesearch import search as conesearch
# from .scs import search as conesearch

from .sia import SIAService, SIAQuery, SIARecord
from .ssa import SSAService, SSAQuery, SSARecord
from .sla import SLAService, SLAQuery, SLARecord
from .conesearch import SCSService, SCSQuery, SCSRecord
# from .scs import SCSService, SCSQuery, SCSRecord

from .query import *

__all__ = [ "imagesearch", "spectrumsearch", "linesearch", "consesearch",
            "SIARecord", "SSARecord", "SLARecord", "SCSRecord",
            "DalResults" ]

