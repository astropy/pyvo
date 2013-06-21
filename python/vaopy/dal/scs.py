"""
A module for searching remote source and observation catalogs

A Simple Cone Search (SCS) service allows a client to search for
records in a source or observation catalog whose positions are within
some minimum distance of a search position (i.e. within a specified
"cone" on the sky).  This module provides an interface for accessing
such services.  It is implemented as a specialization of the DAL Query
interface.

The ``search()`` function provides a simple interface to a service, 
returning an SCSResults instance as its results which represents the
matching records from the catalog.  The SCSResults supports access to
and iterations over the individual records; these are provided as
SCSRecord instances, which give easy access to key metadata in the
response, including the ICRS position of the matched source or
observation.  

This module also features the SCSQuery class that provides an
interface for building up and remembering a query.  The SCSService
class can represent a specific service available at a URL endpoint.
"""

import numbers
from . import query
from .query import DALQueryError

__all__ = [ "search", "SCSResults", "SCSRecord", "SCSQuery", "SCSService" ]

def search(url, pos, radius=1.0, verbosity=2):
    """
    submit a simple Cone Search query that requests objects or observations
    whose positions fall within some distance from a search position.  

    :Args:
       *url*        the base URL of the query service.
       *pos*:       a 2-element tuple containing the ICRS right ascension 
                       and declination defining the position of the center 
                       of the circular search region, in decimal degrees
       *radius*:    the radius of the circular search region, in decimal 
                       degrees
       *verbosity*  an integer value that indicates the volume of columns
                       to return in the result table.  0 means the minimum
                       set of columsn, 3 means as many columns as are 
                       available. 
    """
    service = SCSService(url)
    return service.search(pos, radius, verbosity)

class SCSService(query.DALService):
    """
    a representation of a Cone Search service
    """

    def __init__(self, baseurl, resmeta=None, version="1.0"):
        """
        instantiate a Cone Search service

        :Args:
           *baseurl*:  the base URL for submitting search queries to the 
                         service.
           *resmeta*:  an optional dictionary of properties about the 
                         service
        """
        query.DALService.__init__(self, baseurl, "scs", version, resmeta)

    def search(self, pos, radius=1.0, verbosity=2):
        """
        submit a simple Cone Search query that requests objects or observations
        whose positions fall within some distance from a search position.  

        :Args:
           *pos*:       a 2-element tuple containing the ICRS right ascension 
                           and declination defining the position of the center 
                           of the circular search region, in decimal degrees
           *radius*:    the radius of the circular search region, in decimal 
                           degrees
           *verbosity*  an integer value that indicates the volume of columns
                           to return in the result table.  0 means the minimum
                           set of columsn, 3 means as many columns as are 
                           available. 
        """
        q = self.create_query(pos, radius, verbosity)
        return q.execute()

    def create_query(self, pos=None, radius=None, verbosity=None):
        """
        create a query object that constraints can be added to and then 
        executed.  The input arguments will initialize the query with the 
        given values.

        :Args:
           *pos*:       a 2-element tuple containing the ICRS right ascension 
                           and declination defining the position of the center 
                           of the circular search region, in decimal degrees
           *radius*:    the radius of the circular search region, in decimal 
                           degrees
           *verbosity*  an integer value that indicates the volume of columns
                           to return in the result table.  0 means the minimum
                           set of columsn, 3 means as many columns as are 
                           available. 
        """
        if pos is not None and not isinstance(pos, tuple) and \
           not isinstance(pos, list):
            raise TypeError("create_query(): pos is not a tuple or list")

        q = SCSQuery(self._baseurl)
        if pos    is not None:  q.pos = pos
        if radius is not None:  q.sr  = radius
        if verbosity is not None: q.verbosity = verbosity
        return q

class SCSQuery(query.DALQuery):
    """
    a class for preparing an query to a Cone Search service.  Query constraints
    are added via its service type-specific methods.  The various execute()
    functions will submit the query and return the results.  

    The base URL for the query can be changed via the baseurl property.
    """

    def __init__(self, baseurl, version="1.0"):
        """
        initialize the query object with a baseurl
        """
        query.DALQuery.__init__(self, baseurl, "scs", version)
        

    @property
    def ra(self):
        """
        the right ascension part of the position constraint (default: None).
        """
        return self.getparam("RA")
    @ra.setter
    def ra(self, val):
        if val is not None:
            if not isinstance(val, numbers.Number):
                raise ValueError("ra constraint is not a number")
            while val < 0:
                val = val + 360.0
            while val >= 360.0:
                val = val - 360.0

        self.setparam("RA", val)
    @ra.deleter
    def ra(self):
        self.unsetparam("RA")

    @property
    def dec(self):
        """
        the declination part of the position constraint (default: None).
        """
        return self.getparam("DEC")
    @dec.setter
    def dec(self, val):
        if val is not None:
            if not isinstance(val, numbers.Number):
                raise ValueError("ra constraint is not a number")
            if val < -90.0 or val > 90.0:
                raise ValueError("dec constraint out-of-range: " + str(val))

        self.setparam("DEC", val)
    @dec.deleter
    def dec(self):
        self.unsetparam("DEC")

    @property
    def pos(self):
        return (self.ra, self.dec)
    @pos.setter
    def pos(self, pair):
        if pair is not None and not isinstance(pair, tuple) and \
           not isinstance(pair, list):
            raise TypeError("create_query(): pos is not a tuple or list")
        if len(pair) < 2:
            raise ValueError("create_query(): pos has fewer than 2 elements")
        self.ra = pair[0]
        self.dec = pair[1]
    @pos.deleter
    def pos(self, pair):
        del self.ra
        del self.dec

    @property
    def radius(self):
        """
        the radius of the circular (cone) search region.
        """
        return self.getparam("SR")
    @radius.setter
    def radius(self, val):
        if val is not None:
            if not isinstance(val, numbers.Number):
                raise ValueError("ra constraint is not a number")
            if val <= 0.0 or val > 180.0:
                raise ValueError("sr constraint out-of-range: " + val)

        self.setparam("SR", val)
    @radius.deleter
    def radius(self):
        self.unsetparam("SR")

    @property
    def sr(self):
        """
        a synonym for radius
        """
        return self.radius
    @sr.setter
    def sr(self, val):
        self.radius = val
    @sr.deleter
    def sr(self):
        del self.radius

    @property
    def verbosity(self):
        return self.getparam("VERB")
    @verbosity.setter
    def verbosity(self, val):
        # do a check on val
        if not isinstance(val, int):
            raise ValueError("verbosity value not an integer: " + val)
        self.setparam("VERB", val)
    @verbosity.deleter
    def verbosity(self):
        self.unsetparam("VERB")

    def execute(self):
        """
        submit the query and return the results as a Results subclass instance.
        This implimentation returns an SCSResults instance

        :Raises:
           *DALServiceError*: for errors connecting to or 
                              communicating with the service
           *DALQueryError*:   if the service responds with 
                              an error, including a query syntax error.  
        """
        return SCSResults(self.execute_votable(), self.getqueryurl(True))

    def execute_votable(self):
        """
        submit the query and return the results as an AstroPy votable instance

        :Raises:
           *DALServiceError*: for errors connecting to or 
                              communicating with the service
           *DALFormatError*:  for errors parsing the VOTable response
           *DALQueryError*:   for errors in the input query syntax
        """
        try: 
            from astropy.io.votable.exceptions import W22
        except ImportError, ex:
            raise RuntimeError("astropy votable not available")

        try:
            return query._votableparse(self.execute_stream().read)
        except query.DALAccessError:
            raise
        except W22, e:
            raise query.DALFormatError("Unextractable Error encoded in " +
                                       "deprecated DEFINITIONS element")
        except Exception, e:
            raise query.DALFormatError(e, self.getqueryurl())

    def getqueryurl(self, lax=False):
        """
        return the GET URL that encodes the current query.  This is the 
        URL that the execute functions will use if called next.  

        :Args:
           *lax*:  if False (default), a DALQueryError exception will be 
                      raised if any required parameters (RA, DEC, or SR)
                      are missing.  If True, no syntax checking will be 
                      done.  
        """
        out = query.DALQuery.getqueryurl(self)
        if not lax:
            if self.ra is None:
                raise DALQueryError("Query is missing an RA parameter", url=out)
            if self.dec is None:
                raise DALQueryError("Query is missing a DEC parameter", url=out)
            if self.sr is None:
                raise DALQueryError("Query is missing an SR parameter", url=out)
        return out

class SCSResults(query.DALResults):
    """
    Results from a Cone Search query.  It provides random access to records in 
    the response.  Alternatively, it can provide results via a Cursor 
    (compliant with the Python Database API) or an iterable.
    """

    def __init__(self, votable, url=None, version="1.0"):
        """
        initialize the cursor.  This constructor is not typically called 
        by directly applications; rather an instance is obtained from calling 
        a SCSQuery's execute().
        """
        query.DALResults.__init__(self, votable, url, "scs", version)
        self._scscols = {
            "ID_MAIN":         self.fieldname_with_ucd("ID_MAIN"),
            "POS_EQ_RA_MAIN":  self.fieldname_with_ucd("POS_EQ_RA_MAIN"),
            "POS_EQ_DEC_MAIN": self.fieldname_with_ucd("POS_EQ_DEC_MAIN")
            }
        self._recnames = { "id":  self._scscols["ID_MAIN"],
                           "ra":  self._scscols["POS_EQ_RA_MAIN"],
                           "dec": self._scscols["POS_EQ_DEC_MAIN"]
                           }

    def _findresultsresource(self, votable):
        if len(votable.resources) < 1:
            return None
        return votable.resources[0]

    def _findstatus(self, votable):
        # this is specialized according to the Conesearch standard

        # look first in the preferred location: just below the root VOTABLE
        info = self._findstatusinfo(votable.infos)
        if info:
            return (info.name, info.value)

        
        # look next in the result resource
        res = self._findresultsresource(votable)
        if res:
            # look for RESOURCE/INFO
            info = self._findstatusinfo(res.infos)
            if info:
                return (info.name, info.value)

            # if not there, check for a PARAM
            info = self._findstatusinfo(res.params)
            if info:
                return (info.name, info.value)

        # last resort:  VOTABLE/DEFINITIONS/PARAM
        # NOT SUPPORTED BY astropy; parser has been configured to 
        # raise W22 as exception instead.

        # assume it's okay
        return ("OK", "Successful Response")

    def _findstatusinfo(self, infos):
        # this can be overridden to specialize for a particular DAL protocol
        for info in infos:
            if info.name == "Error":
                return info
                
        

    def getrecord(self, index):
        """
        return a Cone Search result record that follows dictionary
        semantics.  The keys of the dictionary are those returned by this
        instance's fieldNames() function: either the column IDs or name, if 
        the ID is not set.  The returned record has additional accessor 
        methods for getting at stardard Cone Search response metadata (e.g. 
        ra, dec).
        """
        return SCSRecord(self, index)

class SCSRecord(query.Record):
    """
    a dictionary-like container for data in a record from the results of an
    Cone Search query, describing an available image.
    """

    def __init__(self, results, index):
        query.Record.__init__(self, results, index)
        self._ucdcols = results._scscols
        self._names = results._recnames

    @property
    def ra(self):
        """
        return the right ascension of the object or observation described by
        this record.
        """
        return self.get(self._names["ra"])

    @property
    def dec(self):
        """
        return the declination of the object or observation described by
        this record.
        """
        return self.get(self._names["dec"])

    @property
    def id(self):
        """
        return the identifying name of the object or observation described by
        this record.
        """
        return self.get(self._names["id"])



