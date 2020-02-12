# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Datalink classes and mixins
"""
import numpy as np
import copy
import warnings
import dateutil
from datetime import datetime

from .query import DALResults, DALQuery, DALService, Record
from .exceptions import DALServiceError
from .vosi import AvailabilityMixin, CapabilityMixin
from .params import find_param_by_keyword, get_converter

from astropy.io.votable.tree import Param
from astropy import units as u
from astropy.units import Quantity, Unit
from astropy.units import spectral as spectral_equivalencies
from astropy.time import Time

from astropy.io.votable.tree import Resource, Group
from astropy.utils.collections import HomogeneousList

from ..utils.decorators import stream_decode_content
from ..dam.obscore import POLARIZATION_STATES


# monkeypatch astropy with group support in RESOURCE
def _monkeypath_astropy_resource_groups():
    old_group_unknown_tag = Group._add_unknown_tag

    def new_group_unknown_tag(self, iterator, tag, data, config, pos):
        if tag == "PARAM":
            return self._add_param(self, iterator, tag, data, config, pos)
        else:
            old_group_unknown_tag(self, iterator, tag, data, config, pos)

    old_init = Resource.__init__

    def new_init(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        self._groups = HomogeneousList(Group)
    Resource.__init__ = new_init

    def resource_groups(self):
        return self._groups
    Resource.groups = property(resource_groups)

    def resource_add_group(self, iterator, tag, data, config, pos):
        group = Group(self, config=config, pos=pos, **data)
        self.groups.append(group)
        group.parse(iterator, config)
    Resource._add_group = resource_add_group

    old_resource_unknown_tag = Resource._add_unknown_tag

    def new_resource_unknown_tag(self, iterator, tag, data, config, pos):
        if tag == "GROUP":
            return self._add_group(iterator, tag, data, config, pos)
        else:
            old_resource_unknown_tag(self, iterator, tag, data, config, pos)
    Resource._add_unknown_tag = new_resource_unknown_tag


if not hasattr(Resource, 'groups'):
    _monkeypath_astropy_resource_groups()

__all__ = [
    "AdhocServiceResultsMixin", "DatalinkResultsMixin", "DatalinkRecordMixin",
    "DatalinkService", "DatalinkQuery", "DatalinkResults", "DatalinkRecord",
    "SodaRecordMixin", "SodaQuery"]


def _get_input_params_from_resource(resource):
    # get the group with name inputParams
    group_input_params = next(
        group for group in resource.groups if group.name == "inputParams")
    # get only Param elements from the group
    return {
        _.name: _ for _ in group_input_params.entries if isinstance(_, Param)}


def _get_params_from_resource(resource):
    return {_.name: _ for _ in resource.params}


def _get_accessurl_from_params(params):
    if "accessURL" not in params:
        raise DALServiceError("Datalink has no accessURL")
    return params["accessURL"].value


class AdhocServiceResultsMixin:
    """
    Mixing for adhoc:service functionallity for results classes.
    """
    def __init__(self, votable, url=None, session=None):
        super().__init__(votable, url=url, session=session)

        self._adhocservices = list(
            resource for resource in votable.resources
            if resource.type == "meta" and resource.utype == "adhoc:service"
        )

    def iter_adhocservices(self):
        yield from self._adhocservices

    def get_adhocservice_by_ivoid(self, ivo_id):
        """
        Return the adhoc service starting with the given ivo_id.

        Parameters
        ----------
        ivoid : str
           the ivoid of the service we want to have.

        Returns
        -------
        Resource
            The resource element describing the service.
        """
        for adhocservice in self.iter_adhocservices():
            if any(
                    all((
                        param.name == "standardID",
                        param.value.lower().startswith(ivo_id.lower())
                    )) for param in adhocservice.params
            ):
                return adhocservice
        raise DALServiceError(
            "No Adhoc Service with ivo-id {}!".format(ivo_id))

    def get_adhocservice_by_id(self, id_):
        """
        Return the adhoc service starting with the given service_def id.

        Parameters
        ----------
        id_ : str
           the service_def id of the service we want to have.

        Returns
        -------
        Resource
            The resource element describing the service.
        """
        for adhocservice in self.iter_adhocservices():
            if adhocservice.ID == id_:
                return adhocservice
        raise DALServiceError(
            "No Adhoc Service with service_def id {}!".format(id_))


class DatalinkResultsMixin(AdhocServiceResultsMixin):
    """
    Mixing for datalink functionallity for results classes.
    """
    def iter_datalinks(self):
        """
        Iterates over all datalinks in a DALResult.
        """
        for record in self:
            yield record.getdatalink()


class DatalinkRecordMixin:
    """
    Mixin for record classes, providing functionallity for datalink.

    - ``getdataset()`` considers datalink.
    """
    def getdatalink(self):
        try:
            datalink = self._results.get_adhocservice_by_ivoid(
                b"ivo://ivoa.net/std/datalink")

            query = DatalinkQuery.from_resource(self, datalink)
            return query.execute()
        except DALServiceError:
            return DatalinkResults.from_result_url(self.getdataurl())

    @stream_decode_content
    def getdataset(self, timeout=None):
        try:
            url = next(self.getdatalink().bysemantics('#this')).access_url
            response = self._session.get(url, stream=True, timeout=timeout)
            response.raise_for_status()
            return response.raw
        except (DALServiceError, ValueError, StopIteration):
            # this should go to Record.getdataset()
            return super().getdataset(timeout=timeout)


class DatalinkService(DALService, AvailabilityMixin, CapabilityMixin):
    """
    a representation of a Datalink service
    """

    def __init__(self, baseurl, session=None):
        """
        instantiate a Datalink service

        Parameters
        ----------
        baseurl :  str
           the base URL that should be used for forming queries to the service.
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

    def run_sync(self, id, responseformat=None, **keywords):
        """
        runs sync query and returns its result

        Parameters
        ----------
        id : str
            the dataset identifier
        responseformat : str
            the output format

        Returns
        -------
        DatalinkResults
            the query result

        See Also
        --------
        DatalinkResults
        """
        return self.create_query(id, responseformat, **keywords).execute()

    # alias for service discovery
    search = run_sync

    def create_query(self, id, responseformat=None, **keywords):
        """
        create a query object that constraints can be added to and then
        executed.  The input arguments will initialize the query with the
        given values.

        Parameters
        ----------
        baseurl : str
            the base URL for the Datalink service
        id : str
            the dataset identifier
        responseformat : str
            the output format
        """
        return DatalinkQuery(
            self.baseurl, id, responseformat, **keywords)


class DatalinkQuery(DALQuery):
    """
    A class for preparing a query to a Datalink service.  Query constraints
    are added via its service type-specific methods.  The various execute()
    functions will submit the query and return the results.

    The base URL for the query, which controls where the query will be sent
    when one of the execute functions is called, is typically set at
    construction time; however, it can be updated later via the
    :py:attr:`~pyvo.dal.query.DALQuery.baseurl` to send a configured
    query to another service.

    A session can also optionally be passed in that will be used for
    network transactions made by this object to remote services.

    In addition to the search constraint attributes described below, search
    parameters can be set generically by name via dict semantics.
    The typical function for submitting the query is ``execute()``; however,
    alternate execute functions provide the response in different forms,
    allowing the caller to take greater control of the result processing.
    """
    @classmethod
    def from_resource(cls, row, resource, session=None, **kwargs):
        """
        Creates a instance from a Record and a Datalink Resource.

        XML Hierarchy:

        .. code:: xml

            <FIELD id="ID">
            <FIELD id="srcGroup">

            <GROUP name="inputParams">
                <PARAM name="ID" datatype="char" arraysize="*" value=""
                    ref="primaryID"/>
                <PARAM name="CALIB" datatype="char" arraysize="*"
                    value="FLUX"/>
                <PARAM name="GROUP" datatype="char" arraysize="*" value=""
                    ref="srcGroup"/>
            </GROUP>
        """
        input_params = _get_input_params_from_resource(resource)
        # get params outside of any group
        dl_params = _get_params_from_resource(resource)
        accessurl = _get_accessurl_from_params(dl_params)

        query_params = dict()
        for name, input_param in input_params.items():
            if input_param.ref:
                query_params[name] = row[input_param.ref]
            elif np.isscalar(input_param.value) and input_param.value:
                query_params[name] = input_param.value
            elif (
                    not np.isscalar(input_param.value) and
                    input_param.value.all() and
                    len(input_param.value)
            ):
                query_params[name] = " ".join(
                    str(_) for _ in input_param.value)

        for name, query_param in kwargs.items():
            try:
                input_param = find_param_by_keyword(name, input_params)
                converter = get_converter(input_param)
                query_params[input_param.name] = converter.serialize(
                    query_param)
            except KeyError:
                query_params[name] = query_param

        return cls(accessurl, session=session, **query_params)

    def __init__(
            self, baseurl, id=None, responseformat=None, session=None, **keywords):
        """
        initialize the query object with the given parameters

        Parameters
        ----------
        baseurl : str
            the Datalink baseurl
        id : str
            the dataset identifier
        responseformat : str
            the output format
        session : object
            optional session to use for network requests
        """
        super().__init__(baseurl, session=session, **keywords)

        if id:
            self["ID"] = id
        if responseformat:
            self["RESPONSEFORMAT"] = responseformat

    def execute(self):
        """
        submit the query and return the results as a DatalinkResults instance

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
        return DatalinkResults(self.execute_votable(), url=self.queryurl, session=self._session)


class DatalinkResults(DatalinkResultsMixin, DALResults):
    """
    The list of matching records resulting from an datalink query.
    Each record contains a set of metadata that describes an available
    record matching the query constraints.  The number of records in
    the results is available by passing it to the Python built-in ``len()``
    function.

    This class supports iterable semantics; thus,
    individual records (in the form of
    :py:class:`~pyvo.dal.query.Record` instances) are typically
    accessed by iterating over an ``DatalinkResults`` instance.

    Alternatively, records can be accessed randomly via
    :py:meth:`getrecord` or through a Python Database API (v2)
    Cursor (via :py:meth:`~pyvo.dal.query.DALResults.cursor`).
    Column-based data access is possible via the
    :py:meth:`~pyvo.dal.query.DALResults.getcolumn` method.

    ``DatalinkResults`` is essentially a wrapper around an Astropy
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

    >>> table = results.to_table()

    ``DatalinkResults`` supports the array item operator ``[...]`` in a
    read-only context.  When the argument is numerical, the result
    is an
    :py:class:`~pyvo.dal.query.Record` instance, representing the
    record at the position given by the numerical index.  If the
    argument is a string, it is interpreted as the name of a column,
    and the data from the column matching that name is returned as
    a Numpy array.
    """

    def getrecord(self, index):
        """
        return a representation of a datalink result record that follows
        dictionary semantics. The keys of the dictionary are those returned by
        this instance's fieldnames attribute. The returned record has the
        additional function :py:meth:`~pyvo.dal.query.DALResults.getdataset`

        Parameters
        ----------
        index : int
           the integer index of the desired record where 0 returns the first
           record

        Returns
        -------
        REc
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
        return DatalinkRecord(self, index, session=self._session)

    def bysemantics(self, semantics):
        """
        return the rows with the dataset identified by the given semantics

        Returns
        -------
        Sequence of DatalinkRecord
            a sequence of dictionary-like wrappers containing the result record
        """
        # TODO: get semantics with astropy and implement resursive lookup
        for record in self:
            if record.semantics == semantics:
                yield record

    def getdataset(self, timeout=None):
        """
        return the first row with the dataset identified by semantics #this

        Returns
        -------
        DatalinkRecord
            a dictionary-like wrapper containing the result record.
        """
        try:
            return next(self.bysemantics("#this")).getdataset(timeout=timeout)
        except StopIteration:
            raise ValueError("No row with semantics #this found!")

    def iter_procs(self):
        """
        iterate over all rows with a processing service
        """
        for row in self:
            if row.service_def:
                yield row

    def get_first_proc(self):
        """
        returns the first datalink row with a processing service.
        """
        for proc in self.iter_procs():
            return proc
        raise IndexError("No processing service found in datalink result")


class SodaRecordMixin:
    """
    Mixin for soda functionallity for record classes.
    If used, it's result class must have
    `pyvo.dal.datalink.AdhocServiceResultsMixin` mixed in.
    """
    def _get_soda_resource(self):
        try:
            return self._results.get_adhocservice_by_ivoid(
                b"ivo://ivoa.net/std/SODA#sync")
        except DALServiceError:
            pass

        # let it count as soda resource
        try:
            return self._results.get_adhocservice_by_ivoid(
                b"ivo://ivoa.net/std/datalink#links")
        except DALServiceError:
            pass

        dataformat = self.getdataformat()
        if dataformat is None:
            raise DALServiceError(
                "No SODA Resouces available and no dataformat in record. "
                "Maybe you forgot to include it into the TAP Query?")

        if "content=datalink" in dataformat:
            dataurl = self.getdataurl()
            if not dataurl:
                raise DALServiceError(
                    "No dataurl in record, but dataformat contains "
                    "'content=datalink'. Maybe you forgot to include it into "
                    "the TAP Query?")

            try:
                datalink_result = DatalinkResults.from_result_url(dataurl)
                return datalink_result.get_adhocservice_by_ivoid(
                    b"ivo://ivoa.net/std/SODA#sync")
            except DALServiceError:
                pass

        return None

    def processed(
            self, circle=None, range=None, polygon=None, band=None, **kwargs):
        """
        Returns processed dataset.

        Parameters
        ----------
        circle : `astropy.units.Quantity`
            latitude, longitude and radius
        range : `astropy.units.Quantity`
            two longitude + two latitude values describing a rectangle
        polygon : `astropy.units.Quantity`
            multiple (at least three) pairs of longitude and latitude points
        band : `astropy.units.Quantity`
            two bandwidth or frequency values
        """
        soda_resource = self._get_soda_resource()

        if soda_resource:
            soda_query = SodaQuery.from_resource(
                self, soda_resource, circle=circle, range=range,
                polygon=polygon, band=band, **kwargs)

            soda_stream = soda_query.execute_stream()
            soda_query.raise_if_error()
            return soda_stream
        else:
            return self.getdataset()


class DatalinkRecord(DatalinkRecordMixin, SodaRecordMixin, Record):
    """
    a dictionary-like container for data in a record from the results of an
    datalink query,

    The commonly accessed metadata which are stadardized by the datalink
    standard are available as attributes.  If the metadatum accessible
    via an attribute is not available, the value of that attribute
    will be None.  All metadata, including non-standard metadata, are
    acessible via the ``get(`` *key* ``)`` function (or the [*key*]
    operator) where *key* is table column name.
    """

    @property
    def id(self):
        """
        Input identifier
        """
        return self.get("ID", decode=True)

    @property
    def access_url(self):
        """
        Link to data or processing service
        """
        row_url = self.get("access_url", decode=True)

        if not row_url:
            proc_resource = self._results.get_adhocservice_by_id(
                self.service_def)
            dl_params = _get_params_from_resource(proc_resource)
            row_url = _get_accessurl_from_params(dl_params)

        return row_url

    @property
    def service_def(self):
        """
        reference to the service descriptor resource
        """
        return self.get("service_def", decode=True)

    @property
    def error_message(self):
        """
        Error if an access_url cannot be created
        """
        return self.get("error_message", decode=True)

    @property
    def description(self):
        """
        Human-readable text describing this link
        """
        return self.get("description", decode=True)

    @property
    def semantics(self):
        """
         Term from a controlled vocabulary describing the link
        """
        return self.get("semantics", decode=True)

    @property
    def content_type(self):
        """
        Mime-type of the content the link returns
        """
        return self.get("content_type", decode=True)

    @property
    def content_length(self):
        """
        Size of the download the link returns
        """
        return int(self["content_length"])

    def getdataurl(self):
        """
        return the URL contained in the access URL column which can be used
        to retrieve the dataset described by this record. Raises
        :py:class:`~pyvo.dal.query.DALServiceError` if theres an error.
        """
        if self.error_message:
            raise DALServiceError(self.error_message)

        return self.access_url

    def process(self, **kwargs):
        """
        calls the processing service and returns it's result as a file-like
        object
        """
        proc_resource = self._results.get_adhocservice_by_id(self.service_def)
        proc_query = DatalinkQuery.from_resource(self, proc_resource, **kwargs)
        proc_stream = proc_query.execute_stream()
        return proc_stream

    @property
    def params(self):
        """
        the access parameters of the service behind this datalink row.
        """
        proc_resource = self._results.get_adhocservice_by_id(self.service_def)
        return proc_resource.params

    @property
    def input_params(self):
        """
        a list of input parameters for the service behind this datalink row.
        """
        proc_resource = self._results.get_adhocservice_by_id(self.service_def)
        return list(_get_input_params_from_resource(proc_resource).values())


class AxisParamMixin():
    """
    a class to handle axis parameters (pos, band, time and pol) in Soda
    or SIAv2 queries
    """
    @property
    def pos(self):
        """
        return a copy of the list of positions to be used as constraints
        """
        if getattr(self, '_pos', None):
            return copy.deepcopy(self._pos)
        return None

    def pos_append(self, val):
        """
        append a new position to be used as constraints.

        PARAMETERS:
            val: tuple
                3 elem for CIRCLE, 4 for RANGE and even > 6 for POLYGON
        """
        if not isinstance(val, (tuple, Quantity)):
            raise ValueError('Expected list or tuple for pos attribute: '.
                             format(val))
        if not getattr(self, '_pos', None):
            setattr(self, '_pos', [])
        if len(val) < 3:
            raise ValueError(
                'Position needs at least 3 values. Received {}'.
                    format(val))
        if len(val) == 3:
            # must be circle
            shape = 'CIRCLE '
        elif len(val) == 4:
            shape = 'RANGE '
        elif not len(val)%2:
            shape = 'POLYGON '
        else:
            raise ValueError(
                'Polygon needs even number of values (ra-dec pairs).'
                'Received: {}'.format(val))
        try:
            self._validate_pos(val)
        except Exception as e:
            raise ValueError('Invalid position {}. Reason: {}'.format(
                val, str(e)))
        format_val = shape + self._get_format_points(val)
        if 'POS' in self:
            if format_val not in self['POS']:
                self['POS'].append(format_val)
                self._pos.append(val)
        else:
            self['POS'] = [format_val]
            self._pos.append(val)

    def pos_del(self, index):
        if 'POS' in self:
            del self['POS'][index]
        if getattr(self, '_pos', None):
            del self._pos[index]

    @property
    def band(self):
        """
        return a copy of the list of energy bands to be used as constraints
        """
        if getattr(self, '_band', None):
            return copy.deepcopy(self._band)
        return None

    def band_append(self, val):

        if isinstance(val, tuple):
            if len(val) == 1:
                max_band = min_band = val[0]
            elif len(val) == 2:
                min_band = val[0]
                max_band = val[1]
            else:
                raise ValueError('Too few/many members in band attribute: '.
                                 format(val))
        else:
            max_band = min_band = val

        if not getattr(self, '_band', None):
            setattr(self, '_band', [])

        if not isinstance(min_band, Quantity):
            min_band = min_band*u.meter
        min_band = min_band.to(u.meter)
        if not isinstance(max_band, Quantity):
            max_band = max_band*u.meter
        if min_band > max_band:
            raise ValueError('Invalid band: min({}) > max({})'.format(
                min_band, max_band))
        max_band = max_band.to(u.meter)
        format_band = '{} {}'.format(min_band.value, max_band.value)
        if 'BAND' in self:
            if format_band not in self['BAND']:
                self['BAND'].append(format_band)
                self._band.append(val)
        else:
            self['BAND'] = [format_band]
            self._band.append(val)

    def band_del(self, index):
        if 'BAND' in self:
            del self['BAND'][index]
        if getattr(self, '_band', None):
            del self._band[index]

    @property
    def time(self):
        """
        return a copy of the list of time lists to be used as constraints
        """
        if getattr(self, '_time', None):
            return copy.deepcopy(self._time)
        return None

    def time_append(self, val):
        """
        append a new time instance or interval
        """
        if not getattr(self, '_time', None):
            setattr(self, '_time', [])
        if isinstance(val, tuple):
            if len(val) == 1:
                max_time = min_time = val[0]
            elif len(val) == 2:
                min_time = val[0]
                max_time = val[1]
            else:
                raise ValueError('Too few/many members in time attribute: '.
                                 format(val))
        else:
            max_time = min_time = val

        if not isinstance(min_time, Time):
            min_time = Time(min_time)
        if not isinstance(max_time, Time):
            max_time = Time(max_time)
        if min_time > max_time:
            raise ValueError('Invalid time interval: min({}) > max({})'.format(
                min_time, max_time
            ))
        format_time = '{} {}'.format(min_time.mjd, max_time.mjd)
        if 'TIME' in self:
            if format_time not in self['TIME']:
                self['TIME'].append(format_time)
                self._time.append(val)
        else:
            self['TIME'] = [format_time]
            self._time.append(val)

    def time_del(self, index):
        """
        delete a time instance or interval
        """
        if 'TIME' in self:
            del self['TIME'][index]
        if getattr(self, '_time', None):
            del self._time[index]

    @property
    def pol(self):
        """
        return a copy of the list of polarization states to be used as
        constraints
        """
        if getattr(self, '_pol', None):
            return copy.deepcopy(self._pol)
        return None

    def pol_append(self, val):
        """
        appends a new polarization state to the search constraints
        """
        if val not in POLARIZATION_STATES:
            raise ValueError('{} not a valid polarization state: {}'.
                             format(val, POLARIZATION_STATES))
        if not getattr(self, '_pol', None):
            setattr(self, '_pol', [])
        if 'POL' in self:
            if val not in self['POL']:
                self['POL'].append(val)
                self._pol.append(val)
        else:
            self['POL'] = [val]
            self._pol.append(val)

    def pol_del(self, index):
        """
        deletes a polarization state from constraints
        """
        if 'POL' in self:
            del self['POL'][index]
        if getattr(self, '_pol', None):
            del self._pol[index]

    def _get_format_points(self, values):
        """
        formats the tuple values into a string to be sent to the service
        entries in values are either quantities or assumed to be degrees
        """
        return ' '.join(
            [str(val.to(u.deg).value) if isinstance(val, Quantity) else
             str((val*u.deg).value) for val in values])

    def _validate_pos(self, pos):
        """
        validates position

        This has probably done already somewhere else
        """
        if len(pos) == 3:
            self._validate_ra(pos[0])
            self._validate_dec(pos[1])
            if not isinstance(pos[2], Quantity):
                radius = pos[2] * u.deg
            else:
                radius = pos[2]
            if radius <= 0*u.deg  or radius.to(u.deg) > 90*u.deg:
                raise ValueError('Invalid circle radius: {}'.format(radius))
        elif len(pos) == 4:
            ra_min = pos[0] if isinstance(pos[0], Quantity) else pos[0] * u.deg
            ra_max = pos[1] if isinstance(pos[1], Quantity) else pos[1] * u.deg
            dec_min = pos[2] if isinstance(pos[2], Quantity) \
                else pos[2] * u.deg
            dec_max = pos[3] if isinstance(pos[3], Quantity) \
                else pos[3] * u.deg
            self._validate_ra(ra_min)
            self._validate_ra(ra_max)
            if ra_max.to(u.deg) < ra_min.to(u.deg):
                raise ValueError('min > max in ra range: '.format(ra_min,
                                                                  ra_max))
            self._validate_dec(dec_min)
            self._validate_dec(dec_max)
            if dec_max.to(u.deg) < dec_min.to(u.deg):
                raise ValueError('min > max in dec range: '.format(dec_min,
                                                                   dec_max))
        else:
            for i, m in enumerate(pos):
                if i%2:
                    self._validate_dec(m)
                else:
                    self._validate_ra(m)

    def _validate_ra(self, ra):
        if not isinstance(ra, Quantity):
            ra = ra * u.deg
        if ra.to(u.deg).value < 0 or ra.to(u.deg).value > 360.0:
            raise ValueError('Invalid ra: {}'.format(ra))

    def _validate_dec(self, dec):
        if not isinstance(dec, Quantity):
            dec = dec * u.deg
        if dec.to(u.deg).value < -90.0 or dec.to(u.deg).value > 90.0:
            raise ValueError('Invalid dec: {}'.format(dec))


class SodaQuery(DatalinkQuery, AxisParamMixin):
    """
    a class for preparing a query to a SODA Service.
    """
    def __init__(
            self, baseurl, circle=None, range=None, polygon=None, band=None,
            **kwargs):
        super().__init__(baseurl, **kwargs)

        if circle:
            self.circle = circle

        if range:
            self.range = range

        if polygon:
            self.polygon = polygon

        if band:
            self.band = band

    @property
    def circle(self):
        """
        The CIRCLE parameter defines a spatial region using the circle xtype
        defined in DALI.
        """
        return getattr(self, '_circle', None)

    @circle.setter
    def circle(self, circle):
        self._validate_pos(circle)
        if len(circle) != 3:
           raise ValueError(
                "Circle must be a sequence with exactly three values")
        self['CIRCLE'] = self._get_format_points(circle)
        setattr(self, '_circle', circle)
        del self.range
        del self.polygon

    @circle.deleter
    def circle(self):
        if hasattr(self, '_circle'):
            delattr(self, '_circle')
        if 'CIRCLE' in self:
            del self['CIRCLE']

    @property
    def range(self):
        """
        A rectangular range.
        """
        warnings.warn(
            "Use pos attribute instead",
            DeprecationWarning
        )
        return getattr(self, '_circle', None)

    @range.setter
    def range(self, range):
        warnings.warn(
            "Use pos attribute instead",
            DeprecationWarning
        )
        self._validate_pos(range)
        setattr(self, '_range', range)
        if len(range) != 4:
           raise ValueError(
               "Range must be a sequence with exactly four values")
        self['POS'] = 'RANGE ' + self._get_format_points(range)
        del self.circle
        del self.polygon

    @range.deleter
    def range(self):

        if hasattr(self, '_range'):
            delattr(self, '_range')
        if 'POS' in self and self['POS'].startswith('RANGE'):
            del self['POS']

    @property
    def polygon(self):
        """
        The POLYGON parameter defines a spatial region using the polygon xtype
        defined in DALI.
        """
        return getattr(self, '_polygon', None)

    @polygon.setter
    def polygon(self, polygon):
        if len(polygon) < 6 or len(polygon)%2:
            raise ValueError(
                'Polygon must be a sequence with at least six numeric values, '
                'expressing pairs of ra and dec in degrees'
            )
        self._validate_pos(polygon)
        self['POLYGON'] = self._get_format_points(polygon)
        setattr(self, '_polygon', polygon)
        del self.circle
        del self.range

    @polygon.deleter
    def polygon(self):
        if hasattr(self, '_polygon'):
            delattr(self, '_polygon')
        if 'POLYGON' in self:
            del self['POLYGON']

    @property
    def band(self):
        """
        The BAND parameter defines the wavelength interval(s) to be extracted
        from the data using a floating point interval
        """
        return getattr(self, "_band", None)

    @band.setter
    def band(self, band):
        setattr(self, "_band", band)

        if not isinstance(band, Quantity):
            valerr = ValueError(
                'Band must be specified with exactly two values, ',
                'expressing a frequency or wavelength range'
            )

            try:
                # assume meters
                band = band * Unit("meter")
                if len(band) != 2:
                    raise valerr
            except (ValueError, TypeError):
                raise valerr

        # transform to meters
        band = band.to(Unit("m"), equivalencies=spectral_equivalencies())
        # frequency is counter-proportional to wavelength, so we just sort
        # it to have the right order again
        band.sort()

        self["BAND"] = "{start} {end}".format(
            start=band.value[0], end=band.value[1])

    @band.deleter
    def band(self):
        if hasattr(self, '_band'):
            delattr(self, '_band')
        if 'BAND' in self:
            del self['BAND']
