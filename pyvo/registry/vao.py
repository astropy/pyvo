# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
a module for basic VO Registry interactions.  

A VO registry is a database of VO resources--data collections and
services--that are available for VO applications.  Typically, it is 
aware of the resources from all over the world.  A registry can find 
relevent data collections and services through search
queries--typically, subject-based.  The registry responds with a list
of records describing matching resources.  With a record in hand, the 
application can use the information in the record to access the 
resource directly.  Most often, the resource is a data service that
can be queried for individual datasets of interest.  

This module provides basic, low-level access to the VAO Registry at 
STScI using (proprietary) VOTable-based services.  In most cases,
the Registry task, with its higher-level features (e.g. result caching
and resource aliases), can be a more convenient interface.  The more  
basic interface provided here allows developers to code their own 
interaction models.  
"""
from __future__ import print_function, division

from ..dal import query as dalq
from ..dal import sia, ssa, sla, scs, tap
from urllib import quote_plus, urlopen
import re

import numpy.ma as _ma

try:
	from astropy.utils.decorators import deprecated
except ImportError:
	def deprecated(version):
		return lambda f: f


__all__ = [ "search", "RegistryService", "RegistryQuery", 
                      "RegistryResults", "SimpleResource" ]

@deprecated("0.5")
def search(keywords=None, servicetype=None, waveband=None, sqlpred=None):
    """
    execute a simple query to the VAO registry.  

    Parameters
    ----------
    keywords : str or list of str
       keyword terms to match to registry records.  
       Use this parameter to find resources related to a 
       particular topic.
    servicetype : str
       the service type to restrict results to.
       Allowed values include,
       'catalog'  (synonyms: 'table', 'scs', 'conesearch', 'ConeSearch'), 
       'image'    (synonyms: 'sia', 'SimpleImageAccess'), 
       'spectrum' (synonyms: 'ssa', 'ssap', 'SimpleSpectralAccess'),
       'line'     (synonyms: 'sla', 'slap', 'SimpleLineAccess')
       'database' (synonyms: 'tap','TableAccess').
    waveband : str
       the name of a desired waveband; resources returned 
       will be restricted to those that indicate as having
       data in that waveband.  Allowed, case-insensitive 
       values include 'Radio', 'Millimeter', 'Infrared'
       (synonym: 'IR'), 'Optical', 'UV', 'EUV', 'X-ray' 
       (synonym: 'Xray').
    sqlpred : str
       an SQL WHERE predicate (without the leading "WHERE") 
       that further contrains the search against supported 
       keywords.

    Returns
    -------
    RegistryResults
       a container holding a table of matching resource (e.g. services)

    See Also
    --------
    RegistryResults
    """
    reg = RegistryService()
    return reg.search(keywords, servicetype, waveband, sqlpred)


@deprecated("0.5")
class RegistryService(dalq.DALService):
    """
    a class for submitting searches to the VAO registry.  
    """

    STSCI_REGISTRY_BASEURL = "http://vao.stsci.edu/directory/NVORegInt.asmx/"

    def __init__(self, baseurl=None, resmeta=None, version="1.0"):
        """
        connect to an STScI registry at the given URL
        Parameters
        ----------
        baseurl : str
           the base URL for submitting search queries to the 
           service.  If None, it will default to the STScI 
           public registry
        resmeta : str
           an optional dictionary of properties about the service
        """
        if not baseurl:  baseurl = self.STSCI_REGISTRY_BASEURL
        if not baseurl.endswith("/"): baseurl += "/"

        super(RegistryService, self).__init__(baseurl, "vaoreg", 
                                              version, resmeta)


    def search(self, keywords=None, servicetype=None, 
               waveband=None, orkw=False, sqlpred=None):
        """
        execute a simple registry search of the specified
        keywords. 

        Parameters
        ----------
        keywords : str or list of str
           keyword terms to match to registry records.  
           Use this parameter to find resources related to a 
           particular topic.
        servicetype : str
           the service type to restrict results to.
           Allowed values include,
           'catalog'  (synonyms: 'table', 'scs', 'conesearch', 'ConeSearch'), 
           'image'    (synonyms: 'sia', 'SimpleImageAccess'), 
           'spectrum' (synonyms: 'ssa', 'ssap', 'SimpleSpectralAccess'),
           'line'     (synonyms: 'sla', 'slap', 'SimpleLineAccess')
           'database' (synonyms: 'tap','TableAccess').
        waveband : str
           the name of a desired waveband; resources returned 
           will be restricted to those that indicate as having
           data in that waveband.  Allowed, case-insensitive 
           values include 'Radio', 'Millimeter', 'Infrared'
           (synonym: 'IR'), 'Optical', 'UV', 'EUV', 'X-ray' 
           (synonym: 'Xray').
        orkw : bool
           If true, the keywords will be OR-ed together,
           and returned records will match at least one of 
           the keywords.  If false (default), the keywords qill 
           be AND-ed, requiring the returned records to to 
           match all of the keywords.  
        sqlpred : str
           an SQL WHERE predicate (without the leading "WHERE") 
           that further contrains the search against supported 
           keywords.

        Returns
        -------
        RegistryResults
           a container holding a table of matching resource (e.g. services)

        See Also
        --------
        RegistryResults
        """
        srch = self.create_query(keywords, servicetype, waveband, orkw, sqlpred)
        # print(srch.getqueryurl())
        return srch.execute()
        
    
    def resolve(self, ivoid):
        """
        Resolve the identifier against the registry, returning a
        resource record.  

        Parameters
        ----------
        ivoid : str
            the IVOA Identifier of the resource
        """
        srch = self.create_query()
        srch.addpredicate("identifier='{0}'".format(ivoid))
        res = srch.execute()
        return res.getrecord(0)

    def create_query(self, keywords=None, servicetype=None, 
                     waveband=None, orkw=False, sqlpred=None):
        """
        create a RegistryQuery object that can be refined or saved
        before submitting.  

        Parameters
        ----------
        keywords : str
           a string giving a single term or a python list 
           of terms to match to registry records.  
        servicetype : str
           the service type to restrict results to; 
           allowed values include, 
           'catalog'  (synonyms: 'table', 'scs', 'conesearch', 'ConeSearch'), 
           'image'    (synonyms: 'sia', 'SimpleImageAccess'), 
           'spectrum' (synonyms: 'ssa', 'ssap', 'SimpleSpectralAccess'),
           'line'     (synonyms: 'sla', 'slap', 'SimpleLineAccess')
           'database' (synonyms: 'tap','TableAccess').
        waveband : str
           the name of a desired waveband; resources returned 
           will be restricted to those that indicate as having
           data in that waveband.  Allowed, case-insensitive 
           values include 'Radio', 'Millimeter', 'Infrared'
           (synonym: 'IR'), 'Optical', 'UV', 'EUV', 'X-ray' 
           (synonym: 'Xray').
        orkw : bool
           If true, the keywords will be OR-ed together,
           and returned records will match at least one of 
           the keywords.  If false (default), the keywords qill 
           be AND-ed, requiring the returned records to to 
           match all of the keywords.  
        sqlpred : str
           an SQL WHERE predicate (without the leading "WHERE") 
           that further contrains the search against supported 
           keywords.

        See Also
        --------
        RegistryQuery
        """
        srch = RegistryQuery(self._baseurl)
        if sqlpred:
            srch.addpredicate(sqlpred)
        if waveband:
            srch.waveband = waveband
        if servicetype:
            srch.servicetype = servicetype
        if keywords:
            srch.addkeywords(keywords)
        if isinstance(orkw, bool):
            srch.or_keywords(orkw)
        elif orkw is not None:
            raise ValueError("create_query: orkw parameter not a bool: " +
                             str(orkw))
        return srch


@deprecated("0.5")
class RegistryQuery(dalq.DALQuery):
    """
    a representation of a registry query that can be built up over
    successive method calls and then executed.  An instance is normally
    obtained via a call to RegistrySearch.create_query()
    """
    
    SERVICE_NAME = "VOTCapBandPredOpt"
#    SERVICE_NAME = "VOTCapability"
    RESULTSET_TYPE_ARG = "VOTStyleOption=2"
    ALLOWED_WAVEBANDS = "Radio Millimeter Infrared Optical UV".split() + \
        "EUV X-ray Gamma-ray".split()
    WAVEBAND_SYN = { "ir":  "Infrared",
                     "IR":  "Infrared",
                     "uv":  "UV",
                     "euv": "EUV",
                     "xray": "X-ray" }
                     
    ALLOWED_CAPS = { "table": "ConeSearch", 
                     "catalog": "ConeSearch", 
                     "scs": "ConeSearch", 
                     "conesearch": "ConeSearch", 
                     "image": "SimpleImageAccess",
                     "sia": "SimpleImageAccess",
                     "spectra": "SimpleSpectralAccess",
                     "spectrum": "SimpleSpectralAccess",
                     "ssa": "SimpleSpectralAccess",
                     "ssap": "SimpleSpectralAccess",
                     "line": "SimpleLineAccess",
                     "sla": "SimpleLineAccess",
                     "slap": "SimpleLineAccess",
                     "tap": "TableAccess",
                     "database": "TableAccess",
                     "tableAccess": "TableAccess",
                     "simpleImageAccess": "SimpleImageAccess",
                     "simpleLineAccess": "SimpleLineAccess",
                     "simpleSpectralAccess": "SimpleSpectralAccess"  }
                     

    def __init__(self, baseurl=None, orKeywords=False, version="1.0"):
        """
        create the query instance

        Parameters
        ----------
        baseurl : str
           the base URL for the VAO registry.  If None, it will
           be set to the public VAO registry at STScI.
        orKeywords : bool
           if True, keyword constraints will by default be 
           OR-ed together; that is, a resource that matches 
           any of the keywords will be returned.  If FALSE,
           the keywords will be AND-ed, thus requiring a 
           resource to match all the keywords.  
        """
        if not baseurl:  baseurl = RegistryService.STSCI_REGISTRY_BASEURL
        super(RegistryQuery, self).__init__(baseurl, "vaoreg", version)
        self._kw = []          # list of individual keyword phrases
        self._preds = []       # list of SQL predicates
        self._svctype = None
        self._band = None
        self._orKw = orKeywords
        self._doSort = True
        self._dalonly = False

    @property
    def keywords(self):
        """
        return the current set of keyword constraints

        To update, use addkeywords(), removekeywords(), or clearkeywords().
        """
        return list(self._kw)

    def addkeywords(self, keywords):
        """
        add keywords that should be added to this query.  Keywords 
        are searched against key fields in the registry record.  A
        keyword can in fact be a phrase--a sequence of words; in this
        case the sequence of words must appear verbatim in the record
        for that record to be matched. 

        Parameters
        ----------
        keywords : str or list of str  
            either a single keyword phrase (as a string) 
            or a list of keyword phrases to add to the 
            query.  
        """
        if isinstance(keywords, str):
            keywords = [keywords]
        self._kw.extend(keywords)

    def removekeywords(self, keywords):
        """
        remove the given keyword or keywords from the query.  A
        keyword can in fact be a phrase--a sequence of words; in this
        case, the phrase will be remove.  

        Parameters
        ----------
        keywords : str or list of str    
            either a single keyword phrase (as a string) 
            or a list of keyword phrases to remove from
            the query.  
        """
        if isinstance(keywords, str):
            keywords = [keywords]
        for kw in keywords:
            self._kw.remove(kw)

    def clearkeywords(self):
        """
        remove all keywords that have been added to this query.
        """
        self._kw = []

    def or_keywords(self, ored):
        """
        set whether keywords are OR-ed or AND-ed together.  When
        the keywords are OR-ed, returned records will match at 
        least one of the keywords.  When they are AND-ed, the 
        records will match all of the keywords provided.  

        Parameters
        ----------
        ored : bool   
            true, if the keywords should be OR-ed; false,
            if they should be AND-ed.
        """
        if not isinstance(ored, bool):
            raise ValueError("RegistryQuery.or_keyword: value not a bool")
        self._orKw = ored

    def will_or_keywords(self):
        """
        Return true if the keywords will be OR-ed.  
        """
        return self._orKw

    @property
    def servicetype(self):
        """
        the type of service that query results will be restricted to.
        """
        return self._svctype
    @servicetype.setter
    def servicetype(self, val):
        if not val:
            raise ValueError("missing serviceType value");
        if len(val) < 2:
            raise ValueError("unrecognized serviceType value: " + val);

        # uncapitalize
        if val[0].upper() == val[0]:
            val = val[0].lower() + val[1:]

        if val not in self.ALLOWED_CAPS.keys():
            raise ValueError("unrecognized servicetype value: " + val);
                             
        self._svctype = val
    @servicetype.deleter
    def servicetype(self):
        self._svctype = None

    @property
    def waveband(self):
        """
        the waveband to restrict the query by.  The query results will 
        include only those resourse that indicate they have data from this 
        waveband.  Allowed values include "Radio", "Millimeter", "Infrared"
        (synonym: "IR"), "Optical", "UV", "EUV", "X-ray" (synonym: "Xray");
        when setting, the value is case-insensitive.  
        """
        return self._band
    @waveband.setter
    def waveband(self, band):
        if band is None:
            self._band = None
            return

        if not isinstance(band, str):
            raise ValueError("band should be a string; got: " + str(type(band)))
        if not band:
            raise ValueError("missing waveband value");
        if len(band) < 2:
            raise ValueError("unrecognized waveband: " + band);

        _band = band
        if self.WAVEBAND_SYN.has_key(band):
            _band = self.WAVEBAND_SYN[band]
        else:
            # capitalize
            _band = _band[0].upper() + _band[1:]
        if _band not in self.ALLOWED_WAVEBANDS:
            raise ValueError("unrecognized waveband: " + band)
        self._band = _band
    @waveband.deleter
    def waveband(self):
        self._band = None

    @property
    def predicates(self):
        """
        the (read-only) list of predicate constraints that will 
        be applied to the query.  These will be AND-ed with all other 
        constraints (including previously added predicates); that is, 
        this constraint must be satisfied in addition to the other 
        constraints to match a particular resource record.  

        To update, use addpredicate(), removepredicate(), or clearpredicate().
        """
        return list(self._preds)

    def addpredicate(self, pred):
        """
        add an SQL search predicate to the query.  This predicate should
        be of form supported by STScI VOTable search services.  This 
        predicate will be AND-ed with all other constraints (including
        previously added predicates); that is, this constraint must be
        satisfied in addition to the other constraints to match a 
        particular resource record.
        """
        self._preds.append(pred)

    def removepredicate(self, pred):
        """
        remove the give predicate from the current set of predicate
        constraints.  
        """
        self._preds.remove(pred)

    def clearpredicates(self):
        """
        remove all previously added predicates.
        """
        self._preds = []

    def execute_votable(self):
        """
        submit the query and return the results as an AstroPy votable instance

        Raises
        ------
        DALServiceError
           for errors connecting to or communicating with the service
        DALFormatError
           for errors parsing the VOTable response
        DALQueryError
           for errors in the input query syntax
        """
        out = dalq.DALQuery.execute_votable(self)
        res = dalq.DALResults(out)
        tbl = res.votable

        # We note that the server-side implementation of the service will 
        # include all of the capability records of resource that have 
        # capabilities of the given type.  Consequently, the results includes
        # capabilites that are not of the requested type.

        # filter out service types that don't match
        if self.servicetype:
            cap = self._toCapConst(self.servicetype).encode('utf-8')
            tbl.array = \
                _ma.array(tbl.array.data[tbl.array.data['capabilityClass']==cap],
                     mask=tbl.array.mask[tbl.array.data['capabilityClass']==cap])
            tbl._nrows = tbl.array.shape[0]

        return out

    def execute(self):
        """
        submit the query and return the results as a RegistryResults
        instance.  

        Raises
        ------
        RegistryServiceError   
            for errors connecting to or communicating with the service
        RegistryQueryError     
            if the service responds with an error, including a query syntax 
            error.  A syntax error should only occur if the query contains 
            non-sensical predicates.
        """
        return RegistryResults(self.execute_votable(), self.getqueryurl())

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
            out = urlopen(url)
            if dalq._is_python3:
                contenttype = out.info().get_content_type()
            else:
                contenttype = out.info().gettype()

            if contenttype == "text/plain":
                # Error message returned
                self._raiseServiceError(out.read())
            elif contenttype != "text/xml":
                # Unexpected response
                raise dalq.DALFormatError("Wrong response format: " + 
                                          contenttype)
            return out

        except IOError as ex:
            raise dalq.DALServiceError.from_except(ex, url)

    def _raiseServiceError(self, response):
        invalidmessage = "System.InvalidOperationException: "
        outmsg = re.sub(r'\n.*', '', response).strip()
        if response.startswith(invalidmessage):
            raise dalq.DALQueryError(outmsg[len(invalidmessage):])
        raise dalq.DALServiceError(outmsg)

    def getqueryurl(self, lax=False):
        """
        return the GET URL that will submit the query and return the 
        results as a VOTable
        """
        url = "{0}{1}?{2}".format(self._baseurl, self.SERVICE_NAME, 
                                  self.RESULTSET_TYPE_ARG)

        if self._band:
            url += "&waveband={0}".format(self._band)
        else:
            url += "&waveband="

        if self._svctype:
            url += "&capability={0}".format(self._toCapConst(self.servicetype))
        else:
            url += "&capability="

        preds = list(self._preds)
        if (self.keywords): 
            preds.append(self.keywords_to_predicate(self.keywords, self._orKw))
        if (preds):
            url += "&predicate={0}".format(
                quote_plus(" AND ".join(map(lambda p: "({0})".format(p), 
                                            preds))))
        else:
            url += "&predicate="

        return url
        
    def _toCapConst(self, stype):
        return self.ALLOWED_CAPS[stype]

    def keywords_to_predicate(self, keywords, ored=True):
        """
        return the given keywords as a predicate that can be added to
        the current query.  This function can be overridden to change
        how keyword searches are implemented.  

        Parameters
        ----------
          *keywords*  a python list of the keywords
          *ored*      if True, the keywords should be ORed together; 
                          otherwise, they should be ANDed
        """
        textcols = ["title", "shortName", "identifier",
                    "[content/subject]", "[curation/publisher]", 
                    "[content/description]" ]

        conjunction = (ored and ") OR (") or ") AND ("

        const = []
        for kw in keywords:
            keyconst = []
            for col in textcols:
                keyconst.append("{0} LIKE '%{1}%'".format(col, kw))
            const.append(" OR ".join(keyconst))
        return "("+conjunction.join(const)+")"


@deprecated("0.5")
class RegistryResults(dalq.DALResults):
    """
    an iterable set of results from a registry query.  Each record is
    returned as SimpleResource instance
    """

    _strarraycols = ["waveband", "subject", "type", "contentLevel"]

    def __init__(self, votable, url=None, version="1.0"):
        """
        initialize the results.  This constructor is not typically called 
        by directly applications; rather an instance is obtained from calling 
        a SIAQuery's execute().
        """
        super(RegistryResults, self).__init__(votable, url, "vaoreg", version)

    def getrecord(self, index):
        """
        return all the attributes of a resource record with the given index
        as SimpleResource instance (a dictionary-like object).

        Parameters
        ----------
        index  : int
            the zero-based index of the record
        """
        return SimpleResource(self, index)

    def getvalue(self, name, index):
        """
        return the value of a record attribute--a value from a column and row.

        This implementation is aware of how lists of strings are encoded 
        and will return a python list of strings accordingly.

        Parameters
        ----------
        name : str
           the name of the attribute (column)
        index : int
           the zero-based index of the record

        Raises
        ------
        IndexError
            if index is negative or equal or larger than the 
            number of rows in the result table.
        KeyError
            if name is not a recognized column name
        """
        out = super(RegistryResults, self).getvalue(name, index)
        if name in self._strarraycols:
            out = split_str_array_cell(out)
        return out

    @property
    def size(self):
        """
        the number of records returned in this result (read-only)
        """
        return self.votable.nrows    


@deprecated("0.5")
class SimpleResource(dalq.Record):
    """
    a dictionary for the resource metadata returned in one record of a 
    registry query.

    A SimpleResource acts as a dictionary, so in general, all attributes can 
    be accessed by name via the [] operator, and the attribute names can 
    by returned via the keys() function.  For convenience, it also stores 
    key values as properties; these include:

    Properties
    ----------
    title : bytes
       the title of the resource
    shortname : bytes
       the resource's short name
    ivoid : bytes
       the IVOA identifier for the resource (identifier will also work)
    accessurl : str
       when the resource is a service, the service's access URL.
    """

    def __init__(self, results, index):
        super(SimpleResource, self).__init__(results, index)

    def __getitem__(self, key):
        """
        return a resource metadatum value with a name given by key.  This
        version will split encoded string array values into tuples.
        """
        out = super(SimpleResource, self).__getitem__(key)
        if key in RegistryResults._strarraycols:
            out = split_str_array_cell(out)
        return out

    @property
    def title(self):
        """
        the title of the resource
        """
        return self.get("title")

    @property
    def shortname(self):
        """
        the short name for the resource
        """
        return self.get("shortName")

    @property
    def description(self):
        """
        the textual description of the resource.  

        See Also
        --------
        SimpleResource.describe
        """
        return self.get("description")

    @property
    def tags(self):
        """
        a user-friendly label for the resource
        """
        return self.get("tags")

    @property
    def ivoid(self):
        """
        the IVOA identifier for the resource.  In this interface, this 
        ID may be appended by a #-delimited suffix to point to a particular 
        capability.
        """
        return self.get("identifier")

    @property
    def identifier(self):
        """
        the IVOA identifier for the resource.  In this interface, this 
        ID may be appended by a #-delimited suffix to point to a particular 
        capability.
        """
        return self.get("identifier")

    @property
    def publisher(self):
        """
        the name of the organization responsible for providing this resource.
        """
        return self.get("publisher")

    @property
    def waveband(self):
        """
        a list of names of the wavebands that the resource provides data for
        """
        return self.get("waveband")

    @property
    def subject(self):
        """
        a list of the subject keywords that describe this resource
        """
        return self.get("subject")

    @property
    def type(self):
        """
        a list of the resource types that characterize this resource.
        """
        return self.get("type")

    @property
    def contentlevel(self):
        """
        a list of content level labels that describe the intended audience 
        for this resource.
        """
        return self.get("contentLevel")

    @property
    def capability(self):
        """
        the name of the IVOA service capability.  This will typically set to
        the value of the capability/@xsi:type attribute in the VOResource 
        record (without the namespace prefix).
        """
        return self.get("capabilityClass")

    @property
    def standardid(self):
        """
        the IVOA identifier of the standard that this resource capability 
        supports.  
        """
        return self.get("capabilityStandardID")

    @property 
    def accessurl(self):
        """
        the URL that can be used to access the service resource.  If the 
        resource is not a service, this will typically be blank.  

        Note that this will always be returned as a native string--i.e. as 
        unicode for Python 3 and as a byte-string for Python 2--making ready
        to use as a URL with urllib functions.
        """
        return self.get_str("accessURL")

    def to_service(self):
        """
        return an appropriate DALService subclass for this resource that 
        can be used to search the resource.  Return None if the resource is 
        not a recognized DAL service.  Currently, only Conesearch, SIA, SSA,
        and SLA services are supported.  
        """
        return _createService(self, True);

    def search(self, *args, **keys):
        """
        assuming this resource refers to a searchable service, execute a 
        search against the resource.  This is equivalent to:

        >>> self.to_service().search(*args, **keys)

        The arguments provided should be appropriate for the service that 
        the DAL service type would expect.  See the documentation for the 
        appropriate service type:

        ============  =========================================
        Service type  Use the argument syntax for
        ============  =========================================
        catalog       :py:meth:`pyvo.dal.scs.SCSService.search`
        image         :py:meth:`pyvo.dal.sia.SIAService.search`
        spectrum      :py:meth:`pyvo.dal.ssa.SSAService.search`
        line          :py:meth:`pyvo.dal.sla.SLAService.search`
        database      *not yet supported*
        ============  =========================================

        Raises
        ------
        RuntimeError
           if the resource does not describe a searchable service.
        """
        service = _createService(self, False);
        if not service:
            raise RuntimeError("resource, {0}, is not a searchable service".format(self.shortname))

        return service.search(*args, **keys)

    def describe(self, verbose=False, width=78, file=None):
        """
        Print a summary description of this resource.  

        Parameters
        ----------
        verbose : bool
            If false (default), only user-oriented information is 
            printed; if true, additional information will be printed
            as well.
        width : int
            Format the description with given character-width.
        out : writable file-like object
            If provided, write information to this output stream.
            Otherwise, it is written to standard out.  
        """
        restype = "Generic Resource"
        if self.get("interfaceClass"):
            # it's a service of some kind
            restype = "Custom Service"
            stdid = self.get("capabilityStandardID")
            if stdid:
                if stdid.startswith("ivo://ivoa.net/std/ConeSearch"):
                    restype = "Catalog Cone-search Service"
                elif stdid.startswith("ivo://ivoa.net/std/SIA"):
                    restype = "Image Data Service"
                elif stdid.startswith("ivo://ivoa.net/std/SSA"):
                    restype = "Spectrum Data Service"
                elif stdid.startswith("ivo://ivoa.net/std/SLA"):
                    restype = "Spectral Line Database Service"
                elif stdid.startswith("ivo://ivoa.net/std/Registry"):
                    restype = "Registry Service"
                    if "Harvest" in self.get("capabilityClass"):
                        restype = "Registry Harvest Service"
                    elif "Search" in self.get("capabilityClass"):
                        restype = "Registry Search Service"
            elif self.get("interfaceClass") == "WebBrowser":
                restype = "Web-page Based Service" 
        print(restype, file=file)
        print(dalq.para_format_desc(self.title), file=file)
        print("Short Name: " + self.shortname, file=file)
        print("Publisher: " + dalq.para_format_desc(self.publisher), file=file)
        print("IVOA Identifier: " + self.identifier, file=file)
        if self.accessurl:
            print("Base URL: " + self.accessurl, file=file)

        if self.description:
            print(file=file)
            print(dalq.para_format_desc(self.description), file=file)
            print(file=file)

        if self.get("subjects"):
            val = self.get("subjects")
            if not hasattr(val, "__getitem__"):
                val = [val]
            val = (str(v) for v in val)
            print(dalq.para_format_desc("Subjects: " + ", ".join(val)), 
                  file=file)
        if self.get("waveband"):
            val = self.get("waveband")
            if not hasattr(val, "__getitem__"):
                val = [val]
            val = (str(v) for v in val)
            print(dalq.para_format_desc("Waveband Coverage: " + ", ".join(val)),
                  file=file)

        if verbose:
            if self.get("capabilityStandardID"):
                print("StandardID: " + self["capabilityStandardID"], file=file)
            if self.get("referenceURL"):
                print("More info: " + self["referenceURL"], file=file)
            


        

                
        

_standardIDs = {
    "ivo://ivoa.net/std/ConeSearch":  scs.SCSService,
    "ivo://ivoa.net/std/SIA":  sia.SIAService,
    "ivo://ivoa.net/std/SSA":  ssa.SSAService,
    "ivo://ivoa.net/std/SLAP":  sla.SLAService,
    "ivo://ivoa.net/std/TAP":  tap.TAPService,
}

def _createService(resource, savemeta=False):
    if not resource.accessurl:
        return None
    meta = None
    if savemeta:
        meta = resource

    serviceCls = _standardIDs.get(resource.standardid)
    try:
        if serviceCls:
            return serviceCls(resource.accessurl, meta)
    except Exception:
        return None

def split_str_array_cell(val, delim=None):
    """
    split an encoded string array value into a tuple.  The VAO registry's
    search service encodes string array values by delimiting the elements 
    with pound signs ('#').  These delimiters also mark the start and end 
    of the encoded value as well.  This function converts the encoded value
    into a split tuple.

    Parameters
    ----------
    val : str
       the original string value to split
    delim : str
       the delimiter that separates the values; defaults to '#'
    """
    if not val: return val

    if delim is None:
        dval = "'#'"
        # we do the following because "u'#'" is not legal syntax in Python3
        if dalq._is_python3:
            if isinstance(val, bytes):
                dval = "b'#'"
        else:
            if isinstance(val, unicode):
                dval = "u'#'"
        delim = eval(dval)

    if val[0:1] == delim: val = val[1:]
    if val[-1:] == delim: val = val[:-1]
    return tuple(val.split(delim))
