# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
A module for accessing remote source and observation catalogs
"""
from __future__ import print_function, division

import requests
import astropy
from astropy.io.votable.tree import VOTableFile, Resource, Table
from astropy.table import Column
from datetime import datetime
import time

from . import query
from .query import DALServiceError, DALQueryError
from ..tools import vosi, uws

__all__ = ["TAPService", "TAPQuery", "AsyncTAPJob", "TAPResults"]

def search(url, query, language = "ADQL", maxrec = None, uploads = None):
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

class TAPService(query.DALService):
    """
    a representation of a Table Access Protocol service
    """

    _availability = (None, None)
    _capabilities = None
    _tables = None

    def __init__(self, baseurl, resmeta = None):
        """
        instantiate a Tablee Access Protocol service

        Parameters
        ----------
        baseurl :  str
           the base URL that should be used for forming queries to the service.
        """
        super(TAPService, self).__init__(baseurl, "tap", "1.0", resmeta)

    @property
    def availability(self):
        """returns availability as a tuple in the following form:
        [0] : bool
            whether the service is available or not
        [1] : datetime
            the time since the server is running
        """
        if self._availability == (None, None):
            r = requests.get(
                '{0}/availability'.format(self._baseurl), stream = True)
            self._availability = vosi.parse_availability(r.raw)
        return self._availability

    @property
    def available(self):
        return self.availability[0]

    @property
    def up_since(self):
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
                '{0}/capabilities'.format(self._baseurl), stream = True)
            self._capabilities = vosi.parse_capabilities(r.raw)
        return self._capabilities

    @property
    def tables(self):
        """
        returns tables as a flat OrderedDict
        """
        if self._tables is None:
            r = requests.get('{0}/tables'.format(self._baseurl), stream = True)
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

    def _run(self, q, query):
        """
        sets query parameters
        """
        q.setparam("REQUEST", "doQuery")
        q.setparam("LANG", q._language)

        if isinstance(q, dict):
            for k, v in query:
                q.setparam(k.upper(), v)
        else:
            q.setparam("QUERY", query)

        if q._maxrec:
            q.setparam("MAXREC", q._maxrec)

    def run_sync(self, query, language = "ADQL", maxrec = None, uploads = None):
        """
        runs sync query and returns its result

        Parameters
        ----------
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
            the query result

        See Also
        --------
        TAPResults
        """
        q = TAPQuery(self._baseurl, self._version, language, maxrec, uploads)
        self._run(q, query)

        return q.execute()

    #alias for service discovery
    search = run_sync

    def _run_async(self, query, language = "ADQL", maxrec = None,
        uploads = None):
        q = AsyncTAPJob(self._baseurl, self._version, language, maxrec,
            uploads)
        self._run(q, query)
        return q

    def run_async(self, query, language = "ADQL", maxrec = None,
        uploads = None):
        """
        submit and start a async query and returns a AsyncTAPJob object

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
        AsyncTAPJob
            the query instance

        See Also
        --------
        AsyncTAPJob
        """
        q = self._run_async(query, language, maxrec, uploads)
        return q.submit().run()

    def submit_job(self, query, language = "ADQL", maxrec = None,
        uploads = None):
        """
        submit a async query without starting it and returns a AsyncTAPJob
        object

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
        AsyncTAPJob
            the query instance

        See Also
        --------
        AsyncTAPJob
        """
        return self._run_async(query, language, maxrec, uploads)

class TAPQuery(query.DALQuery):
    def __init__(self, baseurl, version="1.0", language = "ADQL", maxrec = None,
        uploads = None):
        """
        initialize the query object with the given parameters

        Parameters
        ----------
        baseurl : str
            the TAP baseurl
        version : str
            the version string
        language : str
            the query language. defaults to ADQL
        maxrec : int
            the amount of records to fetch
        uploads : dict
            Files to upload. Uses table name as key and file name as value
        """
        self._language = language
        self._uploads = uploads or {}
        self._maxrec = maxrec

        super(TAPQuery, self).__init__(baseurl, "tap", version)

        if self._uploads:
            upload_param = ';'.join(
                ['{0},param:{0}'.format(k) for k in self._uploads])
            self.setparam("UPLOAD", upload_param)

    def getqueryurl(self, lax = False):
        return '{}/sync'.format(self._baseurl)

    def _submit(self):
        """
        does the actual request
        """
        url = self.getqueryurl()

        def _fileobj(s):
            if type(s) == astropy.table.table.Table:
                from cStringIO import StringIO
                f = StringIO()
                s.write(output = f, format = "votable")
                return f
            try:
                s = open(s)
            finally:
                return s

        files = dict((k, _fileobj(v)) for (k, v) in self._uploads.items())

        r = requests.post(url, params = self._param, stream = True,
            files = files)
        return r

    def execute(self):
        """
        submit the query and return the results as a Results subclass instance

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
        return TAPResults(self.execute_votable(), self.getqueryurl(True))


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
        url = self.getqueryurl()

        try:
            return self._submit().raw
        except IOError as ex:
            raise DALServiceError.from_except(ex, url, self.protocol,
                self.version)

class AsyncTAPJob(TAPQuery):
    _job = {}

    def _update(self):
        """
        updates job infos
        """
        url = self.getqueryurl()

        try:
            r = requests.get(url, stream = True)
            r.raise_for_status()
        except request.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, url, self.protocol,
                self.version)
        self._job.update(uws.parse_job(r.raw))

    @property
    def job(self):
        #keep it up to date
        self._update()
        return self._job

    def getqueryurl(self, lax = False):
        if getattr(self, "_job", None) is not None and "jobId" in self._job:
            return '{0}/async/{1}'.format(self._baseurl, self._job["jobId"])
        return '{}/async'.format(self._baseurl)

    @property
    def jobId(self):
        """
        the job id
        """
        return self._job["jobId"]

    @property
    def phase(self):
        """
        the current query phase. One of
        """
        self._update()
        return self._job["phase"]

    @property
    def execution_duration(self):
        """
        maximum execution duration. Changeable
        """
        self._update()
        return self._job["executionDuration"]

    @execution_duration.setter
    def execution_duration(self, value):
        """
        maximum execution duration. Changeable

        Parameters
        ----------
        value : int
            seconds after the query execution is aborted
        """
        url = self.getqueryurl()

        try:
            r = requests.post("{}/executionduration".format(url),
                params = {"EXECUTIONDURATION": str(value)})
            r.raise_for_status()
        except request.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, url, self.protocol,
                self.version)
        self._job["executionDuration"] = value

    @property
    def destruction(self):
        """
        datetime after which the job results are deleted automatically.
        Changeable
        """
        self._update()
        return self._job["destruction"]

    @destruction.setter
    def destruction(self, value):
        """
        datetime after which the job results are deleted automatically.
        Changeable

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

        url = self.getqueryurl()

        try:
            r = requests.post("{}/destruction".format(url),
                params = {"DESTRUCTION": value.strftime("%Y-%m-%dT%H:%M:%SZ")})
            r.raise_for_status()
        except request.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, url, self.protocol,
                self.version)
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

    def submit(self):
        """
        submits the job to the server.
        """
        r = self._submit()
        self._job = uws.parse_job(r.raw)

        return self

    def run(self):
        """
        starts the job / change phase to RUN
        """
        try:
            r = requests.post('{}/phase'.format(self.getqueryurl()),
                params = {"PHASE": "RUN"})
            r.raise_for_status()
        except request.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, url, self.protocol,
                self.version)

        return self

    def abort(self):
        """
        aborts the job / change phase to ABORT
        """
        url = self.getqueryurl()

        try:
            r = requests.post('{}/phase'.format(self.getqueryurl()),
                params = {"PHASE": "ABORT"})
            r.raise_for_status()
        except request.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, url, self.protocol,
                self.version)

        return self

    def wait(self, phases = ["COMPLETED", "ABORTED", "ERROR"], interval = 1,
        increment = 1.2, giveup_after = None):
        """
        waits for the job to reach the given phases.

        Parameters
        ----------
        phases : list
            phases to wait for
        interval : int
            poll interval in seconds. defaults to 1
        increment : float
            poll interval increments. defaults to 1.2
        giveup_after : int
            raise an :py:class`~pyvo.dal.query.DALServiceError` after n seconds

        Raises
        ------
        DALServiceError
            if the timeout is exceeded
        """
        attempts = 0
        url = self.getqueryurl()

        while True:
            cur_phase = self.phase
            if cur_phase in phases:
                break
            time.sleep(interval)
            interval = min(120, interval * increment)
            attempts += 1
            if giveup_after and attempts > giveup_after:
                raise DALServiceError(
                    "None of the states in {0} were reached in time.".format(
                    repr(phases)), url, protocol = self.protocol,
                    version = self.version
                )

        return self

    def delete(self):
        """
        deletes the job. this object will become invalid.
        """
        url = self.getqueryurl()
        try:
            r = requests.post(url, params = {"ACTION": "DELETE"})
            r.raise_for_status()
        except request.exceptions.RequestException as ex:
            raise DALServiceError.from_except(ex, url, self.protocol,
                self.version)

    def raise_if_error(self):
        """
        raise a exception if theres an error

        Raises
        ------
        DALQueryError
            if theres an error
        """
        phase = self.phase
        url = self.getqueryurl()

        if phase in ["ERROR", "ABORTED"]:
            raise DALQueryError(self._job.get("message", "Query was aborted."),
                phase, url, self.protocol, self.version)

    def fetch(self):
        """
        This method is an alias for execute, as it is technically the same
        (fetching the votable), but doesnt fit logically (the query is already
        executed at this point)
        """
        return self.execute()

    def execute_stream(self):
        """
        get the result and return the raw VOTable XML as a file stream

        Raises
        ------
        DALServiceError
           for errors connecting to or communicating with the service
        DALQueryError
           for errors in the input query syntax
        """
        url = '{0}/results/result'.format(self.getqueryurl())

        if self.phase != "COMPLETED":
            raise DALServiceError(
                "Can not get the result because the query isn't completed.")

        try:
            r = requests.get(url, stream = True)
            r.raise_for_status()
            return r.raw
        except IOError as ex:
            self._update()

            # we propably got a 404 because query error. raise with error msg
            self.raise_if_error()
            raise DALServiceError.from_except(ex, url, self.protocol,
                self.version)

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

    def getcolumn(self, name):
        col = super(TAPResults, self).getcolumn(name)
        field = self.votable.get_field_by_id_or_name(name)
        try:
            #append unit
            return col * field.unit
        except (ValueError, TypeError):
            #return unchanged
            return col

    def save(self, outfile):
        """
        saves the votable to outfile

        Parameters
        ----------
        outfile : str
            destination filename
        """
        votf = VOTableFile()
        table = self.votable
        resource = Resource()

        resource.tables.append(table)
        votf.resources.append(resource)

        votf.to_xml(outfile)

    def append_column(self, data, **kwargs):
        """
        appends another column to the votable
        """
        if "length" not in kwargs:
            kwargs["length"] = len(data)
        if "dtype" not in kwargs:
            kwargs["dtype"] = data.dtype

        ucd = kwargs.pop("ucd", None)

        table = self.votable.to_table()

        table.add_column(Column(data, **kwargs))
        self._fldnames.append(kwargs["name"])

        self.votable = Table.from_table(self.votable, table)# ???

        self.votable.get_field_by_id_or_name(kwargs["name"]).ucd = ucd
