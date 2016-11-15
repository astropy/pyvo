# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
A module for accessing remote source and observation catalogs
"""
from __future__ import print_function, division

import requests
import astropy
import functools
from astropy.table import Column
from datetime import datetime
import time

from . import query
from .query import DALServiceError, DALQueryError
from ..tools import vosi, uws

__all__ = ["search", "escape",
    "TAPService", "TAPQuery", "AsyncTAPJob", "TAPResults"]

def _fix_upload(upload):
    if type(upload) is not tuple:
        upload = ('uri', upload)
    if type(upload[1]) == TAPResults:
        upload = ('uri', upload[1].result_uri)
    return upload

def _fileobj(s):
    if type(s) == astropy.table.table.Table:
        from cStringIO import StringIO
        f = StringIO()
        s.write(output = f, format = "votable")
        f.seek(0)
        return f
    try:
        s = open(s)
    finally:
        return s

def escape(term):
    """
    escapes a term for use in ADQL
    """
    return str(term).replace("'", "''")

def search(url, query, language="ADQL", maxrec=None, uploads=None):
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
    return service.search(query, language, maxrec, uploads)

class TAPResults(query.DALResults):
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


class TAPQuery(query.DALQuery):
    RESULTS_CLASS = TAPResults

    def __init__(self, baseurl, query, mode="sync", language="ADQL",
        maxrec=None, uploads = None):
        """
        initialize the query object with the given parameters

        Parameters
        ----------
        baseurl : str
            the TAP baseurl
        query : str
            the query string / parameters
        mode : str
            the query mode (sync | async). default "sync"
        language : str
            the query language. defaults to ADQL
        maxrec : int
            the amount of records to fetch
        uploads : dict
            Files to upload. Uses table name as key and file name as value
        """
        super(TAPQuery, self).__init__(baseurl, "TAP", "1.0")

        self._query = query
        self._mode = mode if mode in ("sync", "async") else "sync"
        self._language = language
        self._uploads = uploads or {}
        self._uploads = {k: _fix_upload(v) for k, v in self._uploads.items()}
        self._maxrec = maxrec

        self["REQUEST"] = "doQuery"
        self["LANG"] = language

        if maxrec:
            self["MAXREC"] = maxrec

        if isinstance(query, dict):
            self.update(query)
        else:
            self["QUERY"] = query

        if self._uploads:
            upload_param = ';'.join(
                ['{0},{1}{2}'.format(
                    k,
                    'param:' if v[0] == 'inline' else '',
                    v[1] if v[0] == 'uri' else k
                ) for k, v in self._uploads.items()])
            self["UPLOAD"] = upload_param

    def getqueryurl(self):
        return '{0}/{1}'.format(self.baseurl, self._mode)

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
        if self._mode != "sync":
            raise DALServiceError(
                "Cannot execute a non-synchronous query. Use submit instead")

        url = self.getqueryurl()

        try:
            return self.submit().raw
        except requests.RequestException as ex:
            raise DALServiceError.from_except(ex, url, self.protocol,
                self.version)

    def submit(self):
        """
        does the actual request
        """
        url = self.getqueryurl()

        files = {k: _fileobj(v[1]) for k, v in filter(
            lambda x: x[1][0] == 'inline', self._uploads.items())}

        r = requests.post(url, data = self, stream = True,
            files = files)
        r.raise_for_status()
        # requests doesn't decode the content by default
        r.raw.read = functools.partial(r.raw.read, decode_content=True)
        return r


class TAPService(query.DALService):
    """
    a representation of a Table Access Protocol service
    """

    QUERY_CLASS = TAPQuery

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
        super(TAPService, self).__init__(baseurl, "TAP", "1.0")

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
            r = requests.get(
                '{0}/availability'.format(self.baseurl), stream = True)

            # requests doesn't decode the content by default
            r.raw.read = functools.partial(r.raw.read, decode_content=True)

            self._availability = vosi.parse_availability(r.raw)
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
            r = requests.get(
                '{0}/capabilities'.format(self.baseurl), stream = True)

            # requests doesn't decode the content by default
            r.raw.read = functools.partial(r.raw.read, decode_content=True)

            self._capabilities = vosi.parse_capabilities(r.raw)
        return self._capabilities

    @property
    def tables(self):
        """
        returns tables as a flat OrderedDict
        """
        if self._tables is None:
            r = requests.get('{0}/tables'.format(self.baseurl), stream = True)

            # requests doesn't decode the content by default
            r.raw.read = functools.partial(r.raw.read, decode_content=True)

            self._tables = vosi.parse_tables(r.raw)
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

    def run_sync(self, query, language="ADQL", maxrec=None, uploads=None):
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
        q = self.QUERY_CLASS(
            self.baseurl, query, language=language, maxrec=maxrec,
            uploads=uploads)
        return q.execute()

    #alias for service discovery
    search = run_sync

    def run_async(self, query, language="ADQL", maxrec=None, uploads=None):
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
        job = AsyncTAPJob.create(self.baseurl, query, language, maxrec, uploads)
        job = job.run().wait()
        job.raise_if_error()
        result = job.fetch_result()

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
        return AsyncTAPJob.create(self.baseurl, query, language, maxrec,
            uploads)


class AsyncTAPJob(object):
    _job = {}
 
    @classmethod
    def create(cls, baseurl, query, language="ADQL", maxrec = None,
        uploads = None):
        """
        creates a async tap job on the server unter `baseurl`

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
        query = TAPService.QUERY_CLASS(
            baseurl, query, mode="async", language=language, maxrec=maxrec,
            uploads=uploads)
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

    def _update(self):
        """
        updates local job infos with remote values
        """
        try:
            r = requests.get(self.url, stream = True)
            r.raise_for_status()
        except requests.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, self.url, "TAP", "1.0")
        
        # requests doesn't decode the content by default
        r.raw.read = functools.partial(r.raw.read, decode_content=True)

        self._job.update(uws.parse_job(r.raw))

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
    def jobId(self):
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
            r = requests.post("{}/executionduration".format(self.url),
                data = {"EXECUTIONDURATION": str(value)})
            r.raise_for_status()
        except requests.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, self.url, "TAP", "1.0")
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
        except:
            pass

        try:
            r = requests.post("{}/destruction".format(self.url),
                data = {"DESTRUCTION": value.strftime("%Y-%m-%dT%H:%M:%SZ")})
            r.raise_for_status()
        except requests.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, self.url, "TAP", "1.0")
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
        self.raise_if_error()
        return self._job["results"]

    @property
    def result_uri(self):
        """
        the first result uri
        """
        try:
            return iter(self.result_uris.values()).next()
        except StopIteration:
            return None

    def run(self):
        """
        starts the job / change phase to RUN
        """
        try:
            r = requests.post('{}/phase'.format(self.url),
                data = {"PHASE": "RUN"})
            r.raise_for_status()
        except requests.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, self.url, "TAP", "1.0")

        return self

    def abort(self):
        """
        aborts the job / change phase to ABORT
        """
        try:
            r = requests.post('{}/phase'.format(self.url),
                data = {"PHASE": "ABORT"})
            r.raise_for_status()
        except requests.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, self.url, self.protocol,
                self.version)

        return self

    def wait(
        self, phases={"COMPLETED", "ABORTED", "ERROR"}, interval=1.0,
        increment=1.2, giveup_after=None, timeout=None):
        """
        waits for the job to reach the given phases.

        Parameters
        ----------
        phases : list
            phases to wait for
        interval : float
            poll interval in seconds. defaults to 1
        increment : float
            poll interval increments. defaults to 1.2
        giveup_after : int
            raise an :py:class`~pyvo.dal.query.DALServiceError` after n tries
        timeout : float
            raise an :py:class`~pyvo.dal.query.DALServiceError` after n seconds

        Raises
        ------
        DALServiceError
            if the timeout is exceeded
        """
        attempts = 0
        start_time = time.time()

        while True:
            cur_phase = self.phase
            if cur_phase in phases:
                break
            time.sleep(interval)
            interval = min(120, interval * increment)
            attempts += 1
            if any((
                giveup_after and attempts > giveup_after,
                timeout and start_time + timeout < time.time() 
            )):
                raise DALServiceError(
                    "None of the states in {0} were reached in time.".format(
                    repr(phases)), self.url, "TAP", "1.0")

        return self

    def delete(self):
        """
        deletes the job. this object will become invalid.
        """
        try:
            r = requests.post(self.url, data = {"ACTION": "DELETE"})
            r.raise_for_status()
        except requests.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, self.url, "TAP", "1.0")

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
                self._job.get("message", "Query was aborted."),
                self.phase, self.url, "TAP", "1.0")

    def fetch_result(self):
        """
        returns the result votable if query is finished
        """
        try:
            response = requests.get(self.result_uri, stream = True)
            response.raise_for_status()
        except IOError as ex:
            self._update()
            # we propably got a 404 because query error. raise with error msg
            self.raise_if_error()
            raise DALServiceError.from_except(ex, self.url, "TAP", "1.0")

        return TAPResults(
            query._votableparse(response.raw.read), self.result_uri,
            "TAP", "1.0")
