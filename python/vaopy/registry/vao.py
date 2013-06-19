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

from ..dal import query as dalq
from ..dal import sia, ssa, sla, scs
from urllib import quote_plus, urlopen, urlretrieve
import re

import numpy.ma as _ma

__all__ = [ "search", "RegistryService", "RegistryQuery" ]

def search(keywords=None, servicetype=None, waveband=None, sqlpred=None):
    """
    execute a simple query to the VAO registry.  

    :Args:
      *keywords*:  a string giving a single term or a python list 
                     of terms to match to registry records.  
      *servicetype*: the service type to restrict results to; 
                     allowed values include 'catalog' (synonyms: 
                     'scs', 'conesearch'), 'image' (synonym: 'sia'), 
                     'spectrum' (synonym: 'ssa'). 'service' (a generic
                     service). 'table' (synonyms: 'tap', 'database').
      *waveband*:  the name of a desired waveband; resources returned 
                     will be restricted to those that indicate as having
                     data in that waveband.  Allowed, case-insensitive 
                     values include 'Radio', 'Millimeter', 'Infrared'
                     (synonym: 'IR'), 'Optical', 'UV', 'EUV', 'X-ray' 
                     (synonym: 'Xray').
      *sqlpred*:   an SQL WHERE predicate (without the leading "WHERE") 
                     that further contrains the search against supported 
                     keywords.

    The result will be a RegistryResults instance.  
    """
    reg = RegistryService()
    return reg.search(keywords, servicetype, waveband, sqlpred)


class RegistryService(dalq.DalService):
    """
    a class for submitting searches to the VAO registry.  
    """

    STSCI_REGISTRY_BASEURL = "http://vao.stsci.edu/directory/NVORegInt.asmx/"

    def __init__(self, baseurl=None, resmeta=None, version="1.0"):
        """
        connect to an STScI registry at the given URL
        :Args:
           *baseurl*:  the base URL for submitting search queries to the 
                         service.  If None, it will default to the STScI 
                         public registry
           *resmeta*:  an optional dictionary of properties about the 
                         service
        """
        if not baseurl:  baseurl = self.STSCI_REGISTRY_BASEURL
        if not baseurl.endswith("/"): baseurl += "/"

        dalq.DalService.__init__(self, baseurl, "vaoreg", version, resmeta)


    def search(self, keywords=None, servicetype=None, 
               waveband=None, sqlpred=None):
        """
        execute a simple registry search of the specified
        keywords. 

        :Args:
          *keywords*:  a string giving a single term or a python list 
                         of terms to match to registry records.  
          *servicetype:  the service type to restrict results to; 
                         allowed values include 'catalog' (synonyms: 
                         'scs', 'conesearch'), 'image' (synonym: 'sia'), 
                         'spectrum' (synonym: 'ssa'). 'service' (a generic
                         service). 'table' (synonyms: 'tap', 'database').
          *waveband*:  the name of a desired waveband; resources returned 
                         will be restricted to those that indicate as having
                         data in that waveband.  Allowed, case-insensitive 
                         values include 'Radio', 'Millimeter', 'Infrared'
                         (synonym: 'IR'), 'Optical', 'UV', 'EUV', 'X-ray' 
                         (synonym: 'Xray').
          *sqlpred*:   an SQL WHERE predicate (without the leading "WHERE") 
                         that further contrains the search against supported 
                         keywords.

        The result will be a RegistryResults instance.  
        """
        srch = self.create_query(keywords, servicetype, waveband, sqlpred)
        # print srch.getqueryurl()
        return srch.execute()
        
    
    def resolve(self, ivoid):
        """
        Resolve the identifier against the registry, returning a
        resource record.  
        @param ivoid          the IVOA Identifier of the resource
        """
        srch = self.create_query()
        srch.addpredicate("identifier='%s'" % ivoid)
        res = srch.execute()
        return res.getrecord(0)

    def create_query(self, keywords=None, servicetype=None, 
                     waveband=None, sqlpred=None):
        """
        create a RegistryQuery object that can be refined or saved
        before submitting.  
        :Args:
          *keywords*:  a string giving a single term or a python list 
                         of terms to match to registry records.  
          *servicetype:  the service type to restrict results to; 
                         allowed values include 'catalog' (synonyms: 
                         'table', 'scs', 'conesearch', 'ConeSearch'), 
                         'image' (synonym: 'sia', 'SimpleImageAccess'), 
                         'spectrum' (synonym: 'ssa', 'ssap', 
                         'SimpleSpectralAccess'). 
                         'database' (synonyms: 'tap','TableAccess').
          *waveband*:  the name of a desired waveband; resources returned 
                         will be restricted to those that indicate as having
                         data in that waveband.  Allowed, case-insensitive 
                         values include 'Radio', 'Millimeter', 'Infrared'
                         (synonym: 'IR'), 'Optical', 'UV', 'EUV', 'X-ray' 
                         (synonym: 'Xray').
          *sqlpred*:   an SQL WHERE predicate (without the leading "WHERE") 
                         that further contrains the search against supported 
                         keywords.
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
        return srch

class RegistryQuery(dalq.DalQuery):
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
                     

    def __init__(self, baseurl=None, orKeywords=True, version="1.0"):
        """
        create the query instance

        :Args:
           *baseurl*:     the base URL for the VAO registry.  If None, it will
                            be set to the public VAO registry at STScI.
           *orKeywords*:  if True, keyword constraints will by default be 
                            OR-ed together; that is, a resource that matches 
                            any of the keywords will be returned.  If FALSE,
                            the keywords will be AND-ed, thus requiring a 
                            resource to match all the keywords.  
           
        """
        if not baseurl:  baseurl = RegistryService.STSCI_REGISTRY_BASEURL
        dalq.DalQuery.__init__(self, baseurl, "vaoreg", version)
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
        @param keywords  either a single keyword phrase (as a string) 
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
        @param keywords  either a single keyword phrase (as a string) 
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
        @param ored   true, if the keywords should be OR-ed; false,
                        if they should be AND-ed.
        """
        self._orKw = ored

    def will_or_keywords(self):
        """
        set true if the keywords will be OR-ed or AND-ed together
        in the query.  True is returned if the keywords will be 
        OR-ed.  
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
            raise ValueError("unrecognized serviceType value: " + 
                             serviceType);

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

        :Raises:
           *DalServiceError*: for errors connecting to or 
                              communicating with the service
           *DalFormatError*:  for errors parsing the VOTable response
           *DalQueryError*:   for errors in the input query syntax
        """
        out = dalq.DalQuery.execute_votable(self)
        res = dalq.DalResults(out)
        tbl = res._tbl

        # We note that the server-side implementation of the service will 
        # include all of the capability records of resource that have 
        # capabilities of the given type.  Consequently, the results includes
        # capabilites that are not of the requested type.

        # filter out service types that don't match
        if self.servicetype:
            cap = self._toCapConst(self.servicetype)
            tbl.array = \
                _ma.array(tbl.array.data[tbl.array.data['capabilityClass']==cap],
                     mask=tbl.array.mask[tbl.array.data['capabilityClass']==cap])
            tbl._nrows = tbl.array.shape[0]

        return out

    def execute(self):
        """
        submit the query and return the results as a RegistryResults
        instance.  
        @throws RegistryServiceError   for errors connecting to or 
                    communicating with the service
        @throws RegistryQueryError     if the service responds with 
                    an error, including a query syntax error.  A 
                    syntax error should only occur if the query 
                    query contains non-sensical predicates.
        """
        return RegistryResults(self.execute_votable(), self.getqueryurl())

    def execute_stream(self):
        """
        submit the query and return the raw VOTable XML as a file stream

        :Raises:
           *DalServiceError*: for errors connecting to or 
                              communicating with the service
           *DalQueryError*:   for errors in the input query syntax
        """
        try:
            url = self.getqueryurl()
            out = urlopen(url)
            if out.info().gettype() == "text/plain":
                # Error message returned
                self._raiseServiceError(out.read())
            elif out.info().gettype() != "text/xml":
                # Unexpected response
                raise dalq.DalFormatError("Wrong response format: " + 
                                          out.info().gettype())
            return out

        except IOError, ex:
            raise dalq.DalServiceError.from_except(ex, url)

    def _raiseServiceError(self, response):
        invalidmessage = "System.InvalidOperationException: "
        outmsg = re.sub(r'\n.*', '', response).strip()
        if response.startswith(invalidmessage):
            raise dalq.DalQueryError(outmsg[len(invalidmessage):])
        raise dalq.DalServiceError(outmsg)

    def getqueryurl(self, lax=False):
        """
        return the GET URL that will submit the query and return the 
        results as a VOTable
        """
        url = "%s%s?%s" % (self._baseurl, self.SERVICE_NAME, 
                           self.RESULTSET_TYPE_ARG)

        # this adds arbitrary parameters
        # if len(self.paramnames()) > 0:
        #    url += "&" + \
        #     "&".join(map(lambda p: "%s=%s"%(p,self._paramtostr(self._param[p])),
        #                  self._param.keys()))

        if self._band:
            url += "&waveband=%s" % self._band
        else:
            url += "&waveband="

        if self._svctype:
            url += "&capability=%s" % self._toCapConst(self.servicetype)
        else:
            url += "&capability="

        preds = list(self._preds)
        if (self.keywords): 
            preds.append(self.keywords_to_predicate(self.keywords, self._orKw))
        if (preds):
            url += "&predicate=%s" % \
                quote_plus(" AND ".join(map(lambda p: "(%s)" % p, preds)))
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

        :Args:
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
                keyconst.append("%s LIKE '%%%s%%'" % (col, kw))
            const.append(" OR ".join(keyconst))
        return "("+conjunction.join(const)+")"

class RegistryResults(dalq.DalResults):
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
        dalq.DalResults.__init__(self, votable, url, "vaoreg", version)

    def getrecord(self, index):
        """
        return all the attributes of a resource record with the given index
        as SimpleResource instance (a dictionary-like object).
        @param index  the zero-based index of the record
        """
        return SimpleResource(self, index)

    def getvalue(self, name, index):
        """
        return the value of a record attribute--a value from a column and row.

        This implementation is aware of how lists of strings are encoded 
        and will return a python list of strings accordingly.

        :Args:
           *name*:   the name of the attribute (column)
           *index*:  the zero-based index of the record

        :Raises:
           IndexError  if index is negative or equal or larger than the 
                         number of rows in the result table.
           KeyError    if name is not a recognized column name
        """
        out = dalq.DalResults.getvalue(self, name, index)
        if name not in self._strarraycols:
            return out
        
        if out == '': return out
        if out[0] == '#': out = out[1:]
        if out[-1] == '#': out = out[:-1]
        return tuple(out.split('#'))

    @property
    def size(self):
        """
        the number of records returned in this result (read-only)
        """
        return self._tbl.nrows    


class SimpleResource(dalq.Record):
    """
    a dictionary for the resource attributes returned by a registry query.
    A SimpleResource is a dictionary, so in general, all attributes can 
    be accessed by name via the [] operator, and the attribute names can 
    by returned via the keys() function.  For convenience, it also stores 
    key values as public python attributes; these include:

       title         the title of the resource
       shortname     the resource's short name
       ivoid         the IVOA identifier for the resource (identifier will also work)
       accessurl     when the resource is a service, the service's access 
                       URL.
    """

    def __init__(self, results, index):
        dalq.Record.__init__(self, results, index)

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
        """
        return self.get("accessURL")

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

           self.to_service().search(*args, **keys)

        The arguments provided should be appropriate for the service that 
        the DAL service type would expect.  

        :Raises:
           *RuntimeError*:   if the resource does not describe a searchable
                                service.
        """
        service = _createService(self, False);
        if not service:
            raise RuntimeError("resource, %s, is not a searchable service" % self.shortname)

        return service.search(*args, **keys)

_standardIDs = {
    "ivo://ivoa.net/std/ConeSearch":  scs.SCSService,
    "ivo://ivoa.net/std/SIA":  sia.SIAService,
    "ivo://ivoa.net/std/SSA":  ssa.SSAService,
    "ivo://ivoa.net/std/SLAP":  sla.SLAService,
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
    except Exception, ex:
        return None
