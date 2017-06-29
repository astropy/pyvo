# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
A module for accessing remote source and observation catalogs
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import warnings

from .query import (
    DALResults, DALQuery, DALService, Record, DALServiceError, PyvoUserWarning)
from .mixin import AvailabilityMixin, CapabilityMixin

from astropy.io.votable.tree import Param

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
    "search", "DatalinkService", "DatalinkQuery", "DatalinkResults"]

def search(url, id, responseformat=None, **keywords):
    """
    submit a Datalink query that returns rows matching the criteria given.

    Parameters
    ----------
    url : str
        the base URL of the query service.
    id : str
        the dataset identifier
    responseformat : str
        the output format

    Returns
    -------
    DatalinkResults
        a container holding a table of matching catalog records

    Raises
    ------
    DALServiceError
        for errors connecting to or
        communicating with the service.
    DALQueryError
        if the service responds with
        an error, including a query syntax error.
    """
    service = DatalinkService(url)
    return service.search(id, responseformat, **keywords)

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

    #alias for service discovery
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
    def from_resource(cls, row, resource):
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
        # TODO: implement the full xml hierarchy
        group_input_params = next(
            group for group in resource.groups if group.name == "inputParams")
        dl_params = {_.name: _ for _ in resource.params}
        input_params = (
            _ for _ in group_input_params.entries if type(_) == Param)

        if "accessURL" not in dl_params:
            raise DALServiceError("Datalink has no accessURL")

        query_params = {}
        for input_param in input_params:
            if input_param.value:
                query_params[input_param.name] = input_param.value
            elif input_param.ref:
                query_params[input_param.name] = row[input_param.ref]

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
        return DatalinkResults(self.execute_votable(), self.queryurl)


class DatalinkResults(DALResults):
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

    >>> table = results.table

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
            a sequence of dictionary-like wrappers containing the result record.
        """
        # TODO: get semantics with astropy and implement resursive lookup
        for record in self:
            if record.semantics == semantics:
                yield record

    def getdataset(self):
        """
        return the first row with the dataset identified by semantics #this

        Returns
        -------
        DatalinkRecord
            a dictionary-like wrapper containing the result record.
        """
        try:
            return next(self.bysemantics("#this"))
        except StopIteration:
            raise ValueError("No row with semantics #this found!")


class DatalinkRecord(Record):
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


class DatalinkMixin(object):
    """
    Mixing for datalink functionallity

    If you mix this in, you have to call _init_datalinks in your constructor.
    """
    _datalinks = None

    def iter_datalinks(self):
        """
        Iterates over all datalinks in a DALResult.
        """
        if self._datalinks is None:
            raise RuntimeError(
                "iter_datalinks called without previous init_datalinks")

        if len(self._datalinks) < 1:
            return

        if len(self._datalinks) > 1:
            warnings.warn(
                "Got more than one datalink element!", PyvoUserWarning)

        datalink = next(iter(self._datalinks))

        for record in self:
            query = DatalinkQuery.from_resource(record, datalink)
            yield query.execute()

    def _init_datalinks(self, votable):
        # this can be overridden to specialize for a particular DAL protocol
        adhocs = (
            resource for resource in votable.resources
            if resource.type == "meta" and resource.utype == "adhoc:service"
        )

        datalinks = (
            adhoc for adhoc in adhocs
            if any(
                param.name == "standardID" and param.value.lower(
                    ).startswith(b"ivo://ivoa.net/std/datalink")
                for param in adhoc.params))

        self._datalinks = list(datalinks)


