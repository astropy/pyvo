# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
A module for accessing remote source and observation catalogs
"""
from __future__ import print_function, division

import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import time

from . import query
from .query import DALServiceError, DALQueryError
from ..tools import vosi

__all__ = ["TAPService", "TAPQuery"]

class TAPService(query.DALService):
    """
    a representation of a Table Access Protocol service
    """

    _capabilities = None

    def __init__(self, baseurl):
        """
        instantiate a Tablee Access Protocol service

        Parameters
        ----------
        baseurl :  str
           the base URL that should be used for forming queries to the service.
        protocol : str
           The protocol implemented by the service, e.g., "scs", "sia",
           "ssa", and so forth.
        version : str
           The protocol version, e.g, "1.0", "1.2", "2.0".
        resmeta : dict
           an optional dictionary of properties about the service
        """
        super(TAPService, self).__init__(baseurl, "tap")

    @property
    def capabilities(self):
        """returns a service property.

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
            r = requests.get('{0}/capabilities'.format(self._baseurl))
            self._capabilities = vosi.parse_capabilities(r.text)
        return self._capabilities

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
            The query string
        language : str
            The query language
        """
        q = TAPQuery(self._baseurl, self._version, language, maxrec, uploads)
        self._run(q, query)

        return q.execute()

    def run_async(self, query, language = "ADQL", maxrec = None,
        uploads = None):
        """
        runs async query and returns a TAPQueryAsync object

        Parameters
        ----------
        query : str, dict
            The query string
        language : str
            The query language
        """
        q = TAPQueryAsync(self._baseurl, self._version, language, maxrec,
            uploads)
        self._run(q, query)
        q.submit()
        return q

class TAPQuery(query.DALQuery):
    def __init__(self, baseurl, version="1.0", language = "ADQL", maxrec = None,
        uploads = None):
        """
        initialize the query object with a baseurl
        """
        self._language = language
        self._uploads = uploads
        self._maxrec = maxrec

        super(TAPQuery, self).__init__(baseurl, "tap")

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

        files = {k: open(v) for k, v in self._uploads.items()}

        r = requests.post(url, params = self._param, stream = True,
            files = files)

        return r.raw

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

        try:
            return self._submit()
        except IOError as ex:
            raise DALServiceError.from_except(ex, url, self.protocol,
                self.version)

class TAPQueryAsync(TAPQuery):
    def _update(self):
        """
        updates job infos
        """
        url = self.getqueryurl()

        r = requests.get(url).text
        self._job.update(vosi.parse_job(r))

    def get_job(self):
        #keep it up to date
        self._update()
        return getattr(self, "_job", {})

    def getqueryurl(self, lax = False):
        if getattr(self, "_job", None) is not None and "jobId" in self._job:
            return '{0}/async/{1}'.format(self._baseurl, self._job["jobId"])
        return '{}/async'.format(self._baseurl)

    @property
    def phase(self):
        self._update()
        return self._job["phase"]

    @property
    def execution_duration(self):
        self._update()
        return self._job["executionDuration"]

    @execution_duration.setter
    def execution_duration(self, value):
        r = requests.post("{}/executionduration".format(self.getqueryurl()),
            params = {"EXECUTIONDURATION": str(value)})
        self._job["executionDuration"] = value

    @property
    def destruction(self):
        self._update()
        return self._job["destruction"]

    @destruction.setter
    def destruction(self, value):
        try:
            #is string? easier to ask for forgiveness
            value = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        except:
            pass

        r = requests.post("{}/destruction".format(self.getqueryurl()),
            params = {"DESTRUCTION": value.strftime("%Y-%m-%dT%H:%M:%SZ")})
        self._job["destruction"] = value

    @property
    def quote(self):
        self._update()
        return self._job["quote"]

    @property
    def owner(self):
        self._update()
        return self._job["owner"]

    def submit(self):
        r = self._submit().read()
        self._job = vosi.parse_job(r)

    def start(self):
        r = requests.post('{}/phase'.format(self.getqueryurl()),
            params = {"PHASE": "RUN"})

    def abort(self):
        r = requests.post('{}/phase'.format(self.getqueryurl()),
            params = {"PHASE": "ABORT"})

    def run(self):
        self.start()
        self.wait(["COMPLETED", "ABORTED", "ERROR"])
        self.raise_if_error()

    def wait(self, phases, interval = 1, increment = 1.2, giveup_after = None):
        attempts = 0
        url = self.getqueryurl()

        while True:
            cur_phase = self.phase
            if cur_phase in phases:
                break
            time.sleep(interval)
            poll_interval = min(120, interval * increment)
            attempts += 1
            if giveup_after and attempts > giveup_after:
                raise DALServiceError(
                    "None of the states in {0} were reached in time.".format(
                    repr(phases)), url, protocol = self.protocol,
                    version = self.version
                )

    def delete(self):
        r = requests.post(self.getqueryurl(), params = {"ACTION": "DELETE"})

    def raise_if_error(self):
        phase = self.phase
        url = self.getqueryurl()

        if phase in ["ERROR", "ABORTED"]:
            raise DALQueryError(self._job.get("message", "Query was aborted."),
                phase, url, self.protocol, self.version)

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
