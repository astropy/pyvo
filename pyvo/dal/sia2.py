# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
A module for searching for images in a remote archive.

A Simple Image Access (SIA) service allows a client to search for
images in an archive whose field of view overlaps with a given
region on the sky. The region can be a circle, a range or an arbitrary polyon.
The service responds to a search query
with a table in which each row represents an image that is available
for download.  The columns provide metadata describing each image and
one column in particular provides the image's download URL (also
called the *access reference*, or *acref*).  Some SIA services act as
a cut-out service; in this case, the query result is a table of images
whose field of view matches the requested region and which will be
created when accessed via the download URL.

This module provides an interface for accessing an SIA v2 service.  It is
implemented as a specialization of the DAL Query interface.

The ``search()`` function support the simplest and most common types
of queries, returning an SIAResults instance as its results which
represents the matching images from the archive.  The SIAResults
supports access to and iterations over the individual records; these
are provided as SIARecord instances, which give easy access to key
metadata in the response, such as the position of the image's center,
the image format, the size and shape of the image, and its download
URL.

The ``SIAService`` class can represent a specific service available at a URL
endpoint.
"""
import re
import copy
import dateutil.parser

from pyvo.io.vosi.vodataservice import TableParam

from astropy.coordinates import SkyCoord
from astropy.time import Time
from astropy.units import Quantity
from astropy import units as u

from .query import DALResults, DALQuery, DALService, Record
from .mimetype import mime2extension
from .adhoc import DatalinkResultsMixin, DatalinkRecordMixin, SodaRecordMixin
from .vosi import AvailabilityMixin, CapabilityMixin

from .. import samp

__all__ = ["search", "SIAService", "SIAQuery", "SIAResults", "ObsCoreRecord"]

SIA2_STANDARD_ID = 'ivo://ivoa.net/std/SIA#query-2.0'

# to be moved to ObsCore
POLARIZATION_STATES = ['I', 'Q', 'U', 'V', 'RR', 'LL', 'RL', 'LR',
                       'XX', 'YY', 'XY', 'YX', 'POLI', 'POLA']
CALIBRATION_LEVELS = [0, 1, 2, 3, 4]

def search(url, pos=None, band=None, time=None, pol=None,
                 field_of_view=None, spatial_resolution=None,
                 spectral_resolving_power=None, exptime=None,
                 timeres=None, id=None, facility=None, collection=None,
                 instrument=None, data_type=None, calib_level=None,
                 target=None, res_format=None, maxrec=None,
                 session=None):
    """
    submit a simple SIA query to a SIAv2 compatible service

    See pyvo.dal.sia.SIAv2Query.__init__ for a description of the parameters
    and returned types

    """
    service = SIAService(url)
    # TODO - check capabilities of the service for SIAv2 standard ID
    return service.search(pos=pos, band=band,
                          time=time, pol=pol,
                          field_of_view=field_of_view,
                          spatial_resolution=spatial_resolution,
                          spectral_resolving_power=spectral_resolving_power,
                          exptime=exptime, timeres=timeres, id=id,
                          facility=facility, collection=collection,
                          instrument=instrument, data_type=data_type,
                          calib_level=calib_level, target=target,
                          res_format=res_format, maxrec=maxrec,
                          session=session)

def _tolist(value):
    # return value as a list - is there something in Python to do that?
    if isinstance(value, list):
        return value
    return [value]

class SIAService(DALService, AvailabilityMixin, CapabilityMixin):
    """
    a representation of an SIA2 service
    """

    def __init__(self, baseurl, session=None):
        """
        instantiate an SIA service

        Parameters
        ----------
        baseurl : str
           the base URL for submitting search queries to the service.
        session : object
           optional session to use for network requests
        """
        super().__init__(baseurl, session=session)

        # Check if the session has an update_from_capabilities attribute.
        # This means that the session is aware of IVOA capabilities,
        # and can use this information in processing network requests.
        # One such usecase for this is auth.
        if hasattr(self._session, 'update_from_capabilities'):
            self._session.update_from_capabilities(self.capabilities)

        self.query_ep = None # service query end point
        for cap in self.capabilities:
            # assumes that the access URL is the same regardless of the
            # authentication method except BasicAA which is not supported
            # in pyvo. So pick any access url as long as it's not
            if cap.standardid == SIA2_STANDARD_ID:
                for interface in cap.interfaces:
                    if interface.accessurls and not \
                        [m for m in interface.securitymethods if
                         m.standardid != 'ivo://ivoa.net/sso#BasicAA']:
                        self.query_ep = interface.accessurls[0].content
                        break

    def _get_metadata(self):
        """
        the metadata resource element
        """
        if not hasattr(self, "_metadata"):
            query = self.create_query(format='metadata')
            metadata = query.execute_votable()

            setattr(self, "_metadata", metadata)
            try:
                setattr(self, "_metadata_resource", metadata.resources[0])
            except IndexError:
                setattr(self, "_metadata_resource", None)

    @property
    def description(self):
        """
        the service description.
        """
        self._get_metadata()

        try:
            return getattr(self, "_metadata", None).description
        except AttributeError:
            return None

    @property
    def params(self):
        """
        the service parameters.
        """
        self._get_metadata()

        try:
            return getattr(self, "_metadata_resource", None).params
        except AttributeError:
            return None

    @property
    def columns(self):
        """
        the available columns on this service
        """
        self._get_metadata()
        fields = getattr(self, '_metadata', None).get_first_table().fields

        try:
            return [
                TableParam.from_field(field) for field in fields]
        except AttributeError:
            return []

    def search(self, pos=None, band=None, time=None, pol=None,
                 field_of_view=None, spatial_resolution=None,
                 spectral_resolving_power=None, exptime=None,
                 timeres=None, id=None, facility=None, collection=None,
                 instrument=None, data_type=None, calib_level=None,
                 target=None, res_format=None, maxrec=None,
                 session=None):
        """
        Performs a SIAv2 search against a SIAv2 service

        See pyvo.dal.sia.SIAv2Query.__init__ for a description of the
        parameters and returned types

        """
        return SIAQuery(self.query_ep, pos=pos, band=band,
                        time=time, pol=pol,
                        field_of_view=field_of_view,
                        spatial_resolution=spatial_resolution,
                        spectral_resolving_power=spectral_resolving_power,
                        exptime=exptime, timeres=timeres, id=id,
                        facility=facility, collection=collection,
                        instrument=instrument, data_type=data_type,
                        calib_level=calib_level, target=target,
                        res_format=res_format, maxrec=maxrec,
                        session=session).execute()

    def describe(self):
        print(self.description)
        print()


class SIAQuery(DALQuery):
    """
    a class very similar to :py:attr:`~pyvo.dal.query.SIAQuery` class but
    used to interact with SIAv2 services.
    """

    def __init__(self, url, pos=None, band=None, time=None, pol=None,
                 field_of_view=None, spatial_resolution=None,
                 spectral_resolving_power=None, exptime=None,
                 timeres=None, id=None, facility=None, collection=None,
                 instrument=None, data_type=None, calib_level=None,
                 target=None, res_format=None, maxrec=None,
                 session=None):
        """
        initialize the query object with a url and the given parameters
        Note: The majority of the attributes represent constraints used to
        query the SIA service and are represented through lists. Multiple value
        attributes are OR-ed in the query, however the values of different
        attributes are AND-ed. Intervals are represented with tuples and
        open-ended intervals should be expressed with float("-inf") or
        float("inf"). Eg. For all values less than or equal to 600 use
        (float(-inf), 600)

        Parameters
        ----------
        url : str
            the query end point of the SIA service
        pos : tuple or list of tuple
            the positional region(s) to be searched for data. Each region can
            be expressed as a tuple representing a CIRCLE, RANGE or POLYGON as
            follows:
            (`~astropy.coordinates.SkyCoord`, radius) - for CIRCLE. angle units
            required for radius
            (long1, long2, lat1, lat2) - for RANGE (angle units required)
            (`~astropy.coordinates.SkyCoord`, at least three times) for POLYGON
        band : scalar, tuple(interval) or list of tuples
            energy units required
            the energy interval(s) to be searched for data.
        time: `~astropy.time.Time` or list of `~astropy.time.Time`
            the time interval(s) to be searched for data.
        pol: TBD enum or list of enums
            the polarization state(s) to be searched for data.
        field_of_view: tuple or list of tuples
            angle units required
            the range(s) of field of view (size) to be searched for data
        spatial_resolution: tuple or list of tuples
            angle units required
            the range(s) of spatial resolution to be searched for data
        spectral_resolving_power: tuple or list of tuples
            the range(s) of spectral resolving power to be searched for data
        exptime: tuple or list of tuples
        time units required
            the range(s) of exposure times to be searched for data
        timeres: tuple of list of tuples
            time units required
            the range(s) of temporal resolution to be searched for data
        id: str or list of str
            specifies the identifier of dataset(s)
        collection: str or list of str
            name of the collection that the data belongs to
        facility: str or list of str
            specifies the name of the facility (usually telescope) where
            the data was acquired.
        instrument: str or list of str
            specifies the name of the instrument with which the data was
            acquired.
        data_type: 'image'|'cube'
            specifies the type of the data
        calib_level: 0, 1 - raw data, 2 - calibrated data,
            3 - highly processed data
            specifies the calibration level of the data. Can be a single value
            or a list of values
        target: str or list of str
            specifies the name of the target (e.g. the intention of the
            original science program or observation)
        res_format : str or list of strings
            specifies response format(s).
        max_records: int
            allows the client to limit the number or records in the response
        session : object
           optional session to use for network requests
        Returns
        -------
        SIAResults
            a container holding a table of matching image records. Records are
            represented in IVOA ObsCore format

        Raises
        ------
        DALServiceError
            for errors connecting to or communicating with the service
        DALQueryError
            if the service responds with an error,
            including a query syntax error.

        See Also
        --------
        SIAResults
        pyvo.dal.query.DALServiceError
        pyvo.dal.query.DALQueryError

        """
        super().__init__(url, session=session)

        self._pos = []
        for pp in _tolist(pos):
            self.pos_append(pp)

        self._band = []
        for bb in _tolist(band):
            self.band_append(bb)

        self._time = []
        for tt in _tolist(time):
            self.time_append(tt)

        self._pol = []
        for pp in _tolist(pol):
            self.pol_append(pp)

        self._fov = []
        for ff in _tolist(field_of_view):
            self.field_of_view_append(ff)

        self._spatres = []
        for sp in _tolist(spatial_resolution):
            self.spatial_resolution_append(sp)

        self._specrp = []
        for sr in _tolist(spectral_resolving_power):
            self.spectral_resolving_power_append(sr)

        self._exptime = []
        for et in _tolist(exptime):
            self.exptime_append(et)

        self._timeres = []
        for tr in _tolist(timeres):
            self.timeres_append(tr)

        self._id = []
        for ii in _tolist(id):
            self.id_append(ii)

        self._facility = []
        for ff in _tolist(facility):
            self.facility_append(ff)

        self._collection = []
        for col in _tolist(collection):
            self.collection_append(col)

        self._instrument = []
        for inst in _tolist(instrument):
            self.instrument_append(inst)

        self._dptype = []
        for dt in _tolist(data_type):
            self.data_type_append(dt)

        self._calib_level = []
        for cal in _tolist(calib_level):
            self.calib_level_append(cal)

        self._target = []
        for tt in _tolist(target):
            self.target_append(tt)

        self._res_format = []
        for rf in _tolist(res_format):
            self.res_format_append(rf)

        self.maxrec = maxrec

    @property
    def pos(self):
        """
        Returns a copy of the list of positions to be used as constraints
        """
        return copy.deepcopy(self._pos)

    def pos_append(self, val):
        if not val:
            return
        if not isinstance(val, tuple):
            raise AttributeError(
                'Position value {} must be a tuple'.format(val))
        if not val or len(val) < 2:
            raise AttributeError(
                'Too few tuple elements ({len}) for pos to speficy a '
                'CIRCLE, RANGE or POLYGON'.format(len=len(val)))
        if len(val) == 2:
            # must be a circle with coord and radius
            try:
                pos = 'CIRCLE {ra} {dec} {rad}'.format(
                    ra=val[0].icrs.ra.deg, dec=val[0].icrs.dec.deg,
                    rad=val[1].to(u.deg).value)
            except Exception as e:
                raise AttributeError(
                    'Could not format the CIRCLE position {pos} ({e})'.
                    format(pos=val, e=str(e)))
        elif len(val) == 4 and not isinstance(val[0], SkyCoord):
            # assume range
            pos = 'RANGE {long1} {long2} {lat1} {lat2}'.format(
                long1=val[0], long2=val[1], lat1=val[2], lat2=val[3])
        else:
            # asume polygon
            pos = 'POLYGON'
            try:
                for pt in val:
                    pos += ' {ra} {dec}'.format(ra=pt.icrs.ra.deg,
                                                dec=pt.icrs.dec.deg)
            except Exception as e:
                raise ValueError(
                    'Could not format the POLYGON position {pos} '
                    '({e})'.format(pos=val, e=str(e)))
        self._pos.append(val)
        if 'POS' in self.keys():
            self['POS'].append(pos)
        else:
            self['POS'] = [pos]

    def pos_del(self, index):
        del self._pos[index]
        del self['POS'][index]

    @property
    def band(self):
        """
        Returns a copy of the list of energy or energy bands to be used as
        constraints
        """
        return copy.deepcopy(self._band)

    def band_append(self, val):
        if not val:
            return
        if isinstance(val, tuple):
            band = '{} {}'.format(val[0].to(u.meter).value,
                                  val[1].to(u.meter).value)
        else:
            band = val.to(u.meter).value
        if 'BAND' in self.keys():
            self['BAND'].append(band)
        else:
            self['BAND'] = [band]
        self._band.append(val)

    def band_del(self, index):
        del self['BAND'][index]
        del self._band[index]

    @property
    def time(self):
        """
        Returns a list of time or time intervals to be used as constraints
        """
        return copy.deepcopy(self._time)

    def time_append(self, val):
        if not val:
            return
        if isinstance(val, tuple):
            time = '{} {}'.format(val[0].mjd,
                                  val[1].mjd)
        else:
            time = val.mjd
        if 'TIME' in self.keys():
            self['TIME'].append(time)
        else:
            self['TIME'] = [time]
        self._time.append(val)

    def time_del(self, index):
        del self['TIME'][index]
        del self._time[index]

    @property
    def pol(self):
        """
        Returns copy of a list of polarization states to be used as constraints
        """
        return copy.copy(self._pol)

    def pol_append(self, val):
        if not val:
            return
        if val not in POLARIZATION_STATES:
            raise ValueError('Polarization state {} not in valid set: {}'.
                             format(val, ', '.join(POLARIZATION_STATES)))
        self._pol.append(val)
        if 'POL' not in self.keys():
            self['POL'] = [val]
        else:
            self['POL'].append(val)

    def polarization_del(self, index):
        del self['POL'][index]
        del self._pol[index]

    @property
    def field_of_view(self):
        """
        Returns a copy of the list of field of views to be used as constraints
        """
        return copy.copy(self._fov)

    def field_of_view_append(self, val):
        if not val:
            return
        if not isinstance(val, tuple) or len(val) != 2:
            raise AttributeError(
                'Field of view {} not a size 2 tuple'.format(val))
        fval = '{} {}'.format(val[0].to(u.deg).value, val[1].to(u.deg).value)
        self._fov.append(val)
        if 'FOV' not in self.keys():
            self['FOV'] = [fval]
        else:
            self['FOV'].append(fval)

    def field_of_view_del(self, index):
        del self['FOV'][index]
        del self._fov[index]

    @property
    def spatial_resolution(self):
        """
        Returns a copy of the list of spectral resolutions to be used as
        constraints
        """
        return copy.copy(self._spatres)

    def spatial_resolution_append(self, val):
        if not val:
            return
        if not isinstance(val, tuple) or len(val) != 2:
            raise AttributeError(
                'Spatial resolution {} not a size 2 tuple'.format(val))
        fval = '{} {}'.format(val[0].to(u.deg).value, val[1].to(u.deg).value)
        self._spatres.append(val)
        if 'SPATRES' not in self.keys():
            self['SPATRES'] = [fval]
        else:
            self['SPATRES'].append(fval)

    def spatial_resolution_del(self, index):
        del self['SPATRES'][index]
        del self._spatres[index]

    @property
    def spectral_resolving_power(self):
        """
        Returns a copy of the list of spectral resolving power ranges to be
        used as constraints
        """
        return copy.copy(self._specrp)

    def spectral_resolving_power_append(self, val):
        if not val:
            return
        if not isinstance(val, tuple) or len(val) != 2:
            raise AttributeError(
                'Spectral resolving power {} not a size 2 tuple'.format(val))
        fval = '{} {}'.format(val[0], val[1])
        self._specrp.append(val)
        if 'SPECRP' not in self.keys():
            self['SPECRP'] = [fval]
        else:
            self['SPECRP'].append(fval)

    def spectral_resolving_power_del(self, index):
        del self['SPECRP'][index]
        del self._specrp[index]

    @property
    def exptime(self):
        """
        Returns a copy of the list of exposure time ranges to be used as
        constraints
        """
        return copy.copy(self._exptime)

    def exptime_append(self, val):
        if not val:
            return
        if not isinstance(val, tuple) or len(val) != 2:
            raise AttributeError(
                'Exposure time {} not a size 2 tuple'.format(val))
        fval = '{} {}'.format(val[0].to(u.second).value,
                              val[1].to(u.second).value)
        self._exptime.append(val)
        if 'EXPTIME' not in self.keys():
            self['EXPTIME'] = [fval]
        else:
            self['EXPTIME'].append(fval)

    def exptime_del(self, index):
        del self['EXPTIME'][index]
        del self._exptime[index]

    @property
    def timeres(self):
        """
        Returns a copy of the list of time resolution ranges to be used as
        constraints
        """
        return copy.copy(self._timeres)

    def timeres_append(self, val):
        if not val:
            return
        if not isinstance(val, tuple) or len(val) != 2:
            raise AttributeError(
                'Time resolution {} not a size 2 tuple'.format(val))
        fval = '{} {}'.format(val[0].to(u.second).value,
                              val[1].to(u.second).value)
        self._timeres.append(val)
        if 'TIMERES' not in self.keys():
            self['TIMERES'] = [fval]
        else:
            self['TIMERES'].append(fval)

    def timeres_del(self, index):
        del self['TIMERES'][index]
        del self._timeres[index]

    @property
    def id(self):
        """
        Returns a copy of the list of ids to be used as constraints
        """
        return copy.copy(self._id)

    def id_append(self, val):
        if not val:
            return
        self._id.append(val)
        if 'ID' not in self.keys():
            self['ID'] = [val]
        else:
            self['ID'].append(val)

    def id_del(self, index):
        del self['ID'][index]
        del self._id[index]

    @property
    def facility(self):
        """
        Returns a copy of the list of facilities to be used as constraints
        """
        return copy.copy(self._facility)

    def facility_append(self, val):
        if not val:
            return
        self._facility.append(val)
        if 'FACILITY' not in self.keys():
            self['FACILITY'] = [val]
        else:
            self['FACILITY'].append(val)

    def facility_del(self, index):
        del self['FACILITY'][index]
        del self._facility[index]

    @property
    def collection(self):
        """
        Returns a copy of the list of collections to be used as constraints
        """
        return copy.copy(self._collection)

    def collection_append(self, val):
        if not val:
            return
        self._collection.append(val)
        if 'COLLECTION' not in self.keys():
            self['COLLECTION'] = [val]
        else:
            self['COLLECTION'].append(val)

    def collection_del(self, index):
        del self['COLLECTION'][index]
        del self._collection[index]

    @property
    def instrument(self):
        """
        Returns a copy of the list of instruments to be used as constraints
        """
        return copy.copy(self._instrument)

    def instrument_append(self, val):
        if not val:
            return
        self._instrument.append(val)
        if 'INSTRUMENT' not in self.keys():
            self['INSTRUMENT'] = [val]
        else:
            self['INSTRUMENT'].append(val)

    def instrument_del(self, index):
        del self['INSTRUMENT'][index]
        del self._instrument[index]

    @property
    def data_type(self):
        """
        Returns a copy of the list of data types to be used as constraints
        """
        return copy.copy(self._dptype)

    def data_type_append(self, val):
        if not val:
            return
        self._dptype.append(val)
        if 'DPTYPE' not in self.keys():
            self['DPTYPE'] = [val]
        else:
            self['DPTYPE'].append(val)

    def data_type_del(self, index):
        del self['DPTYPE'][index]
        del self._dptype[index]

    @property
    def calib_level(self):
        """
        Returns a copy of the list of calibration levels to be used
        as constraints
        """
        return copy.copy(self._calib_level)

    def calib_level_append(self, val):
        if not val:
            return
        if val not in CALIBRATION_LEVELS:
            raise ValueError('Calibration {} not in valid range: {}'.
                             format(val, ','.join(CALIBRATION_LEVELS)))
        self._calib_level.append(val)
        if 'CALIB' not in self.keys():
            self['CALIB'] = [val]
        else:
            self['CALIB'].append(val)

    def calibration_del(self, index):
        del self['CALIB'][index]
        del self._calib_level[index]

    @property
    def target(self):
        """
        Returns a copy of the list of targets to be used as constraints
        """
        return copy.copy(self._target)

    def target_append(self, val):
        if not val:
            return
        self._target.append(val)
        if 'TARGET' not in self.keys():
            self['TARGET'] = [val]
        else:
            self['TARGET'].append(val)

    def target_del(self, index):
        del self['TARGET'][index]
        del self._target[index]

    @property
    def res_format(self):
        """
        Returns a copy of the list of result formats for the response
        """
        return copy.copy(self._res_format)

    def res_format_append(self, val):
        if not val:
            return
        self._res_format.append(val)
        if 'FORMAT' not in self.keys():
            self['FORMAT'] = [val]
        else:
            self['FORMAT'].append(val)

    def res_format_del(self, index):
        del self['FORMAT'][index]
        del self._res_format[index]

    @property
    def maxrec(self):
        return self._maxrec

    @maxrec.setter
    def maxrec(self, val):
        if not isinstance(val, int) and val > 0:
            raise ValueError('maxrec {} must be positive int'.format(val))
        self._maxrec = val

    def execute(self):
        """
        submit the query and return the results as a SIAResults instance

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
        return SIAResults(self.execute_votable(), url=self.queryurl, session=self._session)


class SIAResults(DatalinkResultsMixin, DALResults):
    """
    The list of matching images resulting from an image (SIA) query.
    Each record contains a set of metadata that describes an available
    image matching the query constraints.  The number of records in
    the results is available via the :py:attr:`nrecs` attribute or by
    passing it to the Python built-in ``len()`` function.

    This class supports iterable semantics; thus,
    individual records (in the form of
    :py:class:`~pyvo.dal.sia2.ObsCoreRecord` instances) are typically
    accessed by iterating over an ``SIAResults`` instance.

    >>> results = pyvo.imagesearch(url, pos=[12.24, -13.1], size=0.1)
    >>> for image in results:
    ...     print("{0}: {1}".format(image.title, title.getdataurl()))

    Alternatively, records can be accessed randomly via
    :py:meth:`getrecord` or through a Python Database API (v2)
    Cursor (via :py:meth:`~pyvo.dal.query.DALResults.cursor`).
    Column-based data access is possible via the
    :py:meth:`~pyvo.dal.query.DALResults.getcolumn` method.

    ``SIAResults`` is essentially a wrapper around an Astropy
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

    ``SIAResults`` supports the array item operator ``[...]`` in a
    read-only context.  When the argument is numerical, the result
    is an
    :py:class:`~pyvo.dal.sia2.ObsCoreRecord` instance, representing the
    record at the position given by the numerical index.  If the
    argument is a string, it is interpreted as the name of a column,
    and the data from the column matching that name is returned as
    a Numpy array.
    """

    def getrecord(self, index):
        """
        return a representation of a sia result record that follows
        dictionary semantics. The keys of the dictionary are those returned by
        this instance's fieldnames attribute. The returned record has
        additional image-specific properties

        Parameters
        ----------
        index : int
           the integer index of the desired record where 0 returns the first
           record

        Returns
        -------
        ObsCoreRecord
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
        return ObsCoreRecord(self, index, session=self._session)


class ObsCoreRecord(SodaRecordMixin, DatalinkRecordMixin, Record):
    """
    a dictionary-like container for data in a record from the results of an
    image (SIAv2) search, describing an available image in ObsCore format.

    The commonly accessed metadata which are stadardized by the SIA
    protocol are available as attributes.  If the metadatum accessible
    via an attribute is not available, the value of that attribute
    will be None.  All metadata, including non-standard metadata, are
    acessible via the ``get(`` *key* ``)`` function (or the [*key*]
    operator) where *key* is table column name.
    """

    ###          OBSERVATION INFO
    @property
    def dataproduct_type(self):
        return self['dataproduct_type'].decode('utf-8')

    @property
    def dataproduct_subtype(self):
        if 'dataproduct_subtype' in self.keys():
            return self['dataproduct_subtype'].decode('utf-8')
        return None

    @property
    def calib_level(self):
        return int(self['calib_level'])

    ###          TARGET INFO
    @property
    def target_name(self):
        return self['target_name'].decode('utf-8')

    @property
    def target_class(self):
        if 'target_class' in self.keys():
            return self['target_class'].decode('utf-8')
        return None

    ###          DATA DESCRIPTION
    @property
    def obs_id(self):
        return self['obs_id'].decode('utf-8')

    @property
    def obs_title(self):
        if 'obs_title' in self.keys():
            return self['obs_title'].decode('utf-8')
        return None

    @property
    def obs_collection(self):
        return self['obs_collection'].decode('utf-8')

    @property
    def obs_create_date(self):
        if 'obs_create_date' in self.keys():
            return dateutil.parser.isoparse(self['obs_create_date'])
        return None

    @property
    def obs_creator_name(self):
        if 'obs_creator_name' in self.keys():
            return self['obs_creator_name'].decode('utf-8')
        return None

    @property
    def obs_creator_did(self):
        if 'obs_creator_did' in self.keys():
            return self['obs_creator_did'].decode('utf-8')
        return None

    ##         CURATION INFORMATION
    @property
    def obs_release_date(self):
        if 'obs_release_date' in self.keys():
            return dateutil.parser.isoparse(self['obs_release_date'])
        return None

    @property
    def obs_publisher_id(self):
        return self['obs_publisher_id'].decode('utf-8')

    @property
    def publisher_id(self):
        if 'publisher_id' in self.keys():
            return self['publisher_id'].decode('utf-8')
        return None

    @property
    def bib_reference(self):
        if 'bib_reference' in self.keys():
            return self['bib_reference'].decode('utf-8')
        return None

    @property
    def data_rights(self):
        if 'data_rights' in self.keys():
            return self['data_rights'].decode('utf-8')

    ##           ACCESS INFORMATION
    @property
    def access_url(self):
        return self['access_url'].decode('utf-8')

    @property
    def access_format(self):
        return self['access_format'].decode('utf-8')

    @property
    def access_estsize(self):
        return int(self['access_estsize'].decode('utf-8'))

    ##           SPATIAL CHARACTERISATION

    ##           TIME CHARACTERISATION

    ##           SPECTRAL CHARACTERISATION

    ##           OBSERVABLE AXIS

    ##           POLARIZATION CHARACTERISATION

    ##           PROVENANCE