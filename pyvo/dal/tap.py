# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
A module for accessing remote source and observation catalogs
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

from functools import partial
from datetime import datetime
from time import sleep
from distutils.version import LooseVersion
import requests
from astropy.io.votable import parse as votableparse

from .query import (
    DALResults, DALQuery, DALService, Record, UploadList,
    DALServiceError, DALQueryError)
from ..tools import vosi, uws

__all__ = [
    "search", "escape", "TAPService", "TAPQuery", "AsyncTAPJob", "TAPResults"]

def escape(term):
    """
    escapes a term for use in ADQL
    """
    return str(term).replace("'", "''")

def search(url, query, language="ADQL", maxrec=None, uploads=None, **keywords):
    """
    submit a Table Access query that returns rows matching the criteria given.

    Parameters
    ----------
    url : str
        the base URL of the query service.
    query : str, dict
        The query string / parameters
    language : str
        specifies the query language, default ADQL.
        useful for services which allow to use the backend query language.
    maxrec : int
        specifies the maximum records to return. defaults to the service default
    uploads : dict
        a mapping from table names to file like objects containing a votable

    Returns
    -------
    TAPResults
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
    service = TAPService(url)
    return service.search(query, language, maxrec, uploads, **keywords)

class TAPService(DALService):
    """
    a representation of a Table Access Protocol service
    """

    _availability = (None, None)
    _capabilities = None
    _tables = None

    def __init__(self, baseurl):
        """
        instantiate a Tablee Access Protocol service

        Parameters
        ----------
        baseurl :  str
           the base URL that should be used for forming queries to the service.
        """
        super(TAPService, self).__init__(baseurl)

    @property
    def availability(self):
        """
        returns availability as a tuple in the following form:

        Returns
        -------
        [0] : bool
            whether the service is available or not
        [1] : datetime
            the time since the server is running
        """
        if self._availability == (None, None):
            avail_url = '{0}/availability'.format(self.baseurl)

            response = requests.get(avail_url, stream=True)

            try:
                response.raise_for_status()
            except requests.RequestException as ex:
                raise DALServiceError.from_except(ex, avail_url)

            # requests doesn't decode the content by default
            response.raw.read = partial(response.raw.read, decode_content=True)

            self._availability = vosi.parse_availability(response.raw)
        return self._availability

    @property
    def available(self):
        """
        True if the service is available, False otherwise
        """
        return self.availability[0]

    @property
    def up_since(self):
        """
        datetime the service was started
        """
        return self.availability[1]

    @property
    def capabilities(self):
        """returns capabilities as a nested dictionary

        Known keys include:

            * outputs_formats
            * languages: {
                'ADQL-2.0': {
                    'features':
                        'ivo://ivoa.net/std/TAPRegExt#features-adqlgeo': [],
                        'ivo://ivoa.net/std/TAPRegExt#features-udf': [],
                }
        """
        if self._capabilities is None:
            capa_url = '{0}/capabilities'.format(self.baseurl)
            response = requests.get(capa_url, stream=True)

            try:
                response.raise_for_status()
            except requests.RequestException as ex:
                raise DALServiceError.from_except(ex, capa_url)

            # requests doesn't decode the content by default
            response.raw.read = partial(response.raw.read, decode_content=True)

            self._capabilities = vosi.parse_capabilities(response.raw)
        return self._capabilities

    @property
    def tables(self):
        """
        returns tables as a flat OrderedDict
        """
        if self._tables is None:
            tables_url = '{0}/tables'.format(self.baseurl)

            response = requests.get(tables_url, stream=True)

            try:
                response.raise_for_status()
            except requests.RequestException as ex:
                raise DALServiceError.from_except(ex, tables_url)

            # requests doesn't decode the content by default
            response.raw.read = partial(response.raw.read, decode_content=True)

            self._tables = vosi.parse_tables(response.raw)
        return self._tables

    @property
    def maxrec(self):
        """
        the default output limit.

        Raises
        ------
        DALServiceError
            if the property is not exposed by the service
        """
        try:
            for capa in self.capabilities:
                if "outputLimit" in capa:
                    return capa["outputLimit"]["default"]["value"]
        except KeyError:
            pass
        raise DALServiceError("Default limit not exposed by the service")

    @property
    def hardlimit(self):
        """
        the hard output limit.

        Raises
        ------
        DALServiceError
            if the property is not exposed by the service
        """
        try:
            for capa in self.capabilities:
                if "outputLimit" in capa:
                    return capa["outputLimit"]["hard"]["value"]
        except KeyError:
            pass
        raise DALServiceError("Hard limit not exposed by the service")

    @property
    def upload_methods(self):
        """
        a list of upload methods in form of IVOA identifiers
        """
        _upload_methods = []
        for capa in self.capabilities:
            if "uploadMethods" in capa:
                _upload_methods += capa["uploadMethods"]
        return _upload_methods

    def run_sync(
            self, query, language="ADQL", maxrec=None, uploads=None,
            **keywords):
        """
        runs sync query and returns its result

        Parameters
        ----------
        query : str
            The query
        language : str
            specifies the query language, default ADQL.
            useful for services which allow to use the backend query language.
        maxrec : int
            specifies the maximum records to return. defaults to the service default
        uploads : dict
            a mapping from table names to file like objects containing a votable

        Returns
        -------
        TAPResults
            the query result

        See Also
        --------
        TAPResults
        """
        return self.create_query(
            query, language=language, maxrec=maxrec, uploads=uploads,
            **keywords).execute()

    #alias for service discovery
    search = run_sync

    def run_async(
            self, query, language="ADQL", maxrec=None, uploads=None,
            **keywords):
        """
        runs async query and returns its result

        Parameters
        ----------
        query : str, dict
            the query string / parameters
        language : str
            specifies the query language, default ADQL.
            useful for services which allow to use the backend query language.
        maxrec : int
            specifies the maximum records to return. defaults to the service default
        uploads : dict
            a mapping from table names to file like objects containing a votable

        Returns
        -------
        TAPResult
            the query instance

        Raises
        ------
        DALServiceError
           for errors connecting to or communicating with the service
        DALQueryError
           for errors either in the input query syntax or
           other user errors detected by the service
        DALFormatError
           for errors parsing the VOTable response

        See Also
        --------
        AsyncTAPJob
        """
        job = AsyncTAPJob.create(
            self.baseurl, query, language, maxrec, uploads, **keywords)
        job = job.run().wait()
        job.raise_if_error()
        result = job.fetch_result()
        job.delete()

        return result

    def submit_job(self, query, language="ADQL", maxrec=None, uploads=None):
        """
        submit a async query without starting it and returns a AsyncTAPJob
        object

        Parameters
        ----------
        query : str
            the query string / parameters
        language : str
            specifies the query language, default ADQL.
            useful for services which allow to use the backend query language.
        maxrec : int
            specifies the maximum records to return. defaults to the service default
        uploads : dict
            a mapping from table names to file like objects containing a votable

        Returns
        -------
        AsyncTAPJob
            the query instance

        See Also
        --------
        AsyncTAPJob
        """
        return AsyncTAPJob.create(
            self.baseurl, query, language, maxrec, uploads)

    def create_query(
            self, query=None, mode="sync", language="ADQL", maxrec=None,
            uploads=None, **keywords):
        """
        create a query object that constraints can be added to and then
        executed.  The input arguments will initialize the query with the
        given values.

        Parameters
        ----------
        baseurl : str
            the base URL for the TAP service
        query : str
            the query string / parameters
        mode : str
            the query mode (sync | async). default "sync"
        language : str
            specifies the query language, default ADQL.
            useful for services which allow to use the backend query language.
        maxrec : int
            specifies the maximum records to return.
            defaults to the service default.
        uploads : dict
            a mapping from table names to objects containing a votable.
        """
        return TAPQuery(
            self.baseurl, query, mode, language, maxrec, uploads, **keywords)


class AsyncTAPJob(object):
    """
    This class represents a UWS TAP Job.
    """

    _job = {}

    @classmethod
    def create(
            cls, baseurl, query, language="ADQL", maxrec=None, uploads=None,
            **keywords):
        """
        creates a async tap job on the server under `baseurl`

        Parameters
        ----------
        baseurl : str
            the TAP baseurl
        query : str
            the query string
        language : str
            specifies the query language, default ADQL.
            useful for services which allow to use the backend query language.
        maxrec : int
            specifies the maximum records to return. defaults to the service default
        uploads : dict
            a mapping from table names to file like objects containing a votable
        """
        query = TAPQuery(
            baseurl, query, mode="async", language=language, maxrec=maxrec,
            uploads=uploads, **keywords)
        response = query.submit()
        job = cls(response.url)
        return job

    def __init__(self, url):
        """
        initialize the job object with the given url and fetch the remote values

        Parameters
        ----------
        url : str
            the job url
        """
        self._url = url
        self._update()

    def __enter__(self):
        """
        Enters the context
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exits the context. The job is silently deleted.
        """
        try:
            self.delete()
        except Exception:
            pass

    def _update(self, wait_for_statechange=False):
        """
        updates local job infos with remote values
        """
        try:
            if wait_for_statechange:
                response = requests.get(self.url, stream=True, params={
                    "WAIT": "-1"
                })
            else:
                response = requests.get(self.url, stream=True)
            response.raise_for_status()
        except requests.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, self.url)

        # requests doesn't decode the content by default
        response.raw.read = partial(response.raw.read, decode_content=True)

        self._job.update(uws.parse_job(response.raw))

    @property
    def job(self):
        """
        all up-to-date uws job infos as dictionary
        """
        #keep it up to date
        self._update()
        return self._job

    @property
    def url(self):
        """
        the job url
        """
        return self._url

    @property
    def job_id(self):
        """
        the job id
        """
        return self._job["jobId"]

    @property
    def phase(self):
        """
        the current query phase
        """
        self._update()
        return self._job["phase"]

    @property
    def execution_duration(self):
        """
        maximum execution duration. read-write
        """
        self._update()
        return self._job["executionDuration"]

    @execution_duration.setter
    def execution_duration(self, value):
        """
        maximum execution duration. read-write

        Parameters
        ----------
        value : int
            seconds after the query execution is aborted
        """
        try:
            response = requests.post(
                "{}/executionduration".format(self.url),
                data={"EXECUTIONDURATION": str(value)})
            response.raise_for_status()
        except requests.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, self.url)
        self._job["executionDuration"] = value

    @property
    def destruction(self):
        """
        datetime after which the job results are deleted automatically.
        read-write
        """
        self._update()
        return self._job["destruction"]

    @destruction.setter
    def destruction(self, value):
        """
        datetime after which the job results are deleted automatically.
        read-write

        Parameters
        ----------
        value : datetime
            datetime after which the job results are deleted automatically
        """
        try:
            #is string? easier to ask for forgiveness
            value = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass

        try:
            response = requests.post(
                "{}/destruction".format(self.url),
                data={"DESTRUCTION": value.strftime("%Y-%m-%dT%H:%M:%SZ")})
            response.raise_for_status()
        except requests.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, self.url)
        self._job["destruction"] = value

    @property
    def quote(self):
        """
        estimated runtime
        """
        self._update()
        return self._job["quote"]

    @property
    def owner(self):
        """
        job owner (if applicable)
        """
        self._update()
        return self._job["owner"]

    @property
    def result_uris(self):
        """
        a list of the last result uri's
        """
        return self._job["results"]

    @property
    def result_uri(self):
        """
        the first result uri
        """
        try:
            return next(iter(self.result_uris.values()))
        except StopIteration:
            return None

    @property
    def uws_version(self):
        self._update()
        return self._job["version"]

    def run(self):
        """
        starts the job / change phase to RUN
        """
        try:
            response = requests.post(
                '{}/phase'.format(self.url), data={"PHASE": "RUN"})
            response.raise_for_status()
        except requests.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, self.url)

        return self

    def abort(self):
        """
        aborts the job / change phase to ABORT
        """
        try:
            response = requests.post(
                '{}/phase'.format(self.url), data={"PHASE": "ABORT"})
            response.raise_for_status()
        except requests.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, self.url)

        return self

    def wait(
            self, phases=None):
        """
        waits for the job to reach the given phases.

        Parameters
        ----------
        phases : list
            phases to wait for

        Raises
        ------
        DALServiceError
            if the job is in a state that won't lead to an result
        """
        if not phases:
            phases = {"COMPLETED", "ABORTED", "ERROR"}

        interval = 1.0
        increment = 1.2

        active_phases = {
            "QUEUED", "EXECUTING", "RUN", "COMPLETED", "ERROR", "UNKNOWN"}

        while True:
            self._update(wait_for_statechange=True)
            # use the cached value
            cur_phase = self._job["phase"]

            if cur_phase not in active_phases:
                raise DALServiceError(
                    "Cannot wait for job completion. Job is not active!")

            if cur_phase in phases:
                break

            # fallback for uws 1.0
            if LooseVersion(self._job["version"]) < LooseVersion("1.1"):
                sleep(interval)
                interval = min(120, interval * increment)

        return self

    def delete(self):
        """
        deletes the job. this object will become invalid.
        """
        try:
            response = requests.post(self.url, data={"ACTION": "DELETE"})
            response.raise_for_status()
        except requests.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, self.url)

        self._url = None

    def raise_if_error(self):
        """
        raise a exception if theres an error

        Raises
        ------
        DALQueryError
            if theres an error
        """
        if self.phase in ["ERROR", "ABORTED"]:
            raise DALQueryError(
                self._job.get("message", "Unknown Query Error"),
                self.phase, self.url)

    def fetch_result(self):
        """
        returns the result votable if query is finished
        """
        try:
            response = requests.get(self.result_uri, stream=True)
            response.raise_for_status()
        except requests.RequestException as ex:
            self._update()
            # we propably got a 404 because query error. raise with error msg
            self.raise_if_error()
            raise DALServiceError.from_except(ex, self.url)

        response.raw.read = partial(
            response.raw.read, decode_content=True)
        return TAPResults(votableparse(response.raw.read), self.result_uri)


class TAPQuery(DALQuery):
    """
    a class for preparing an query to an TAP service.  Query constraints
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
            self, baseurl, query, mode="sync", language="ADQL", maxrec=None,
            uploads=None, **keywords):
        """
        initialize the query object with the given parameters

        Parameters
        ----------
        baseurl : str
            the TAP baseurl
        query : str
            the query string
        mode : str
            the query mode (sync | async). default "sync"
        language : str
            the query language. defaults to ADQL
        maxrec : int
            the amount of records to fetch
        uploads : dict
            Files to upload. Uses table name as key and table content as value.
        """
        baseurl = baseurl.rstrip("?")

        super(TAPQuery, self).__init__(baseurl, **keywords)

        self._mode = mode if mode in ("sync", "async") else "sync"
        self._uploads = UploadList.fromdict(uploads or {})

        self["REQUEST"] = "doQuery"
        self["LANG"] = language

        if maxrec:
            self["MAXREC"] = maxrec

        self["QUERY"] = query

        if self._uploads:
            self["UPLOAD"] = self._uploads.param()

    @property
    def queryurl(self):
        return '{baseurl}/{mode}'.format(baseurl=self.baseurl, mode=self._mode)

    def execute_stream(self):
        """
        submit the query and return the raw VOTable XML as a file stream

        Raises
        ------
        DALServiceError
           for errors connecting to or communicating with the service
        DALQueryError
           for errors in the input query syntax
        """

        # theres nothing to execute in non-sync queries
        if self._mode != "sync":
            raise DALServiceError(
                "Cannot execute a non-synchronous query. Use submit instead")

        return super(TAPQuery, self).execute_stream()

    def execute(self):
        """
        submit the query and return the results as a TAPResults instance

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
        return TAPResults(self.execute_votable(), self.queryurl)

    def submit(self):
        """
        Does the request part of the TAP query.
        This function is separated from response parsing because async queries
        return no votable but behave like sync queries in terms of request.
        It returns the requests response.
        """
        url = self.queryurl

        files = {
            upload.name: upload.fileobj()
            for upload in self._uploads
            if upload.is_inline
        }

        response = requests.post(
            url, data=self, stream=True, files=files)
        # requests doesn't decode the content by default
        response.raw.read = partial(response.raw.read, decode_content=True)
        return response


class TAPResults(DALResults):
    """
    The list of matching images resulting from an image (SIA) query.
    Each record contains a set of metadata that describes an available
    image matching the query constraints.  The number of records in
    the results is available via the :py:attr:`nrecs` attribute or by
    passing it to the Python built-in ``len()`` function.

    This class supports iterable semantics; thus,
    individual records (in the form of
    :py:class:`~pyvo.dal.query.Record` instances) are typically
    accessed by iterating over an ``TAPResults`` instance.

    Alternatively, records can be accessed randomly via
    :py:meth:`getrecord` or through a Python Database API (v2)
    Cursor (via :py:meth:`~pyvo.dal.query.DALResults.cursor`).
    Column-based data access is possible via the
    :py:meth:`~pyvo.dal.query.DALResults.getcolumn` method.

    ``TAPResults`` is essentially a wrapper around an Astropy
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

    ``SIAResults`` supports the array item operator ``[...]`` in a
    read-only context.  When the argument is numerical, the result
    is an
    :py:class:`~pyvo.dal.query.Record` instance, representing the
    record at the position given by the numerical index.  If the
    argument is a string, it is interpreted as the name of a column,
    and the data from the column matching that name is returned as
    a Numpy array.
    """

    @property
    def infos(self):
        """
        return the info element as dictionary
        """
        return getattr(self, "_infos", {})

    @property
    def query_status(self):
        """
        return the query status
        """
        return getattr(self, "_infos", {}).get("QUERY_STATUS", None)

    def getrecord(self, index):
        """
        return a representation of a tap result record that follows
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
        return Record(self, index)
