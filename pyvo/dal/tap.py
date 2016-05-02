# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
A module for accessing remote source and observation catalogs
"""
from __future__ import print_function, division

import requests
import xml.etree.ElementTree as ET

from . import query
from .query import DALServiceError, DALQueryError
from ..tools import vosi

__all__ = ["TAPService", "TAPQuery"]

class TAPService(query.DALService):
    """
    a representation of a Table Access Protocol service
    """

    _capabilities = None
    _uploads = {}

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

    def add_upload_file(self, tablename, filename):
        #TODO: perhaps prevent upload when not supported
        self._uploads[tablename] = filename

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

        if self._uploads:
            upload_param = ';'.join(
                ['{0},param:{0}'.format(k) for k in self._uploads])
            q.setparam("UPLOAD", upload_param)

    def run_sync(self, query, language = "ADQL"):
        """
        runs sync query and returns its result

        Parameters
        ----------
        query : str, dict
            The query string
        language : str
            The query language
        """
        q = TAPQuery(self._baseurl, self._version, language, self._uploads)
        self._run(q, query)

        return q.execute()

    def run_async(self, query, language = "ADQL"):
        """
        runs async query and returns a TAPQueryAsync object

        Parameters
        ----------
        query : str, dict
            The query string
        language : str
            The query language
        """
        q = TAPQueryAsync(self._baseurl, self._version, language, self._uploads)
        self._run(q, query)
        q.submit()
        return q

class TAPQuery(query.DALQuery):
    def __init__(self, baseurl, version="1.0", language = "ADQL",
        uploads = None):
        """
        initialize the query object with a baseurl
        """
        self._language = language
        self._uploads = uploads
        super(TAPQuery, self).__init__(baseurl, "tap")

    def getqueryurl(self, lax = False):
        return '{}/sync'.format(self._baseurl)

    def _submit(self):
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

    def submit(self):
        r = self._submit().read()
        self._job = vosi.parse_job(r)

    def run(self):
        r = requests.post('{}/phase'.format(self.getqueryurl()),
            params = {"PHASE": "RUN"})

    def abort(self):
        r = requests.post('{}/phase'.format(self.getqueryurl()),
            params = {"PHASE": "ABORT"})

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
            if self._job["phase"] == "ERROR":
                raise DALQueryError(self._job.get("message", ""), "Error",
                    url, self.protocol, self.version)
            raise DALServiceError.from_except(ex, url, self.protocol,
                self.version)
