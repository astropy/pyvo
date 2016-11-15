# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
A module for searching for spectral line metadata in a remote database.

A Simple Line Access (SLA) service allows a client to search for
metadata describing atomic and molecular transitions that can result
in spectral line emission and absorption.  The service responds to a
search query with a table in which each row represents a transition
that matches the query constraints.  The columns provide the metadata
describing the transition.  This module provides an interface for
accessing an SLA service.  It is implemented as a specialization of
the DAL Query interface.

The ``search()`` function support the simplest and most common types
of queries, returning an SLAResults instance as its results which
represents the matching imagess from the archive.  The SLAResults
supports access to and iterations over the individual records; these
are provided as SLARecord instances, which give easy access to key
metadata in the response, such as the transition title.  

For more complex queries, the SLAQuery class can be helpful which 
allows one to build up, tweak, and reuse a query.  The SLAService
class can represent a specific service available at a URL endpoint.
"""
from __future__ import print_function, division

import re
from . import query

__all__ = [ "search", "SLAService", "SLAQuery", "SLAResults", "SLARecord" ]

def search(url, wavelength, **keywords):
    """
    submit a simple SLA query that requests spectral lines within a 
    wavelength range

    Parameters
    ----------
    url : str
       the base URL for the SLA service
    wavelength : 2 element sequence of floats
       a 2-element sequence giving the wavelength spectral range to search 
       in meters
    **keywords 
       additional parameters can be given via arbitrary 
       keyword arguments.  These can be either standard 
       parameters (with names drown from the 
       ``SSAQuery.std_parameters`` list) or paramters
       custom to the service.  Where there is overlap 
       with the parameters set by the other arguments to
       this function, these keywords will override.

    Returns
    -------
    SLAResults
        a container holding a table of matching spectral lines

    Raises
    ------
    DALServiceError
       for errors connecting to or communicating with the service
    DALQueryError
       if the service responds with an error, including a query syntax error.
    """
    service = SLAService(url)
    return service.search(wavelength, **keywords)


class SLARecord(query.Record):
    """
    a dictionary-like container for data in a record from the results of an
    spectral line (SLA) query, describing a spectral line transition.

    The commonly accessed metadata which are stadardized by the SCS
    protocol are available as attributes.  All metadata, particularly
    non-standard metadata, are acessible via the ``get(`` *key* ``)`` 
    function (or the [*key*] operator) where *key* is table column name.  
    """

    def __init__(self, results, index):
        super(SLARecord, self).__init__(results, index)
        self._utypecols = results._slacols
        self._names = results._recnames

    @property
    def title(self):
        """
        a title/small description of the line transition
        """
        return self.get(self._names["title"])

    @property
    def wavelength(self):
        """
        the vacuum wavelength of the line in meters.
        """
        return self.get(self._names["wavelength"])

    @property
    def species_name(self):
        """
        the name of the chemical species that produces the transition.
        """
        return self.get(self._names["species_name"])

    @property
    def status(self):
        """
        the name of the chemical species that produces the transition.
        """
        return self.get(self._names["status"])

    @property
    def initial_level(self):
        """
        a description of the initial (higher energy) quantum level
        """
        return self.get(self._names["initial_level"])

    @property
    def final_level(self):
        """
        a description of the final (higher energy) quantum level
        """
        return self.get(self._names["final_level"])


class SLAResults(query.DALResults):
    """
    The list of matching spectral lines resulting from a spectal line 
    catalog (SLA) query.  
    Each record contains a set of metadata that describes a source or
    observation within the requested circular region (i.e. a "cone").  The 
    number of records in the results is available via the :py:attr:`nrecs` 
    attribute or by passing it to the Python built-in ``len()`` function.  

    This class supports iterable semantics; thus, 
    individual records (in the form of 
    :py:class:`~pyvo.dal.sia.SLARecord` instances) are typically
    accessed by iterating over an ``SLAResults`` instance.  

    >>> results = pyvo.linesearch(url, wavelength='0.0265/0.0280')
    >>> for spl in results:
    ...     print("{0}: {1}".format(spl.species_name, spl.wavelength))

    Alternatively, records can be accessed randomly via 
    :py:meth:`getrecord` or through a Python Database API (v2)
    Cursor (via :py:meth:`~pyvo.dal.query.DALResults.cursor`).  
    Column-based data access is possible via the 
    :py:meth:`~pyvo.dal.query.DALResults.getcolumn` method.  

    ``SLAResults`` is essentially a wrapper around an Astropy 
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

    ``SLAResults`` supports the array item operator ``[...]`` in a 
    read-only context.  When the argument is numerical, the result 
    is an 
    :py:class:`~pyvo.dal.sla.SLARecord` instance, representing the 
    record at the position given by the numerical index.  If the 
    argument is a string, it is interpreted as the name of a column,
    and the data from the column matching that name is returned as 
    a Numpy array.  
    """

    RECORD_CLASS = SLARecord

    def __init__(self, votable, url=None):
        """
        initialize the cursor.  This constructor is not typically called 
        by directly applications; rather an instance is obtained from calling 
        a SLAQuery's execute().
        """
        super(SLAResults, self).__init__(votable, url, "sla", "1.0")
        self._slacols = {


            "ssldm:Line.title": self.fieldname_with_utype("ssldm:Line.title"),
            "ssldm:Line.wavelength.value": self.fieldname_with_utype("ssldm:Line.wavelength.value"),
            "ssldm:Line.initialLevel.energy.value": self.fieldname_with_utype("ssldm:Line.initialLevel.energy.value"),
            "ssldm:Line.finalLevel.energy.value": self.fieldname_with_utype("ssldm:Line.finalLevel.energy.value"),
            "ssldm:Line.environment.temperature.value": self.fieldname_with_utype("ssldm:Line.environment.temperature.value"),
            "ssldm:Line.einsteinA.value": self.fieldname_with_utype("ssldm:Line.einsteinA.value"),
            "ssldm:Process.type": self.fieldname_with_utype("ssldm:Process.type"),
            "ssldm:Process.name": self.fieldname_with_utype("ssldm:Process.name"),
            "ssldm:Line.identificationStatus": self.fieldname_with_utype("ssldm:Line.identificationStatus"),
            "ssldm:Line.species.name": self.fieldname_with_utype("ssldm:Line.species.name"),
            "ssldm:Line.initialLevel.name": self.fieldname_with_utype("ssldm:Line.initialLevel.name"),
            "ssldm:Line.finalLevel.name": self.fieldname_with_utype("ssldm:Line.finalLevel.name"),
            "ssldm:Line.observedWavelength.value": self.fieldname_with_utype("ssldm:Line.observedWavelength.value"),
            "slap:Query.Score": self.fieldname_with_utype("slap:Query.Score"),
            "ssldm:Line.initialLevel.configuration": self.fieldname_with_utype("ssldm:Line.initialLevel.configuration"),
            "ssldm:Line.finalLevel.configuration": self.fieldname_with_utype("ssldm:Line.finalLevel.configuration"),
            "ssldm:Line.initialLevel.quantumState": self.fieldname_with_utype("ssldm:Line.initialLevel.quantumState"),
            "ssldm:Line.finalLevel.quantumState": self.fieldname_with_utype("ssldm:Line.finalLevel.quantumState"),
            "Target.Name": self.fieldname_with_utype("Target.Name"),
            "char:SpatialAxis.Coverage.Location.Value": self.fieldname_with_utype("char:SpatialAxis.Coverage.Location.Value"),
            "char:TimeAxis.Coverage.Bounds.Start": self.fieldname_with_utype("char:TimeAxis.Coverage.Bounds.Start"),
            "char:TimeAxis.Coverage.Bounds.Stop": self.fieldname_with_utype("char:TimeAxis.Coverage.Bounds.Stop")
        }
        self._recnames = { 
            "title":         self._slacols["ssldm:Line.title"],
            "wavelength":    self._slacols["ssldm:Line.wavelength.value"],
            "status":        self._slacols["ssldm:Line.identificationStatus"],
            "species_name":  self._slacols["ssldm:Line.species.name"],
            "initial_level": self._slacols["ssldm:Line.initialLevel.name"],
            "final_level":   self._slacols["ssldm:Line.finalLevel.name"]
            }


class SLAQuery(query.DALQuery):
    """
    a class for preparing an query to an SLA service.  Query constraints
    are added via its service type-specific methods.  The various execute()
    functions will submit the query and return the results.  

    The base URL for the query, which controls where the query will be sent 
    when one of the execute functions is called, is typically set at 
    construction time; however, it can be updated later via the 
    :py:attr:`~pyvo.dal.query.DALQuery.baseurl` to send a configured 
    query to another service.  

    In addition to the search constraint attributes described below, search 
    parameters can be set generically by name via the dict semantics.
    The class attribute, ``std_parameters``, list the parameters 
    defined by the SLA standard.  

    The typical function for submitting the query is ``execute()``; however, 
    alternate execute functions provide the response in different forms, 
    allowing the caller to take greater control of the result processing.  
    """

    RESULTS_CLASS = SLAResults

    std_parameters = [ "REQUEST", "VERSION", "WAVELENGTH", "CHEMICAL_ELEMENT",
                       "INITIAL_LEVEL_ENERGY", "FINAL_LEVEL_ENERGY",
                       "TEMPERATURE", "EINSTEIN_A", "PROCESS_TYPE", 
                       "PROCESS_NAME", "FORMAT" ]
    
    def __init__(self, baseurl,  version="1.0", request="queryData"):
        """
        initialize the query object with a baseurl and request type
        """
        super(SLAQuery, self).__init__(baseurl, "sla", version)
        self["REQUEST"] = request
        
    @property
    def wavelength(self):
        """
        the wavelength range given in a range-list format in units of meters

        Examples of proper format include:

        =========================  =====================================
        0.20/0.21.5                a wavelength range that includes 21cm
        2.7E-7/0.13                a bandpass from optical to radio
        =========================  =====================================
        """
        return self.get("WAVELENGTH")
    @wavelength.setter
    def wavelength(self, val):
        regex = "\\d+\\.?\\d*([eE][-+]?\\d+)?/?\\d*\\.?\\d*([eE][-+]?\\d+)?$"
        for part in val.split(","):
           if re.match(regex, part) is None:
               raise ValueError("range syntax is wrong")
        
        self["WAVELENGTH"] = val
    @wavelength.deleter
    def wavelength(self):
        del self["WAVELENGTH"]

    @property
    def format(self):
        """
        This parameter is used to only to retrieve a expressly empty 
        result for the benefit of receiving table header information.
        When set to the special value of "metadata", all other constraints
        will be ignored and an empty result will be returned.  
        """
        return self.get("FORMAT")
    @format.setter
    def format(self, val):
        # check values
        formats = val.split(",")
        for f in formats:
            f = f.lower()
            if f not in ["metadata"]:
                raise ValueError("format type not valid: " + f)

        self["FORMAT"] = val
    @format.deleter
    def format(self):
        del self["FORMAT"]


class SLAService(query.DALService):
    """
    a representation of an spectral line catalog (SLA) service
    """

    QUERY_CLASS = SLAQuery

    def __init__(self, baseurl, resmeta=None, version="1.0"):
        """
        instantiate an SLA service

        Parameters
        ----------
        baseurl : str
           the base URL for submitting search queries to the service.
        resmeta : dict
           an optional dictionary of properties about the service
        """
        super(SLAService, self).__init__(baseurl, "sla", version, resmeta)

    def search(self, wavelength, format=None, **keywords):
        """
        submit a simple SLA query to this service with the given constraints.  

        This method is provided for a simple but typical SLA queries.  For 
        more complex queries, one should create an SLAQuery object via 
        create_query()

        Parameters
        ----------
        wavelength : 2-element sequence of floats
           a 2-element sequence giving the wavelength spectral range to 
           search in meters
        format : str
           the spectral format(s) of interest. "metadata" 
           indicates that no spectra should be returned--only 
           an empty table with complete metadata.

        Returns
        -------
        SLAResults
            a container holding a table of matching spectral lines

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
        SLAResults
        pyvo.dal.query.DALServiceError
        pyvo.dal.query.DALQueryError
        """
        q = self.create_query(wavelength, format)
        return q.execute()

    def create_query(self, wavelength=None, format=None):
        """
        create a query object that constraints can be added to and then 
        executed.  The input arguments will initialize the query with the 
        given values.

        Parameters
        ----------
        wavelength : 2-element sequence of floats
           a 2-element tuple giving the wavelength spectral range to search 
           in meters
        format : str
           the spectral format(s) of interest. "metadata" indicates that no
           spectra should be returned--only an empty table with complete 
           metadata.

        Returns
        -------
        SLAQuery
           the query instance

        See Also
        --------
        SLAQuery
        """
        q = self.QUERY_CLASS(self.baseurl, self.version)
        if wavelength is not None: q.wavelength = wavelength
        if format: q.format = format
        return q
