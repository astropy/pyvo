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
        q = TAPQuery(self._baseurl, self._version, language)
        q.setparam("REQUEST", "doQuery")
        q.setparam("LANG", language)
        if isinstance(query, dict):
            for k, v in query:
                q.setparam(k, v)
        else:
            q.setparam("QUERY", query)

        return q.execute()

class TAPQuery(query.DALQuery):
    def __init__(self, baseurl, version="1.0", language = "ADQL"):
        """
        initialize the query object with a baseurl
        """
        self._language = language
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
            r = requests.post(url, params = self._param, stream = True)
            return r.raw
        except IOError as ex:
            raise DALServiceError.from_except(ex, url, self.protocol,
                self.version)
