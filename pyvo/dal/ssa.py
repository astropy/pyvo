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

For more complex queries, the SSAQuery class can be helpful which 
allows one to build up, tweak, and reuse a query.  The SSAService
class can represent a specific service available at a URL endpoint.
"""
from __future__ import print_function, division

import numbers
import re
import sys
from . import query

__all__ = [ "search", "SSAService", "SSAQuery", "SSAResults", "SSARecord" ]

def search(url, pos, size, format='all', **keywords):
    """
    submit a simple SSA query that requests spectra overlapping a 

    Parameters
    ----------
    url : str
       the base URL for the SSA service
    pos : 2-element sequence of floats
       a 2-element seqence giving the ICRS RA and DEC in decimal degrees
    size : float
       a floating point number giving the diameter of the circular region
       in decimal degrees around pos in which to search for spectra.  
    format : str
       the spectral format(s) of interest.  "all" (default) 
       indicates all available formats; "graphic" indicates
       graphical images (e.g. jpeg, png, gif; not FITS); 
       "metadata" indicates that no images should be 
       returned--only an empty table with complete metadata.
    **keywords:   
       additional parameters can be given via arbitrary 
       keyword arguments.  These can be either standard 
       parameters (with names drown from the 
       ``SSAQuery.std_parameters`` list) or paramters
       custom to the service.  Where there is overlap 
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
    service = SSAService(url)
    return service.search(pos, size, format, **keywords)


class SSARecord(query.Record):
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

    def __init__(self, results, index):
        super(SSARecord, self).__init__(results, index)
        self._utypecols = results._ssacols
        self._names = results._recnames

    @property
    def ra(self):
        """
        return the right ascension of the center of the spectrum
        """
        return self.get(self._names["pos"])[0]

    @property
    def dec(self):
        """
        return the declination of the center of the spectrum
        """
        return self.get(self._names["pos"])[1]

    @property
    def title(self):
        """
        return the title of the spectrum
        """
        return self.get(self._names["title"])

    @property
    def format(self):
        """
        return the file format that this the spectrum is stored in
        """
        return self.get(self._names["format"])

    @property
    def dateobs(self):
        """
        return the modified Julien date (MJD) of the mid-point of the 
        observational data that went into the spectrum
        """
        return self.get(self._names["dateobs"])

    @property
    def instr(self):
        """
        return the name of the instrument (or instruments) that produced the 
        data that went into this spectrum.
        """
        return self.get(self._names["instr"])

    @property
    def acref(self):
        """
        return the URL that can be used to retrieve the spectrum.
        """
        return self.get_str(self._names["acref"])

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
        if query._is_python3 and isinstance(out, bytes):
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
        return query.mime2extension(self.format, default)


class SSAResults(query.DALResults):
    """
    The list of matching images resulting from a spectrum (SSA) query.  
    Each record contains a set of metadata that describes an available
    spectrum matching the query constraints.  The number of records in
    the results is available via the :py:attr:`nrecs` attribute or by 
    passing it to the Python built-in ``len()`` function.  

    This class supports iterable semantics; thus, 
    individual records (in the form of 
    :py:class:`~pyvo.dal.ssa.SSARecord` instances) are typically
    accessed by iterating over an ``SSAResults`` instance.  

    >>> results = pyvo.spectrumsearch(url, pos=[12.24, -13.1], size=0.2)
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

    RECORD_CLASS = SSARecord

    def __init__(self, votable, url=None):
        """
        initialize the cursor.  This constructor is not typically called 
        by directly applications; rather an instance is obtained from calling 
        a SSAQuery's execute().
        """
        super(SSAResults, self).__init__(votable, url, "ssa", "1.0")
        self._ssacols = {

            "ssa:Query.Score": self.fieldname_with_utype("ssa:Query.Score"),
            "ssa:Query.Token": self.fieldname_with_utype("ssa:Query.Token"),
            "ssa:Association.Type": self.fieldname_with_utype("ssa:Association.Type"),
            "ssa:Association.ID": self.fieldname_with_utype("ssa:Association.ID"),
            "ssa:Association.Key": self.fieldname_with_utype("ssa:Association.Key"),
            "ssa:Access.Reference": self.fieldname_with_utype("ssa:Access.Reference"),
            "ssa:Access.Format": self.fieldname_with_utype("ssa:Access.Format"),
            "ssa:Access.Size": self.fieldname_with_utype("ssa:Access.Size"),
            "ssa:DataModel": self.fieldname_with_utype("ssa:DataModel"),
            "ssa:Type": self.fieldname_with_utype("ssa:Type"),
            "ssa:Length": self.fieldname_with_utype("ssa:Length"),
            "ssa:TimeSI": self.fieldname_with_utype("ssa:TimeSI"),
            "ssa:SpectralSI": self.fieldname_with_utype("ssa:SpectralSI"),
            "ssa:FluxSI": self.fieldname_with_utype("ssa:FluxSI"),
            "ssa:SpectralAxis": self.fieldname_with_utype("ssa:SpectralAxis"),
            "ssa:FluxAxis": self.fieldname_with_utype("ssa:FluxAxis"),
            "ssa:DataID.Title": self.fieldname_with_utype("ssa:DataID.Title"),
            "ssa:DataID.Creator": self.fieldname_with_utype("ssa:DataID.Creator"),
            "ssa:DataID.Collection": self.fieldname_with_utype("ssa:DataID.Collection"),
            "ssa:DataID.DatasetID": self.fieldname_with_utype("ssa:DataID.DatasetID"),
            "ssa:DataID.CreatorDID": self.fieldname_with_utype("ssa:DataID.CreatorDID"),
            "ssa:DataID.Date": self.fieldname_with_utype("ssa:DataID.Date"),
            "ssa:DataID.Version": self.fieldname_with_utype("ssa:DataID.Version"),
            "ssa:DataID.Instrument": self.fieldname_with_utype("ssa:DataID.Instrument"),
            "ssa:DataID.Bandpass": self.fieldname_with_utype("ssa:DataID.Bandpass"),
            "ssa:DataID.DataSource": self.fieldname_with_utype("ssa:DataID.DataSource"),
            "ssa:DataID.CreationType": self.fieldname_with_utype("ssa:DataID.CreationType"),
            "ssa:DataID.Logo": self.fieldname_with_utype("ssa:DataID.Logo"),
            "ssa:DataID.Contributor": self.fieldname_with_utype("ssa:DataID.Contributor"),
            "ssa:Curation.Publisher": self.fieldname_with_utype("ssa:Curation.Publisher"),
            "ssa:Curation.PublisherID": self.fieldname_with_utype("ssa:Curation.PublisherID"),
            "ssa:Curation.PublisherDID": self.fieldname_with_utype("ssa:Curation.PublisherDID"),
            "ssa:Curation.Date": self.fieldname_with_utype("ssa:Curation.Date"),
            "ssa:Curation.Version": self.fieldname_with_utype("ssa:Curation.Version"),
            "ssa:Curation.Rights": self.fieldname_with_utype("ssa:Curation.Rights"),
            "ssa:Curation.Reference": self.fieldname_with_utype("ssa:Curation.Reference"),
            "ssa:Curation.Contact.Name": self.fieldname_with_utype("ssa:Curation.Contact.Name"),
            "ssa:Curation.Contact.Email": self.fieldname_with_utype("ssa:Curation.Contact.Email"),
            "ssa:Target.Name": self.fieldname_with_utype("ssa:Target.Name"),
            "ssa:Target.Description": self.fieldname_with_utype("ssa:Target.Description"),
            "ssa:Target.Class": self.fieldname_with_utype("ssa:Target.Class"),
            "ssa:Target.Pos": self.fieldname_with_utype("ssa:Target.Pos"),
            "ssa:Target.SpectralClass": self.fieldname_with_utype("ssa:Target.SpectralClass"),
            "ssa:Target.Redshift": self.fieldname_with_utype("ssa:Target.Redshift"),
            "ssa:Target.VarAmpl": self.fieldname_with_utype("ssa:Target.VarAmpl"),
            "ssa:Derived.SNR": self.fieldname_with_utype("ssa:Derived.SNR"),
            "ssa:Derived.Redshift.Value": self.fieldname_with_utype("ssa:Derived.Redshift.Value"),
            "ssa:Derived.Redshift.StatError": self.fieldname_with_utype("ssa:Derived.Redshift.StatError"),
            "ssa:Derived.Redshift.Confidence": self.fieldname_with_utype("ssa:Derived.Redshift.Confidence"),
            "ssa:Derived.VarAmpl": self.fieldname_with_utype("ssa:Derived.VarAmpl"),
            "ssa:CoordSys.ID": self.fieldname_with_utype("ssa:CoordSys.ID"),
            "ssa:CoordSys.SpaceFrame.Name": self.fieldname_with_utype("ssa:CoordSys.SpaceFrame.Name"),
            "ssa:CoordSys.SpaceFrame.Ucd": self.fieldname_with_utype("ssa:CoordSys.SpaceFrame.Ucd"),
            "ssa:CoordSys.SpaceFrame.RefPos": self.fieldname_with_utype("ssa:CoordSys.SpaceFrame.RefPos"),
            "ssa:CoordSys.SpaceFrame.Equinox": self.fieldname_with_utype("ssa:CoordSys.SpaceFrame.Equinox"),
            "ssa:CoordSys.TimeFrame.Name": self.fieldname_with_utype("ssa:CoordSys.TimeFrame.Name"),
            "ssa:CoordSys.TimeFrame.Ucd": self.fieldname_with_utype("ssa:CoordSys.TimeFrame.Ucd"),
            "ssa:CoordSys.TimeFrame.Zero": self.fieldname_with_utype("ssa:CoordSys.TimeFrame.Zero"),
            "ssa:CoordSys.TimeFrame.RefPos": self.fieldname_with_utype("ssa:CoordSys.TimeFrame.RefPos"),
            "ssa:CoordSys.SpectralFrame.Name": self.fieldname_with_utype("ssa:CoordSys.SpectralFrame.Name"),
            "ssa:CoordSys.SpectralFrame.Ucd": self.fieldname_with_utype("ssa:CoordSys.SpectralFrame.Ucd"),
            "ssa:CoordSys.SpectralFrame.RefPos": self.fieldname_with_utype("ssa:CoordSys.SpectralFrame.RefPos"),
            "ssa:CoordSys.SpectralFrame.Redshift": self.fieldname_with_utype("ssa:CoordSys.SpectralFrame.Redshift"),
            "ssa:CoordSys.RedshiftFrame.Name": self.fieldname_with_utype("ssa:CoordSys.RedshiftFrame.Name"),
            "ssa:CoordSys.RedshiftFrame.DopplerDefinition": self.fieldname_with_utype("ssa:CoordSys.RedshiftFrame.DopplerDefinition"),
            "ssa:CoordSys.RedshiftFrame.RefPos": self.fieldname_with_utype("ssa:CoordSys.RedshiftFrame.RefPos"),
            "ssa:Char.SpatialAxis.Name": self.fieldname_with_utype("ssa:Char.SpatialAxis.Name"),
            "ssa:Char.SpatialAxis.Ucd": self.fieldname_with_utype("ssa:Char.SpatialAxis.Ucd"),
            "ssa:Char.SpatialAxis.Unit": self.fieldname_with_utype("ssa:Char.SpatialAxis.Unit"),
            "ssa:Char.SpatialAxis.Coverage.Location.Value": self.fieldname_with_utype("ssa:Char.SpatialAxis.Coverage.Location.Value"),
            "ssa:Char.SpatialAxis.Coverage.Bounds.Extent": self.fieldname_with_utype("ssa:Char.SpatialAxis.Coverage.Bounds.Extent"),
            "ssa:Char.SpatialAxis.Coverage.Support.Area": self.fieldname_with_utype("ssa:Char.SpatialAxis.Coverage.Support.Area"),
            "ssa:Char.SpatialAxis.Coverage.Support.Extent": self.fieldname_with_utype("ssa:Char.SpatialAxis.Coverage.Support.Extent"),
            "ssa:Char.SpatialAxis.SamplingPrecision.SampleExtent": self.fieldname_with_utype("ssa:Char.SpatialAxis.SamplingPrecision.SampleExtent"),
            "ssa:Char.SpatialAxis.SamplingPrecision.SamplingPrecisionRefVal.FillFactor": self.fieldname_with_utype("ssa:Char.SpatialAxis.SamplingPrecision.SamplingPrecisionRefVal.FillFactor"),
            "ssa:Char.SpatialAxis.Accuracy.StatError": self.fieldname_with_utype("ssa:Char.SpatialAxis.Accuracy.StatError"),
            "ssa:Char.SpatialAxis.Accuracy.SysError": self.fieldname_with_utype("ssa:Char.SpatialAxis.Accuracy.SysError"),
            "ssa:Char.SpatialAxis.Calibration": self.fieldname_with_utype("ssa:Char.SpatialAxis.Calibration"),
            "ssa:Char.SpatialAxis.Resolution": self.fieldname_with_utype("ssa:Char.SpatialAxis.Resolution"),
            "ssa:Char.SpectralAxis.Name": self.fieldname_with_utype("ssa:Char.SpectralAxis.Name"),
            "ssa:Char.SpectralAxis.Ucd": self.fieldname_with_utype("ssa:Char.SpectralAxis.Ucd"),
            "ssa:Char.SpectralAxis.Unit": self.fieldname_with_utype("ssa:Char.SpectralAxis.Unit"),
            "ssa:Char.SpectralAxis.Coverage.Location.Value": self.fieldname_with_utype("ssa:Char.SpectralAxis.Coverage.Location.Value"),
            "ssa:Char.SpectralAxis.Coverage.Bounds.Extent": self.fieldname_with_utype("ssa:Char.SpectralAxis.Coverage.Bounds.Extent"),
            "ssa:Char.SpectralAxis.Coverage.Bounds.Start": self.fieldname_with_utype("ssa:Char.SpectralAxis.Coverage.Bounds.Start"),
            "ssa:Char.SpectralAxis.Coverage.Bounds.Stop": self.fieldname_with_utype("ssa:Char.SpectralAxis.Coverage.Bounds.Stop"),
            "ssa:Char.SpectralAxis.Coverage.Support.Extent": self.fieldname_with_utype("ssa:Char.SpectralAxis.Coverage.Support.Extent"),
            "ssa:Char.SpectralAxis.SamplingPrecision.SampleExtent": self.fieldname_with_utype("ssa:Char.SpectralAxis.SamplingPrecision.SampleExtent"),
            "ssa:Char.SpectralAxis.SamplingPrecision.SamplingPrecisionRefVal.FillFactor": self.fieldname_with_utype("ssa:Char.SpectralAxis.SamplingPrecision.SamplingPrecisionRefVal.FillFactor"),
            "ssa:Char.SpectralAxis.Accuracy.BinSize": self.fieldname_with_utype("ssa:Char.SpectralAxis.Accuracy.BinSize"),
            "ssa:Char.SpectralAxis.Accuracy.StatError": self.fieldname_with_utype("ssa:Char.SpectralAxis.Accuracy.StatError"),
            "ssa:Char.SpectralAxis.Accuracy.SysError": self.fieldname_with_utype("ssa:Char.SpectralAxis.Accuracy.SysError"),
            "ssa:Char.SpectralAxis.Calibration": self.fieldname_with_utype("ssa:Char.SpectralAxis.Calibration"),
            "ssa:Char.SpectralAxis.Resolution": self.fieldname_with_utype("ssa:Char.SpectralAxis.Resolution"),
            "ssa:Char.SpectralAxis.ResPower": self.fieldname_with_utype("ssa:Char.SpectralAxis.ResPower"),
            "ssa:Char.TimeAxis.Name": self.fieldname_with_utype("ssa:Char.TimeAxis.Name"),
            "ssa:Char.TimeAxis.Ucd": self.fieldname_with_utype("ssa:Char.TimeAxis.Ucd"),
            "ssa:Char.TimeAxis.Unit": self.fieldname_with_utype("ssa:Char.TimeAxis.Unit"),
            "ssa:Char.TimeAxis.Coverage.Location.Value": self.fieldname_with_utype("ssa:Char.TimeAxis.Coverage.Location.Value"),
            "ssa:Char.TimeAxis.Coverage.Bounds.Extent": self.fieldname_with_utype("ssa:Char.TimeAxis.Coverage.Bounds.Extent"),
            "ssa:Char.TimeAxis.Coverage.Bounds.Start": self.fieldname_with_utype("ssa:Char.TimeAxis.Coverage.Bounds.Start"),
            "ssa:Char.TimeAxis.Coverage.Bounds.Stop": self.fieldname_with_utype("ssa:Char.TimeAxis.Coverage.Bounds.Stop"),
            "ssa:Char.TimeAxis.Coverage.Support.Extent": self.fieldname_with_utype("ssa:Char.TimeAxis.Coverage.Support.Extent"),
            "ssa:Char.TimeAxis.SamplingPrecision.SampleExtent": self.fieldname_with_utype("ssa:Char.TimeAxis.SamplingPrecision.SampleExtent"),
            "ssa:Char.TimeAxis.SamplingPrecision.SamplingPrecisionRefVal.FillFactor": self.fieldname_with_utype("ssa:Char.TimeAxis.SamplingPrecision.SamplingPrecisionRefVal.FillFactor"),
            "ssa:Char.TimeAxis.Accuracy.BinSize": self.fieldname_with_utype("ssa:Char.TimeAxis.Accuracy.BinSize"),
            "ssa:Char.TimeAxis.Accuracy.StatError": self.fieldname_with_utype("ssa:Char.TimeAxis.Accuracy.StatError"),
            "ssa:Char.TimeAxis.Accuracy.SysError": self.fieldname_with_utype("ssa:Char.TimeAxis.Accuracy.SysError"),
            "ssa:Char.TimeAxis.Calibration": self.fieldname_with_utype("ssa:Char.TimeAxis.Calibration"),
            "ssa:Char.TimeAxis.Resolution": self.fieldname_with_utype("ssa:Char.TimeAxis.Resolution"),
            "ssa:Char.FluxAxis.Name": self.fieldname_with_utype("ssa:Char.FluxAxis.Name"),
            "ssa:Char.FluxAxis.Ucd": self.fieldname_with_utype("ssa:Char.FluxAxis.Ucd"),
            "ssa:Char.FluxAxis.Unit": self.fieldname_with_utype("ssa:Char.FluxAxis.Unit"),
            "ssa:Char.FluxAxis.Accuracy.StatError": self.fieldname_with_utype("ssa:Char.FluxAxis.Accuracy.StatError"),
            "ssa:Char.FluxAxis.Accuracy.SysError": self.fieldname_with_utype("ssa:Char.FluxAxis.Accuracy.SysError"),
            "ssa:Char.FluxAxis.Calibration": self.fieldname_with_utype("ssa:Char.FluxAxis.Calibration"),
            "ssa:Data.SpectralAxis.Value": self.fieldname_with_utype("ssa:Data.SpectralAxis.Value"),
            "ssa:Data.SpectralAxis.Ucd": self.fieldname_with_utype("ssa:Data.SpectralAxis.Ucd"),
            "ssa:Data.SpectralAxis.Unit": self.fieldname_with_utype("ssa:Data.SpectralAxis.Unit"),
            "ssa:Data.SpectralAxis.Accuracy.BinSize": self.fieldname_with_utype("ssa:Data.SpectralAxis.Accuracy.BinSize"),
            "ssa:Data.SpectralAxis.Accuracy.BinLow": self.fieldname_with_utype("ssa:Data.SpectralAxis.Accuracy.BinLow"),
            "ssa:Data.SpectralAxis.Accuracy.BinHigh": self.fieldname_with_utype("ssa:Data.SpectralAxis.Accuracy.BinHigh"),
            "ssa:Data.SpectralAxis.Accuracy.StatError": self.fieldname_with_utype("ssa:Data.SpectralAxis.Accuracy.StatError"),
            "ssa:Data.SpectralAxis.Accuracy.StatErrLow": self.fieldname_with_utype("ssa:Data.SpectralAxis.Accuracy.StatErrLow"),
            "ssa:Data.SpectralAxis.Accuracy.StatErrHigh": self.fieldname_with_utype("ssa:Data.SpectralAxis.Accuracy.StatErrHigh"),
            "ssa:Data.SpectralAxis.Accuracy.SysError": self.fieldname_with_utype("ssa:Data.SpectralAxis.Accuracy.SysError"),
            "ssa:Data.SpectralAxis.Resolution": self.fieldname_with_utype("ssa:Data.SpectralAxis.Resolution"),
            "ssa:Data.FluxAxis.Value": self.fieldname_with_utype("ssa:Data.FluxAxis.Value"),
            "ssa:Data.FluxAxis.Ucd": self.fieldname_with_utype("ssa:Data.FluxAxis.Ucd"),
            "ssa:Data.FluxAxis.Unit": self.fieldname_with_utype("ssa:Data.FluxAxis.Unit"),
            "ssa:Data.FluxAxis.Accuracy.StatError": self.fieldname_with_utype("ssa:Data.FluxAxis.Accuracy.StatError"),
            "ssa:Data.FluxAxis.Accuracy.StatErrLow": self.fieldname_with_utype("ssa:Data.FluxAxis.Accuracy.StatErrLow"),
            "ssa:Data.FluxAxis.Accuracy.StatErrHigh": self.fieldname_with_utype("ssa:Data.FluxAxis.Accuracy.StatErrHigh"),
            "ssa:Data.FluxAxis.Accuracy.SysError": self.fieldname_with_utype("ssa:Data.FluxAxis.Accuracy.SysError"),
            "ssa:Data.FluxAxis.Quality": self.fieldname_with_utype("ssa:Data.FluxAxis.Quality"),
            "ssa:Data.FluxAxis.Quality.n": self.fieldname_with_utype("ssa:Data.FluxAxis.Quality.n"),
            "ssa:Data.TimeAxis.Value": self.fieldname_with_utype("ssa:Data.TimeAxis.Value"),
            "ssa:Data.TimeAxis.Ucd": self.fieldname_with_utype("ssa:Data.TimeAxis.Ucd"),
            "ssa:Data.TimeAxis.Unit": self.fieldname_with_utype("ssa:Data.TimeAxis.Unit"),
            "ssa:Data.TimeAxis.Accuracy.BinSize": self.fieldname_with_utype("ssa:Data.TimeAxis.Accuracy.BinSize"),
            "ssa:Data.TimeAxis.Accuracy.BinLow": self.fieldname_with_utype("ssa:Data.TimeAxis.Accuracy.BinLow"),
            "ssa:Data.TimeAxis.Accuracy.BinHigh": self.fieldname_with_utype("ssa:Data.TimeAxis.Accuracy.BinHigh"),
            "ssa:Data.TimeAxis.Accuracy.StatError": self.fieldname_with_utype("ssa:Data.TimeAxis.Accuracy.StatError"),
            "ssa:Data.TimeAxis.Accuracy.StatErrLow": self.fieldname_with_utype("ssa:Data.TimeAxis.Accuracy.StatErrLow"),
            "ssa:Data.TimeAxis.Accuracy.StatErrHigh": self.fieldname_with_utype("ssa:Data.TimeAxis.Accuracy.StatErrHigh"),
            "ssa:Data.TimeAxis.Accuracy.SysError": self.fieldname_with_utype("ssa:Data.TimeAxis.Accuracy.SysError"),
            "ssa:Data.TimeAxis.Resolution": self.fieldname_with_utype("ssa:Data.TimeAxis.Resolution"),
            "ssa:Data.BackgroundModel.Value": self.fieldname_with_utype("ssa:Data.BackgroundModel.Value"),
            "ssa:Data.BackgroundModel.Ucd": self.fieldname_with_utype("ssa:Data.BackgroundModel.Ucd"),
            "ssa:Data.BackgroundModel.Unit": self.fieldname_with_utype("ssa:Data.BackgroundModel.Unit"),
            "ssa:Data.BackgroundModel.Accuracy.StatError": self.fieldname_with_utype("ssa:Data.BackgroundModel.Accuracy.StatError"),
            "ssa:Data.BackgroundModel.Accuracy.StatErrLow": self.fieldname_with_utype("ssa:Data.BackgroundModel.Accuracy.StatErrLow"),
            "ssa:Data.BackgroundModel.Accuracy.StatErrHigh": self.fieldname_with_utype("ssa:Data.BackgroundModel.Accuracy.StatErrHigh"),
            "ssa:Data.BackgroundModel.Accuracy.SysError": self.fieldname_with_utype("ssa:Data.BackgroundModel.Accuracy.SysError"),
            "ssa:Data.BackgroundModel.Quality": self.fieldname_with_utype("ssa:Data.BackgroundModel.Quality")

        }
        self._recnames = { "title":   self._ssacols["ssa:DataID.Title"],
                           # RA and Dec are not separately specified
                           "pos":      self._ssacols["ssa:Target.Pos"],
                           "instr":   self._ssacols["ssa:DataID.Instrument"],
                           # This does not exist specifically in SSA but the closest is
                           "dateobs": self._ssacols["ssa:DataID.Date"],
                           "format":  self._ssacols["ssa:Access.Format"],
                           "acref":   self._ssacols["ssa:Access.Reference"]
                           }


class SSAQuery(query.DALQuery):
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

    In addition to the attributes described below, search parameters can be 
    set generically by name via dict semantic.
    The class attribute, ``std_parameters``, list the parameters 
    defined by the SSA standard.  

    The typical function for submitting the query is ``execute()``; however, 
    alternate execute functions provide the response in different forms, 
    allowing the caller to take greater control of the result processing.  

    """

    RESULTS_CLASS = SSAResults
    
    std_parameters = [ "REQUEST", "VERSION", "POS", "SIZE", "BAND", "TIME", 
                       "FORMAT", "APERTURE", "SPECRP", "SPATRES", "TIMERES", 
                       "SNR", "REDSHIFT", "VARAMPL", "TARGETNAME", 
                       "TARGETCLASS", "FLUXCALIB", "WAVECALIB", "PUBID", 
                       "CREATORID", "COLLECTION", "TOP", "MAXREC", "MTIME", 
                       "COMPRESS", "RUNID" ]

    def __init__(self, baseurl,  version="1.0", request="queryData"):
        """
        initialize the query object with a baseurl and request type
        """
        super(SSAQuery, self).__init__(baseurl, "ssa", version)
        self["REQUEST"] = request
        
    @property
    def pos(self):
        """
        the position (POS) constraint as a 2-element tuple denoting RA and 
        declination in decimal degrees.  This defaults to None.
        """
        return self.get("POS")
    @pos.setter
    def pos(self, pair):
        # do a check on the input
        if (isinstance(pair, list)):
            pair = tuple(pair)
        if (isinstance(pair, tuple)):
            if len(pair) != 2:
                raise ValueError("Wrong number of elements in pos list: " + 
                                 str(pair))
            if (not isinstance(pair[0], numbers.Number) or 
                not isinstance(pair[1], numbers.Number)):
                raise ValueError("Wrong type of elements in pos list: " + 
                                 str(pair))
        else:
            raise ValueError("pos not a 2-element sequence")

        if pair[1] > 90.0 or pair[1] < -90.0:
            raise ValueError("pos declination out-of-range: " + str(pair[1]))

        while pair[0] < 0:
            pair = (pair[0]+360.0, pair[1])
        while pair[0] >= 360.0:
            pair = (pair[0]-360.0, pair[1])


        self["POS"] = pair
    @pos.deleter
    def pos(self):
        del self['POS']

    @property
    def ra(self):
        """
        the right ascension part of the position constraint (default: None).
        If this is set but dec has not been set yet, dec will be set to 0.0.
        """
        if not self.pos: return None
        return self.pos[0]
    @ra.setter
    def ra(self, val):
        if not self.pos: self.pos = (0.0, 0.0)
        self.pos = (val, self.pos[1])

    @property
    def dec(self):
        """
        the declination part of the position constraint (default: None).
        If this is set but ra has not been set yet, ra will be set to 0.0.
        """
        if not self.pos: return None
        return self.pos[1]
    @dec.setter
    def dec(self, val):
        if not self.pos: self.pos = (0.0, 0.0)
        self.pos = (self.pos[0], val)

    @property
    def size(self):
        """
        the diameter of the search region specified in decimal degrees
        """
        return self.get("SIZE")
    @size.setter
    def size(self, val):
        if val is not None:
            if not isinstance(val, numbers.Number):
                raise ValueError("size constraint is not a number")
            if val <= 0.0 or val > 180.0:
                raise ValueError("size constraint out-of-range: " + str(val))

        self["SIZE"] = val
    @size.deleter
    def size(self):
        del self["SIZE"]

    @property
    def band(self):
        """
        the spectral bandpass given in a range-list format in units of 
        meters

        Examples of proper format include:

        =========================  =====================================
        0.20/0.21.5                a wavelength range that includes 21cm
        2.7E-7/0.13                a bandpass from optical to radio
        =========================  =====================================
        """
        return self.get("BAND")
    @band.setter
    def band(self, val):
        self["BAND"] = val
    @band.deleter
    def band(self):
        del self["BAND"]

    @property
    def time(self):
        """
        the time coverage given in a range-list format using a restricted
        subset of ISO 8601.

        Examples of proper format include:

        =========================  =====================================
        2003/2009                  covers years 2003-09, inclusive
        2003-02/2003-04            covers Feb. through April in 2003
        2003-05-02/2010-09-21      covers a range of days 
        2001-05-02T12:21:30/2010   provides second resolution
        =========================  =====================================
        """
        return self.get("TIME")
    @time.setter
    def time(self, val):
        # check the format:
        # YYYY-MM-DD, YYYY-MM, YYYY, YYYY-MM-DDTHH:MM:SS
        if "/" in val:
            dates = val.split("/")
        else:
            dates = [val]
        for _ in dates:
            if not(re.match("\d{4}$|\d{4}-\d{2}$|\d{4}-\d{2}-\d{2}$|" +
                             "\d{4}-\d{2}-\d{2}T\d{2}\:\d{2}\:\d{2}$"), date):
                raise ValueError("time format not valid: " + val)

        self["TIME"] = val
    @time.deleter
    def time(self):
        del self["TIME"]

    @property
    def format(self):
        """
        the desired format of the images to be returned.  This will be in the 
        form of a commna-separated list of MIME-types or one of the following 
        special values. 

        ========= =======================================================
        **value** **meaning**
        all       all formats available
        compliant any SSA data model compliant format
        native    the native project specific format for the spectrum
        graphic   any of the graphics formats: JPEG, PNG, GIF
        votable   the SSA VOTable format
        fits      the SSA-compliant FITS format
        xml       the SSA native XML serialization
        metadata  no images requested; only an empty table with fields
                  properly specified
        ========= =======================================================

        """
        return self.get("FORMAT")
    @format.setter
    def format(self, val):
        # check values
        formats = val.split(",")
        for f in formats:
            f = f.lower()
            if not query.is_mime_type(f) and \
               f not in ["all", "compliant", "native", "graphic", "votable", 
                         "fits", "xml", "metadata"]: 
                raise ValueError("format type not valid: " + f)

        self["FORMAT"] = val
    @format.deleter
    def format(self):
        del self["FORMAT"]


class SSAService(query.DALService):
    """
    a representation of an SSA service
    """

    QUERY_CLASS = SSAQuery

    def __init__(self, baseurl, resmeta=None, version="1.0"):
        """
        instantiate an SSA service

        Parameters
        ----------
        baseurl : str
           the base URL for submitting search queries to the service.
        resmeta : dict
           an optional dictionary of properties about the service
        """
        super(SSAService, self).__init__(baseurl, "ssa", version, resmeta)

    def search(self, pos, size, format='all', **keywords):
        """
        submit a simple SSA query to this service with the given constraints.  

        This method is provided for a simple but typical SSA queries.  For 
        more complex queries, one should create an SSAQuery object via 
        create_query()

        Parameters
        ----------
        pos : 2-element tuple of floats
           a 2-element tuple giving the ICRS RA and Dec of the 
           center of the search region in decimal degrees
        size : float
           a floating point number giving the diameter of the circular region
           in decimal degrees around pos in which to search for spectra.  
        format : str
           the spectral format(s) of interest.  "all" (default) 
           indicates all available formats; "graphic" indicates
           graphical spectra (e.g. jpeg, png, gif; not FITS); 
           "metadata" indicates that no spectra should be 
           returned--only an empty table with complete metadata.
        **keywords :   
           additional parameters can be given via arbitrary 
           keyword arguments.  These can be either standard 
           parameters (with names drown from the 
           ``SSAQuery.std_parameters`` list) or paramters
           custom to the service.  Where there is overlap 
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
        q = self.create_query(pos, size, format, **keywords)
        return q.execute()

    def create_query(self, pos=None, size=None, format=None, **keywords):
        """
        create a query object that constraints can be added to and then 
        executed.  The input arguments will initialize the query with the 
        given values.

        Parameters
        ----------
        pos : 2-element tuple of floats
           a 2-element tuple giving the ICRS RA and Dec of the 
           center of the search region in decimal degrees
        size : float
           a floating point number giving the diameter of the circular region
           in decimal degrees around pos in which to search for spectra.  
        format : str
           the image format(s) of interest.  "all" indicates 
           all available formats; "graphic" indicates
           graphical images (e.g. jpeg, png, gif; not FITS); 
           "metadata" indicates that no images should be 
           returned--only an empty table with complete metadata.
        **keywords : 
           additional parameters can be given via arbitrary 
           keyword arguments.  These can be either standard 
           parameters (with names drown from the 
           ``SSAQuery.std_parameters`` list) or paramters
           custom to the service.  Where there is overlap 
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
        q = self.QUERY_CLASS(self.baseurl, self.version)
        if pos is not None: q.pos = pos
        if size is not None: q.size = size
        if format: q.format = format

        q.update(keywords)

        return q
