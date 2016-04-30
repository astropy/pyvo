# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
A module for accessing remote source and observation catalogs
"""
from __future__ import print_function, division

import requests
import xml.etree.ElementTree as ET

from . import query
from .query import DALServiceError
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
        q.setparam("REQUEST", "doQuery")
        q.setparam("LANG", language)

        if isinstance(query, dict):
            for k, v in query:
                q.setparam(k.upper(), v)
        else:
            q.setparam("QUERY", query)

        if self._uploads:
            upload_param = ';'.join(
                ['{0},param:{0}'.format(k) for k in self._uploads])
            q.setparam("UPLOAD", upload_param)

        return q.execute()

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
            url = self.getqueryurl()

            files = {k: open(v) for k, v in self._uploads.items()}

            r = requests.post(url, params = self._param, stream = True,
                files = files)

            return r.raw
        except IOError as ex:
            raise DALServiceError.from_except(ex, url, self.protocol,
                self.version)
