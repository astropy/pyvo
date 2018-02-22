# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Datalink classes and mixins
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import numpy as np

import requests

from .query import DALResults, DALQuery, DALService, Record
from .exceptions import DALServiceError
from .vosi import AvailabilityMixin, CapabilityMixin

from astropy.io.votable.tree import Param
from astropy.units import Quantity, Unit
from astropy.units import spectral as spectral_equivalencies

from ..utils.decorators import stream_decode_content


# monkeypatch astropy with group support in RESOURCE
def _monkeypath_astropy_resource_groups():
    from astropy.io.votable.tree import Resource, Group
    from astropy.utils.collections import HomogeneousList

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
            old_resource_unknown_tag(iterator, tag, data, config, pos)
    Resource._add_unknown_tag = new_resource_unknown_tag


_monkeypath_astropy_resource_groups()

__all__ = [
    "AdhocServiceResultsMixin", "DatalinkResultsMixin", "DatalinkRecordMixin",
    "DatalinkService", "DatalinkQuery", "DatalinkResults", "DatalinkRecord",
    "SodaRecordMixin", "SodaQuery"]


class AdhocServiceResultsMixin(object):
    """
    Mixing for adhoc:service functionallity for results classes.
    """
    def __init__(self, votable, url=None):
        super(AdhocServiceResultsMixin, self).__init__(votable, url=url)

        self._adhocservices = list(
            resource for resource in votable.resources
            if resource.type == "meta" and resource.utype == "adhoc:service"
        )

    def iter_adhocservices(self):
        for adhocservice in self._adhocservices:
            yield adhocservice

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


class DatalinkRecordMixin(object):
    """
    Mixin for record classes, providing functionallity for datalink.

    - ``getdataset()`` considers datalink.
    """
    def getdatalink(self):
        datalink = self._results.get_adhocservice_by_ivoid(
            b"ivo://ivoa.net/std/datalink")

        query = DatalinkQuery.from_resource(self, datalink)
        return query.execute()

    @stream_decode_content
    def getdataset(self, timeout=None):
        try:
            url = next(self.getdatalink().bysemantics('#this')).access_url
            r = requests.get(url, stream=True, timeout=timeout)
            r.raise_for_status()
            return r.raw
        except (DALServiceError, StopIteration):
            # this should go to Record.getdataset()
            return super(DatalinkRecordMixin, self).getdataset(timeout=timeout)


class DatalinkService(DALService, AvailabilityMixin, CapabilityMixin):
    """
    a representation of a Datalink service
    """

    def __init__(self, baseurl):
        """
        instantiate a Datalink service

        Parameters
        ----------
        baseurl :  str
           the base URL that should be used for forming queries to the service.
        """
        super(DatalinkService, self).__init__(baseurl)

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
    a class for preparing an query to an Datalink service.  Query constraints
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
    @classmethod
    def from_resource(cls, row, resource, **kwargs):
        """
        Creates a instance from a Record and a Datalink Resource.

        XML Hierarchy:

        <FIELD id="ID"...>
        <FIELD id="srcGroup">

        <GROUP name="inputParams">
            <PARAM name="ID" datatype="char" arraysize="*" value=""
                ref="primaryID"/>
            <PARAM name="CALIB" datatype="char" arraysize="*" value="FLUX"/>
            <PARAM name="GROUP" datatype="char" arraysize="*" value=""
                ref="srcGroup"/>
        </GROUP>
        """
        # get the group with name inputParams
        group_input_params = next(
            group for group in resource.groups if group.name == "inputParams")
        # get params outside of any group
        dl_params = {_.name: _ for _ in resource.params}
        # get only Param elements from the group
        input_params = (
            _ for _ in group_input_params.entries if isinstance(_, Param))

        if "accessURL" not in dl_params:
            raise DALServiceError("Datalink has no accessURL")

        query_params = dict()
        for input_param in input_params:
            if input_param.ref:
                query_params[input_param.name] = row[input_param.ref]
            elif np.isscalar(input_param.value) and input_param.value:
                query_params[input_param.name] = input_param.value
            elif (
                    not np.isscalar(input_param.value) and
                    input_param.value.all() and
                    len(input_param.value)
            ):
                query_params[input_param.name] = " ".join(
                    str(_) for _ in input_param.value)

        query_params.update(kwargs)

        return cls(dl_params["accessURL"].value, **query_params)

    def __init__(
            self, baseurl, id=None, responseformat=None, **keywords):
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
        """
        super(DatalinkQuery, self).__init__(baseurl, **keywords)

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
        return DatalinkResults(self.execute_votable(), url=self.queryurl)


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
        return DatalinkRecord(self, index)

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


class SodaRecordMixin(object):
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
        Link to data
        """
        return self.get("access_url", decode=True)

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


class SodaQuery(DatalinkQuery):
    """
    a class for preparing a query to a SODA Service.
    """
    def __init__(
            self, baseurl, circle=None, range=None, polygon=None, band=None,
            **kwargs):
        super(SodaQuery, self).__init__(baseurl, **kwargs)

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
        setattr(self, '_circle', circle)
        del self.range
        del self.polygon

        if not isinstance(circle, Quantity):
            valerr = ValueError(
                "Circle must be a sequence with exactly three values")

            try:
                # assume degrees
                circle = circle * Unit('deg')
                if len(circle) != 3:
                    raise valerr
            except (ValueError, TypeError):
                raise valerr

        self['CIRCLE'] = ' '.join(
            str(value) for value in circle.to(Unit('deg')).value)

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
        return getattr(self, '_circle', None)

    @range.setter
    def range(self, range):
        setattr(self, '_range', range)
        del self.circle
        del self.polygon

        if not isinstance(range, Quantity):
            valerr = ValueError(
                "Range must be a sequence with exactly four values")

            try:
                # assume degrees
                range = range * Unit('deg')
                if len(range) != 4:
                    raise valerr
            except (ValueError, TypeError):
                raise valerr

        self['POS'] = 'RANGE ' + ' '.join(
            str(value) for value in range.to(Unit('deg')).value)

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
        setattr(self, '_polygon', polygon)
        del self.circle
        del self.range

        if not isinstance(polygon, Quantity):
            valerr = ValueError(
                'Polygon must be a sequence with at least six numeric values, '
                'expressing pairs of ra and dec in degrees'
            )

            try:
                # assume degrees
                polygon = polygon * Unit('deg')
                if len(polygon) < 3:
                    raise valerr
            except (ValueError, TypeError):
                raise valerr

        self['POLYGON'] = ' '.join(
            str(value) for value in polygon.to(Unit('deg')).value)

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
