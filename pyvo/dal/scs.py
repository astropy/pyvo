# Licensed under a 3-clause BSD style license - see LICENSE.rst
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
from __future__ import print_function, division

import numbers
from . import query
from .query import DALQueryError

__all__ = [ "search", "SCSService", "SCSQuery", "SCSResults", "SCSRecord" ]

def search(url, pos, radius=1.0, verbosity=2):
    """
    submit a simple Cone Search query that requests objects or observations
    whose positions fall within some distance from a search position.  

    Parameters
    ----------
    url : str
        the base URL of the query service.
    pos : 2-element tuple of floats
        a 2-element tuple containing the ICRS right ascension 
        and declination defining the position of the center 
        of the circular search region, in decimal degrees
    radius : float
        the radius of the circular search region, in decimal 
        degrees
    verbosity : int
        an integer value that indicates the volume of columns
        to return in the result table.  0 means the minimum
        set of columsn, and 3 means as many columns as are 
        available. 

    Returns
    -------
    SCSResults
        a container holding a table of matching catalog records 

    Raises
    ------
    DALServiceError
       for errors connecting to or 
       communicating with the service
    DALQueryError
       if the service responds with 
       an error, including a query syntax error.  

    See Also
    --------
    SCSResults
    pyvo.dal.query.DALServiceError
    pyvo.dal.query.DALQueryError
    """
    service = SCSService(url)
    return service.search(pos, radius, verbosity)

class SCSRecord(query.Record):
    """
    a dictionary-like container for data in a record from the results of an
    Cone Search (SCS) query, describing a matching source or observation.

    The commonly accessed metadata which are stadardized by the SCS
    protocol are available as attributes.  All metadata, particularly
    non-standard metadata, are acessible via the ``get(`` *key* ``)`` 
    function (or the [*key*] operator) where *key* is table column name.  
    """

    def __init__(self, results, index):
        super(SCSRecord, self).__init__(results, index)
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


class SCSResults(query.DALResults):
    """
    The list of matching catalog records resulting from a catalog (SCS) query.  
    Each record contains a set of metadata that describes a source or
    observation within the requested circular region (i.e. a "cone").  The 
    number of records in the results is available via the :py:attr:`nrecs` 
    attribute or by passing it to the Python built-in ``len()`` function.  

    This class supports iterable semantics; thus, 
    individual records (in the form of 
    :py:class:`~pyvo.dal.scs.SCSRecord` instances) are typically
    accessed by iterating over an ``SCSResults`` instance.  

    >>> results = pyvo.conesearch(url, pos=[12.24, -13.1], radius=0.1)
    >>> for src in results:
    ...     print("{0}: {1} {2}".format(src.id, src.ra, src.dec))

    Alternatively, records can be accessed randomly via 
    :py:meth:`getrecord` or through a Python Database API (v2)
    Cursor (via :py:meth:`~pyvo.dal.query.DALResults.cursor`).  
    Column-based data access is possible via the 
    :py:meth:`~pyvo.dal.query.DALResults.getcolumn` method.  

    ``SCSResults`` is essentially a wrapper around an Astropy 
    :py:mod:`~astropy.io.votable` 
    :py:class:`~astropy.io.votable.tree.Table` instance where the 
    columns contain the various metadata describing the images.  
    One can access that VOTable directly via the 
    :py:attr:`~pyvo.dal.query.DALResults.votable` attribute.  Thus,
    when one retrieves a whole column via 
    :py:meth:`~pyvo.dal.query.DALResults.getcolumn`, the result is 
    a Numpy array.  Alternatively, one can manipulate the results 
    as an Astropy :py:class:`~astropy.table.table.Table` via the 
    following conversion:

    >>> table = results.votable.to_table()

    ``SCSResults`` supports the array item operator ``[...]`` in a 
    read-only context.  When the argument is numerical, the result 
    is an 
    :py:class:`~pyvo.dal.scs.SCSRecord` instance, representing the 
    record at the position given by the numerical index.  If the 
    argument is a string, it is interpreted as the name of a column,
    and the data from the column matching that name is returned as 
    a Numpy array.  
    """

    RECORD_CLASS = SCSRecord

    def __init__(self, votable, url=None, version="1.0"):
        """
        initialize the cursor.  This constructor is not typically called 
        by directly applications; rather an instance is obtained from calling 
        a SCSQuery's execute().
        """
        super(SCSResults, self).__init__(votable, url, "scs", version)
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


class SCSQuery(query.DALQuery):
    """
    a class for preparing an query to a Cone Search service.  Query constraints
    are added via its service type-specific methods.  The various execute()
    functions will submit the query and return the results.  

    The base URL for the query, which controls where the query will be sent 
    when one of the execute functions is called, is typically set at 
    construction time; however, it can be updated later via the 
    :py:attr:`~pyvo.dal.query.DALQuery.baseurl` to send a configured 
    query to another service.  

    In addition to the search constraint attributes described below, search 
    parameters can be set generically by name via dict semantics.
    The class attribute, ``std_parameters``, list the parameters 
    defined by the SCS standard.  

    The typical function for submitting the query is ``execute()``; however, 
    alternate execute functions provide the response in different forms, 
    allowing the caller to take greater control of the result processing.  
    """
    RESULTS_CLASS = SCSResults

    std_parameters = [ "RA", "DEC", "SR" ]

    def __init__(self, baseurl, version="1.0"):
        """
        initialize the query object with a baseurl
        """
        super(SCSQuery, self).__init__(baseurl, "scs", version)
        

    @property
    def ra(self):
        """
        the right ascension part of the position constraint (default: None).
        """
        return self.get("RA")
    @ra.setter
    def ra(self, val):
        if val is not None:
            if not isinstance(val, numbers.Number):
                raise ValueError("ra constraint is not a number")
            while val < 0:
                val = val + 360.0
            while val >= 360.0:
                val = val - 360.0

        self["RA"] = val
    @ra.deleter
    def ra(self):
        del self["RA"]

    @property
    def dec(self):
        """
        the declination part of the position constraint (default: None).
        """
        return self.get("DEC")
    @dec.setter
    def dec(self, val):
        if val is not None:
            if not isinstance(val, numbers.Number):
                raise ValueError("dec constraint is not a number")
            if val < -90.0 or val > 90.0:
                raise ValueError("dec constraint out-of-range: " + str(val))

        self["DEC"] = val
    @dec.deleter
    def dec(self):
        del self["DEC"]

    @property
    def pos(self):
        """
        the position (POS) constraint as a 2-element tuple denoting RA and dec
        in decimal degrees.  This defaults to None.
        """
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
        return self.get("SR")
    @radius.setter
    def radius(self, val):
        if val is not None:
            if not isinstance(val, numbers.Number):
                raise ValueError("ra constraint is not a number")
            if val <= 0.0 or val > 180.0:
                raise ValueError("sr constraint out-of-range: " + val)

        self["SR"] = val
    @radius.deleter
    def radius(self):
        del self["SR"]

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
        """
        a parameter for controling the volume of columns returned.
        The value of 0 means the minimum set of columsn, 3 means as
        many columns as are available. 
        """
        return self.get("VERB")
    @verbosity.setter
    def verbosity(self, val):
        # do a check on val
        if not isinstance(val, int):
            raise ValueError("verbosity value not an integer: " + val)
        self["VERB"] = val
    @verbosity.deleter
    def verbosity(self):
        del self["VERB"]

    def execute_votable(self):
        """
        submit the query and return the results as an AstroPy votable instance

        Raises
        ------
        DALServiceError  
           for errors connecting to or communicating with the service
        DALFormatError  
           for errors parsing the VOTable response
        DALQueryError  
           for errors in the input query syntax
        """
        try: 
            from astropy.io.votable.exceptions import W22
        except ImportError:
            raise RuntimeError("astropy votable not available")

        try:
            return query._votableparse(self.execute_stream().read)
        except query.DALAccessError:
            raise
        except W22 as e:
            raise query.DALFormatError("Unextractable Error encoded in " +
                                       "deprecated DEFINITIONS element")
        except Exception as e:
            raise query.DALFormatError(e, self.getqueryurl())


class SCSService(query.DALService):
    """
    a representation of a Cone Search service
    """

    QUERY_CLASS = SCSQuery

    def __init__(self, baseurl, resmeta=None, version="1.0"):
        """
        instantiate a Cone Search service

        Parameters
        ----------
        baseurl : str
           the base URL for submitting search queries to the 
           service.
        resmeta : dict
           an optional dictionary of properties about the service
        """
        super(SCSService, self).__init__(baseurl, "scs", version, resmeta)

    def search(self, pos, radius=1.0, verbosity=2):
        """
        submit a simple Cone Search query that requests objects or observations
        whose positions fall within some distance from a search position.  

        Parameters
        ----------
        pos : 2-element tuple/list of floats
           a 2-element tuple or list containing the ICRS right ascension 
           and declination defining the position of the center 
           of the circular search region, in decimal degrees
        radius : float
           the radius of the circular search region, in decimal degrees
        verbosity : int
           an integer value that indicates the volume of columns
           to return in the result table.  0 means the minimum
           set of columsn, 3 means as many columns as are 
           available. 

        Returns
        -------
        SCSResults
            a container holding a table of matching catalog records 

        Raises
        ------
        DALServiceError
           for errors connecting to or 
           communicating with the service
        DALQueryError
           if the service responds with 
           an error, including a query syntax error.  

        See Also
        --------
        SCSResults
        pyvo.dal.query.DALServiceError
        pyvo.dal.query.DALQueryError
        """
        q = self.create_query(pos, radius, verbosity)
        return q.execute()

    def create_query(self, pos=None, radius=None, verbosity=None):
        """
        create a query object that constraints can be added to and then 
        executed.  The input arguments will initialize the query with the 
        given values.

        Parameters
        ----------
        pos : 2-element tuple/list of floats
           a 2-element tuple or list containing the ICRS right ascension 
           and declination defining the position of the center 
           of the circular search region, in decimal degrees
        radius : float
           the radius of the circular search region, in decimal degrees
        verbosity : int
           an integer value that indicates the volume of columns
           to return in the result table.  0 means the minimum
           set of columsn, 3 means as many columns as are 
           available. 

        Returns
        -------
        SCSQuery
           the query instance

        See Also
        --------
        SCSQuery
        """
        if pos is not None and not isinstance(pos, tuple) and \
           not isinstance(pos, list):
            raise TypeError("create_query(): pos is not a tuple or list")

        q = self.QUERY_CLASS(self._baseurl)
        if pos    is not None:  q.pos = pos
        if radius is not None:  q.sr  = radius
        if verbosity is not None: q.verbosity = verbosity
        return q
