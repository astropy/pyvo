# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
A module for searching for spectra in a remote archive.

A Simple Spectral Access (SSA) service allows a client to search for
spectra in an archive whose field of view overlaps with a given cone
on the sky.  The service responds to a search query with a table in
which each row represents an image that is available for download.
The columns provide metadata describing each image and one column in
particular provides the image's download URL (also called the *access
reference*, or *acref*).  Some SSA services can create spectra
on-the-fly from underlying data (e.g. image cubes); in this case, the
query result is a table of images whose aperture matches the
requested cone and which will be created when accessed via the
download URL.

This module provides an interface for accessing an SSA service.  It is
implemented as a specialization of the DAL Query interface.

The ``search()`` function support the simplest and most common types
of queries, returning an SSAResults instance as its results which
represents the matching imagess from the archive.  The SSAResults
supports access to and iterations over the individual records; these
are provided as SSARecord instances, which give easy access to key
metadata in the response, such as the position of the spectrum's
aperture, the spectrum format, its frequency range, and its download
URL.

The SSAService class can represent a specific service available at a URL
endpoint.
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import re
from astropy.extern import six
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.units import Quantity, Unit
from astropy.units import spectral as spectral_equivalencies
from .query import DALResults, DALQuery, DALService, Record, mime2extension

__all__ = ["search", "SSAService", "SSAQuery", "SSAResults", "SSARecord"]

def search(baseurl, pos, diameter=None, band=None, time=None, format='all', **keywords):
    """
    submit a simple SSA query that requests spectra overlapping a given region

    Parameters
    ----------
    baseurl : str
        the base URL for the SSA service
    pos : `~astropy.coordinates.SkyCoord` class or sequence of two floats
        the position of the center of the circular search region.
        assuming icrs decimal degrees if unit is not specified.
    diameter : `~astropy.units.Quantity` class or scalar float
        the diameter of the circular region around pos in which to search.
        assuming icrs decimal degrees if unit is not specified.
    band : `~astropy.units.Quantity` class or sequence of two floats
        the bandwidth range the observations belong to.
        assuming meters if unit is not specified.
    time : `~astropy.time.Time` class or sequence of two strings
        the datetime range the observations were made in.
        assuming iso 8601 if format is not specified.
    format : str
        the image format(s) of interest.  "all" indicates
        all available formats; "graphic" indicates
        graphical images (e.g. jpeg, png, gif; not FITS);
        "metadata" indicates that no images should be
        returned--only an empty table with complete metadata.
    **keywords :
        additional case insensitive parameters can be given via arbitrary
        case insensitive keyword arguments. Where there is overlap
        with the parameters set by the other arguments to
        this function, these keywords will override.

    Returns
    -------
    SSAResults
        a container holding a table of matching spectrum records

    Raises
    ------
    DALServiceError
       for errors connecting to or communicating with the service
    DALQueryError
       if the service responds with an error, including a query syntax error.

    See Also
    --------
    SSAResults
    pyvo.dal.query.DALServiceError
    pyvo.dal.query.DALQueryError
    """
    return SSAService(baseurl).search(pos, diameter, band, time, format, **keywords)


class SSAService(DALService):
    """
    a representation of an SSA service
    """

    def __init__(self, baseurl):
        """
        instantiate an SSA service

        Parameters
        ----------
        baseurl : str
           the base URL for submitting search queries to the service.
        """
        super(SSAService, self).__init__(baseurl)

    def search(self, pos, diameter, band=None, time=None, format='all', **keywords):
        """
        submit a simple SSA query to this service with the given constraints.

        This method is provided for a simple but typical SSA queries.  For
        more complex queries, one should create an SSAQuery object via
        create_query()

        Parameters
        ----------
        pos : `~astropy.coordinates.SkyCoord` class or sequence of two floats
            the position of the center of the circular search region.
            assuming icrs decimal degrees if unit is not specified.
        diameter : `~astropy.units.Quantity` class or scalar float
            the diameter of the circular region around pos in which to search.
            assuming icrs decimal degrees if unit is not specified.
        band : `~astropy.units.Quantity` class or sequence of two floats
            the bandwidth range the observations belong to.
            assuming meters if unit is not specified.
        time : `~astropy.time.Time` class or sequence of two strings
            the datetime range the observations were made in.
            assuming iso 8601 if format is not specified.
        format : str
           the image format(s) of interest.  "all" indicates
           all available formats; "graphic" indicates
           graphical images (e.g. jpeg, png, gif; not FITS);
           "metadata" indicates that no images should be
           returned--only an empty table with complete metadata.
        **keywords :
           additional case insensitive parameters can be given via arbitrary
           case insensitive keyword arguments. Where there is overlap
           with the parameters set by the other arguments to
           this function, these keywords will override.

        Returns
        -------
        SSAResults
           a container holding a table of matching catalog records

        Raises
        ------
        DALServiceError
           for errors connecting to or communicating with the service
        DALQueryError
           if the service responds with an error, including a query syntax error

        See Also
        --------
        SSAResults
        pyvo.dal.query.DALServiceError
        pyvo.dal.query.DALQueryError
        """
        return self.create_query(
            pos, diameter, band, time, format, **keywords).execute()

    def create_query(
            self, pos=None, diameter=None, band=None, time=None, format=None,
            request="queryData", **keywords):
        """
        create a query object that constraints can be added to and then
        executed.  The input arguments will initialize the query with the
        given values.

        Parameters
        ----------
        pos : `~astropy.coordinates.SkyCoord` class or sequence of two floats
            the position of the center of the circular search region.
            assuming icrs decimal degrees if unit is not specified.
        diameter : `~astropy.units.Quantity` class or scalar float
            the diameter of the circular region around pos in which to search.
            assuming icrs decimal degrees if unit is not specified.
        band : `~astropy.units.Quantity` class or sequence of two floats
            the bandwidth range the observations belong to.
            assuming meters if unit is not specified.
        time : `~astropy.time.Time` class or sequence of two strings
            the datetime range the observations were made in.
            assuming iso 8601 if format is not specified.
        format : str
           the image format(s) of interest.  "all" indicates
           all available formats; "graphic" indicates
           graphical images (e.g. jpeg, png, gif; not FITS);
           "metadata" indicates that no images should be
           returned--only an empty table with complete metadata.
        **keywords :
           additional case insensitive parameters can be given via arbitrary
           case insensitive keyword arguments. Where there is overlap
           with the parameters set by the other arguments to
           this function, these keywords will override.

        Returns
        -------
        SSAQuery
            the query instance

        See Also
        --------
        SSAQuery
        """
        return SSAQuery(
            self.baseurl, pos, diameter, band, time, format, request,
            **keywords)


class SSAQuery(DALQuery):
    """
    a class for preparing an query to an SSA service.  Query constraints
    are added via its service type-specific properties and methods.  Once
    all the constraints are set, one of the various execute() functions
    can be called to submit the query and return the results.

    The base URL for the query, which controls where the query will be sent
    when one of the execute functions is called, is typically set at
    construction time; however, it can be updated later via the
    :py:attr:`~pyvo.dal.query.DALQuery.baseurl` to send a configured
    query to another service.

    The typical function for submitting the query is ``execute()``; however,
    alternate execute functions provide the response in different forms,
    allowing the caller to take greater control of the result processing.

    """

    def __init__(
            self, baseurl, pos=None, diameter=None, band=None, time=None,
            format=None, request="queryData", **keywords):
        """
        initialize the query object with a baseurl and the given parameters

        Parameters
        ----------
        baseurl : str
            the base URL for the SSA service
        pos : `~astropy.coordinates.SkyCoord` class or sequence of two floats
            the position of the center of the circular search region.
            assuming icrs decimal degrees if unit is not specified.
        diameter : `~astropy.units.Quantity` class or scalar float
            the diameter of the circular region around pos in which to search.
            assuming icrs decimal degrees if unit is not specified.
        band : `~astropy.units.Quantity` class or sequence of two floats
            the bandwidth range the observations belong to.
            assuming meters if unit is not specified.
        time : `~astropy.time.Time` class or sequence of two strings
            the datetime range the observations were made in.
            assuming iso 8601 if format is not specified.
        format : str
           the image format(s) of interest.  "all" indicates
           all available formats; "graphic" indicates
           graphical images (e.g. jpeg, png, gif; not FITS);
           "metadata" indicates that no images should be
           returned--only an empty table with complete metadata.
        **keywords :
           additional case insensitive parameters can be given via arbitrary
           case insensitive keyword arguments. Where there is overlap
           with the parameters set by the other arguments to
           this function, these keywords will override.
        """
        super(SSAQuery, self).__init__(baseurl)

        if pos:
            self.pos = pos

        if diameter:
            self.diameter = diameter

        if band:
            self.band = band

        if time:
            self.time = time

        if format:
            self.format = format

        self.request = request

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

        self["POS"] = "{ra},{dec}".format(
            ra=val.icrs.ra.deg, dec=val.icrs.dec.deg)
    @pos.deleter
    def pos(self):
        delattr(self, "_pos")
        del self["POS"]

    @property
    def diameter(self):
        """
        the diameter of the circular region around pos as a
        `~astropy.units.Quantity` instance.
        """
        return getattr(self, "_diameter", None)
    @diameter.setter
    def diameter(self, val):
        setattr(self, "_diameter", val)

        if not isinstance(val, Quantity):
            # assume degrees
            val = val * Unit("deg")
            try:
                if len(val):
                    raise ValueError(
                        "diameter may be specified using exactly one value")
            except TypeError:
                # len 1
                pass

        self["SIZE"] = val.to(Unit("deg")).value
    @diameter.deleter
    def diameter(self):
        delattr(self, "_diameter")
        del self["SIZE"]

    @property
    def band(self):
        """
        the bandwidth range the observations belong to.
        """
        return getattr(self, "_band", None)
    @band.setter
    def band(self, val):
        setattr(self, "_band", val)

        if not isinstance(val, Quantity):
            # assume meters
            val = val * Unit("meter")
            try:
                if len(val) != 2:
                    raise ValueError(
                        "band must be specified with exactly two values")
            except TypeError:
                raise ValueError(
                    "band must be specified with exactly two values")
        # transform to meters
        val = val.to(Unit("m"), equivalencies=spectral_equivalencies())
        # frequency is counter-proportional to wavelength, so we just sort
        # it to have the right order again
        val.sort()

        self["BAND"] = "{start}/{end}".format(
            start=val.value[0], end=val.value[1])
    @band.deleter
    def band(self):
        delattr(self, "_band")
        del self["BAND"]

    @property
    def time(self):
        """
        the datetime range the observations were made in.
        """
        return getattr(self, "_time", None)
    @time.setter
    def time(self, val):
        setattr(self, "_time", val)

        if not isinstance(val, Time):
            # assume iso8601
            val = Time(val, format="isot")
            try:
                if len(val) != 2:
                    raise ValueError(
                        "time must be specified with exactly two values")
            except TypeError:
                raise ValueError(
                    "time must be specified with exactly two values")

        self["TIME"] = "{start}/{end}".format(
            start=val.isot[0], end=val.isot[1])
    @time.deleter
    def time(self):
        delattr(self, "_time")
        del self["TIME"]

    @property
    def format(self):
        """
        the image format(s) of interest.  "all" indicates
        all available formats; "graphic" indicates
        graphical images (e.g. jpeg, png, gif; not FITS);
        "metadata" indicates that no images should be
        returned--only an empty table with complete metadata.
        """
        return getattr(self, "_format", None)
    @format.setter
    def format(self, val):
        setattr(self, "_format", val)

        if type(val) in (six.text_type, six.binary_type):
            val = [val]

        self["FORMAT"] = ",".join(val)
    @format.deleter
    def format(self):
        delattr(self, "_format")
        del self["FORMAT"]

    @property
    def request(self):
        """
        the type of service operation which is being performed
        """
        return getattr(self, "_request", None)
    @request.setter
    def request(self, val):
        setattr(self, "_request", val)
        self["REQUEST"] = val
    @request.deleter
    def request(self):
        delattr(self, "_request")
        del self["REQUEST"]

    def execute(self):
        """
        submit the query and return the results as a SSAResults instance

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
        return SSAResults(self.execute_votable(), self.queryurl)


class SSAResults(DALResults):
    """
    The list of matching images resulting from a spectrum (SSA) query.
    Each record contains a set of metadata that describes an available
    spectrum matching the query constraints.  The number of records in
    the results is by passing it to the Python built-in ``len()`` function.

    This class supports iterable semantics; thus,
    individual records (in the form of
    :py:class:`~pyvo.dal.ssa.SSARecord` instances) are typically
    accessed by iterating over an ``SSAResults`` instance.

    >>> results = pyvo.spectrumsearch(url, pos=[12.24, -13.1], diameter=0.2)
    >>> for spec in results:
    ...     print("{0}: {1}".format(spec.title, spec.getdataurl()))

    Alternatively, records can be accessed randomly via
    :py:meth:`getrecord` or through a Python Database API (v2)
    Cursor (via :py:meth:`~pyvo.dal.query.DALResults.cursor`).
    Column-based data access is possible via the
    :py:meth:`~pyvo.dal.query.DALResults.getcolumn` method.

    ``SSAResults`` is essentially a wrapper around an Astropy
    :py:mod:`~astropy.io.votable`
    :py:class:`~astropy.io.votable.tree.Table` instance where the
    columns contain the various metadata describing the spectra.
    One can access that VOTable directly via the
    :py:attr:`~pyvo.dal.query.DALResults.votable` attribute.  Thus,
    when one retrieves a whole column via
    :py:meth:`~pyvo.dal.query.DALResults.getcolumn`, the result is
    a Numpy array.  Alternatively, one can manipulate the results
    as an Astropy :py:class:`~astropy.table.table.Table` via the
    following conversion:

    >>> table = results.votable.to_table()

    ``SSAResults`` supports the array item operator ``[...]`` in a
    read-only context.  When the argument is numerical, the result
    is an
    :py:class:`~pyvo.dal.ssa.SSARecord` instance, representing the
    record at the position given by the numerical index.  If the
    argument is a string, it is interpreted as the name of a column,
    and the data from the column matching that name is returned as
    a Numpy array.
    """

    def getrecord(self, index):
        """
        return a representation of a sia result record that follows
        dictionary semantics. The keys of the dictionary are those returned by
        this instance's fieldnames attribute. The returned record has additional
        image-specific properties

        Parameters
        ----------
        index : int
           the integer index of the desired record where 0 returns the first
           record

        Returns
        -------
        SIARecord
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
        return SSARecord(self, index)


class SSARecord(Record):
    """
    a dictionary-like container for data in a record from the results of an
    SSA query, describing an available spectrum.

    The commonly accessed metadata which are stadardized by the SSA
    protocol are available as attributes.  If the metadatum accessible
    via an attribute is not available, the value of that attribute
    will be None.  All metadata, including non-standard metadata, are
    acessible via the ``get(`` *key* ``)`` function (or the [*key*]
    operator) where *key* is table column name.
    """

    @property
    def ra(self):
        """
        return the right ascension of the center of the spectrum
        """
        return self.getbyutype("ssa:Target.Pos")[0]

    @property
    def dec(self):
        """
        return the declination of the center of the spectrum
        """
        return self.getbyutype("ssa:Target.Pos")[1]

    @property
    def title(self):
        """
        return the title of the spectrum
        """
        return self.getbyutype("ssa:DataID.Title", decode=True)

    @property
    def format(self):
        """
        return the file format that this the spectrum is stored in
        """
        return self.getbyutype("ssa:Access.Format", decode=True)

    @property
    def dateobs(self):
        """
        return the modified Julien date (MJD) of the mid-point of the
        observational data that went into the spectrum
        """
        dateobs = self.getbyutype("ssa:DataID.Date", decode=True)
        if dateobs:
            return Time(dateobs, format="iso")
        else:
            return None

    @property
    def instr(self):
        """
        return the name of the instrument (or instruments) that produced the
        data that went into this spectrum.
        """
        return self.getbyutype("ssa:DataID.Instrument", decode=True)

    @property
    def acref(self):
        """
        return the URL that can be used to retrieve the spectrum.
        """
        return self.getbyutype("ssa:Access.Reference", decode=True)

    def getdataurl(self):
        """
        return the URL contained in the access URL column which can be used
        to retrieve the dataset described by this record.  None is returned
        if no such column exists.
        """
        return self.acref

    def suggest_dataset_basename(self):
        """
        return a default base filename that the dataset available via
        ``getdataset()`` can be saved as.  This function is
        specialized for a particular service type this record originates from
        so that it can be used by ``cachedataset()`` via
        ``make_dataset_filename()``.
        """
        out = self.title
        if type(out) == six.binary_type:
            out = out.decode('utf-8')

        if not out:
            out = "spectrum"
        else:
            out = re.sub(r'\s+', '_', out.strip())
        return out

    def suggest_extension(self, default=None):
        """
        returns a recommended filename extension for the dataset described
        by this record.  Typically, this would look at the column describing
        the format and choose an extension accordingly.
        """
        return mime2extension(self.format, default)
