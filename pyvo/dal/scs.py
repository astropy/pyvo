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
response, including the ICRS position of the matched source or observation.

This module also features the SCSQuery class that provides an
interface for building up and remembering a query.  The SCSService
class can represent a specific service available at a URL endpoint.
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

from astropy.coordinates import SkyCoord
from astropy.units import Unit, Quantity
from .query import DALResults, DALQuery, DALService, Record

__all__ = ["search", "SCSService", "SCSQuery", "SCSResults", "SCSRecord"]

def search(url, pos, radius=1.0, verbosity=2, **keywords):
    """
    submit a simple Cone Search query that requests objects or observations
    whose positions fall within some distance from a search position.

    Parameters
    ----------
    url : str
        the base URL of the query service.
    pos : astropy.coordinates.SkyCoord
        a SkyCoord instance defining the position of the center of the
        circular search region.
        converted if it's a iterable containing scalars, assuming icrs degrees.
    radius : `~astropy.units.Quantity` or float
        a Quantity instance defining the radius of the circular search
        region, in degrees.
        converted if it is another unit.
    verbosity : int
        an integer value that indicates the volume of columns
        to return in the result table.  0 means the minimum
        set of columsn, and 3 means as many columns as are available.
    **keywords :
        additional case insensitive parameters can be given via arbitrary
        case insensitive keyword arguments. Where there is overlap
        with the parameters set by the other arguments to
        this function, these keywords will override.

    Returns
    -------
    SCSResults
        a container holding a table of matching catalog records

    Raises
    ------
    DALServiceError
       for errors connecting to or communicating with the service.
    DALQueryError
       if the service responds with an error,
       including a query syntax error.

    See Also
    --------
    SCSResults
    pyvo.dal.query.DALServiceError
    pyvo.dal.query.DALQueryError
    """
    return SCSService(url).search(pos, radius, verbosity, **keywords)


class SCSService(DALService):
    """
    a representation of a Cone Search service
    """

    def __init__(self, baseurl):
        """
        instantiate a Cone Search service

        Parameters
        ----------
        baseurl : str
           the base URL for submitting search queries to the service.
        """
        super(SCSService, self).__init__(baseurl)

    def search(self, pos, radius=1.0, verbosity=2, **keywords):
        """
        submit a simple Cone Search query that requests objects or observations
        whose positions fall within some distance from a search position.

        Parameters
        ----------
        pos : astropy.coordinates.SkyCoord
            a SkyCoord instance defining the position of the center of the
            circular search region.
            converted if it's a iterable containing scalars,
            assuming icrs degrees.
        radius : `~astropy.units.Quantity` or float
            a Quantity instance defining the radius of the circular search
            region, in degrees.
            converted if it is another unit.
        verbosity : int
           an integer value that indicates the volume of columns
           to return in the result table.  0 means the minimum
           set of columns, 3 means as many columns as are available.
        **keywords :
           additional case insensitive parameters can be given via arbitrary
           case insensitive keyword arguments. Where there is overlap
           with the parameters set by the other arguments to
           this function, these keywords will override.

        Returns
        -------
        SCSResults
            a container holding a table of matching catalog records

        Raises
        ------
        DALServiceError
           for errors connecting to or communicating with the service
        DALQueryError
           if the service responds with an error,
           including a query syntax error.

        See Also
        --------
        SCSResults
        pyvo.dal.query.DALServiceError
        pyvo.dal.query.DALQueryError
        """
        return self.create_query(pos, radius, verbosity, **keywords).execute()

    def create_query(self, pos=None, radius=None, verbosity=None, **keywords):
        """
        create a query object that constraints can be added to and then
        executed.  The input arguments will initialize the query with the
        given values.

        Parameters
        ----------
        pos : astropy.coordinates.SkyCoord
            a SkyCoord instance defining the position of the center of the
            circular search region.
            converted if it's a iterable containing scalars,
            assuming icrs degrees.
        radius : `~astropy.units.Quantity` or float
            a Quantity instance defining the radius of the circular search
            region, in degrees.
            converted if it is another unit.
        verbosity : int
            an integer value that indicates the volume of columns
            to return in the result table.  0 means the minimum
            set of columns, 3 means as many columns as are available.
        **keywords :
           additional case insensitive parameters can be given via arbitrary
           case insensitive keyword arguments. Where there is overlap
           with the parameters set by the other arguments to
           this function, these keywords will override.

        Returns
        -------
        SCSQuery
            the query instance

        See Also
        --------
        SCSQuery
        """
        return SCSQuery(self.baseurl, pos, radius, verbosity, **keywords)


class SCSQuery(DALQuery):
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

    The typical function for submitting the query is ``execute()``; however,
    alternate execute functions provide the response in different forms,
    allowing the caller to take greater control of the result processing.
    """

    def __init__(
            self, baseurl, pos=None, radius=None, verbosity=None, **keywords):
        """
        initialize the query object with a baseurl and the given parameters

        Parameters
        ----------
        pos : astropy.coordinates.SkyCoord
            a SkyCoord instance defining the position of the center of the
            circular search region.
            converted if it's a iterable containing scalars,
            assuming icrs degrees.
        radius : `~astropy.units.Quantity` or float
            a Quantity instance defining the radius of the circular search
            region, in degrees.
            converted if it is another unit.
        verbosity : int
            an integer value that indicates the volume of columns
            to return in the result table.  0 means the minimum
            set of columns, 3 means as many columns as are
            available.
        """
        super(SCSQuery, self).__init__(baseurl)

        if pos:
            self.pos = pos

        if radius:
            self.radius = radius

        if verbosity:
            self.verbosity = verbosity

        self.update({key.upper(): value for key, value in keywords.items()})

    @property
    def pos(self):
        """
        the position of the center of the circular search region as a
        `~astropy.coordinates.SkyCoord` instance.
        """
        return getattr(self, "_pos", None)
    @pos.setter
    def pos(self, val):
        setattr(self, "_pos", val)

        # use the astropy, luke
        if not isinstance(val, SkyCoord):
            pos_ra, pos_dec = val

            # assume ICRS degrees
            val = SkyCoord(ra=pos_ra, dec=pos_dec, unit="deg", frame="icrs")

        self["RA"] = val.icrs.ra.deg
        self["DEC"] = val.icrs.dec.deg
    @pos.deleter
    def pos(self):
        delattr(self, "_pos")
        del self["RA"]
        del self["DEC"]

    @property
    def radius(self):
        """
        the radius of the circular region around pos as a
        `~astropy.units.Quantity` instance.
        """
        return getattr(self, "_radius", None)
    @radius.setter
    def radius(self, val):
        setattr(self, "_radius", val)

        if not isinstance(val, Quantity):
            # assume degrees
            val = val * Unit("deg")
            try:
                if len(val):
                    raise ValueError(
                        "radius may be specified using exactly one value")
            except TypeError:
                # len 1
                pass

        self["SR"] = val.to(Unit("deg")).value
    @radius.deleter
    def radius(self):
        delattr(self, "_radius")
        del self["SR"]

    @property
    def verbosity(self):
        """
        an integer value that indicates the volume of columns
        to return in the result table.  0 means the minimum
        set of columsn, 3 means as many columns as are  available.
        """
        return getattr(self, "_verbosity", None)
    @verbosity.setter
    def verbosity(self, val):
        setattr(self, "_verbosity", val)
        self["VERB"] = val
    @verbosity.deleter
    def verbosity(self):
        delattr(self, "_verbosity")
        del self["VERB"]

    def execute(self):
        """
        submit the query and return the results as a SCSResults instance

        Raises
        ------
        DALServiceError
           for errors connecting to or communicating with the service
        DALQueryError
           for errors either in the input query syntax or
           other user errors detected by the service
        DALFormatError
           for errors parsing the VOTable response
        """
        return SCSResults(self.execute_votable(), self.queryurl)


class SCSResults(DALResults):
    """
    The list of matching catalog records resulting from a catalog (SCS) query.
    Each record contains a set of metadata that describes a source or
    observation within the requested circular region (i.e. a "cone").  The
    number of records in the results is available via the :py:attr:`nrecs
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
        return a representation of a conesearch result record that follows
        dictionary semantics. The keys of the dictionary are those returned by
        this instance's fieldnames attribute. The returned record has the
        following additional properties: id, ra, dec

        Parameters
        ----------
        index : int
           the integer index of the desired record where 0 returns the first
           record

        Returns
        -------
        SCSRecord
           a dictionary-like wrapper containing the result record metadata.

        Raises
        ------
        IndexError
           if index is negative or equal or larger than the number of rows in
           the result table.

        See Also
        --------
        Record
        """
        return SCSRecord(self, index)


class SCSRecord(Record):
    """
    a dictionary-like container for data in a record from the results of an
    Cone Search (SCS) query, describing a matching source or observation.

    The commonly accessed metadata which are stadardized by the SCS
    protocol are available as attributes.  All metadata, particularly
    non-standard metadata, are acessible via the ``get(`` *key* ``)``
    function (or the [*key*] operator) where *key* is table column name.
    """

    @property
    def pos(self):
        """
        the position of the object or observation described by this record.
        """
        return SkyCoord(
            ra=self.getbyucd("POS_EQ_RA_MAIN"),
            dec=self.getbyucd("POS_EQ_DEC_MAIN"),
            unit="deg", frame="icrs")

    @property
    def id(self):
        """
        return the identifying name of the object or observation described by
        this record.
        """
        return self.getbyucd("ID_MAIN")
