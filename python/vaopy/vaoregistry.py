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

from urllib import quote_plus, urlopen, urlretrieve
import warnings

class RegistrySearch():
    """
    a class for submitting searches to the VAO registry.  
    """

    STSCI_REGISTRY_BASEURL = "http://vao.stsci.edu/directory/NVORegInt.asmx/"

    @classmethod
    def connect(cls, url=None):
        """
        connect to an STScI registry at the given URL
        @param url    the base URL of the STScI registry.  If None, 
                        the standard endpoint will be used.  
        """
        if not url:  url = cls.STSCI_REGISTRY_BASEURL
        return RegistrySearch(url)

    def __init__(self, url):
        """
        connect to an STScI registry at the given URL
        """
        self.url = url
        if not self.url.endswith("/"): self.url += "/"

    def search(self, keywords=None, serviceType=None, 
               waveband=None, contentLevel=None, sqlpred=None):
        """
        Prepare and execute a registry search of the specified
        keywords. 
 
        A search can be constrained by: 
        - bandpass: Radio, Millimeter, Infrared (IR), Optical, 
                    Ultraviolet (UV),  X-Ray (xray), Gamma-Ray (GR)
        - service type: catalog (SCS), image (SIA), spectra (SSA), 
                        table (Vizier), ResourceType from Registry record
        - content level: ...

        The result will be a RegistryResults instance pointing to the
        first matching in the query results
        """
        srch = self.createQuery()
        if contentLevel:
            srch.addPredicate("[content/contentLevel] like '%%#%s#%%'" % contentLevel)
        if sqlpred:
            srch.addPredicate(sqlpred)
        if waveband:
            srch.setWavebandConstraint(waveband)
        if serviceType:
            srch.setServiceTypeConstraint(serviceType)

        return srch.execute()
        
    
    def resolve(self, ivoid, asVOResource=False):
        """
        Resolve the identifier against the registry, returning a
        resource record.  
        @param ivoid          the IVOA Identifier of the resource
        @param asVOResource   if True, return the VOResource-formated 
                                XML record; otherwise, a SimpleResource
                                instance is returned.
        """
        srch = self.createQuery()
        srch.addPredicate("Identifier='%s'" % ivoid)
        res = srch.execute()
        return res.getRecord(0)

    def createQuery(self):
        """
        create a RegistryQuery object that can be refined or saved
        before submitting.  
        """
        return RegistryQuery(self)


class RegistryQuery():
    """
    a representation of a registry query that can be built up over
    successive method calls and then executed.  An instance is normally
    obtained via a call to RegistrySearch.createQuery()
    """
    
    SERVICE_NAME = "VOTCapBandPredOpt"
    RESULTSET_TYPE_ARG = "VOTStyleOption=2"
    ALLOWED_WAVEBANDS = "Radio Millimeter Infrared Optical UV".split() + \
        "EUV X-ray Gamma-ray".split()
    ALLOWED_CAPS = { "table": "conesearch", 
                     "catalog": "conesearch", 
                     "image": "SimpleImageAccess",
                     "spectra": "SimpleSpectralAccess",
                     "conesearch": "conesearch", 
                     "simpleImageAccess": "SimpleImageAccess",
                     "simpleSpectralAccess": "SimpleSpectralAccess"  }
                     

    def __init__(self, registry, orKeywords=True):
        """
        create the query instance
        """
        self.reg = registry
        self.kw = []          # list of individual keyword phrases
        self.preds = []       # list of SQL predicates
        self.svctype = None
        self.band = None
        self.orKw = orKeywords
        self.doSort = True
        self.dalonly = False

    def addKeywords(self, keywords):
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
        self.kw.extend(keywords)

    def removeKeywords(self, keywords):
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
            self.kw.remove(kw)

    def orKeywords(self, ored):
        """
        set whether keywords are OR-ed or AND-ed together.  When
        the keywords are OR-ed, returned records will match at 
        least one of the keywords.  When they are AND-ed, the 
        records will match all of the keywords provided.  
        @param ored   true, if the keywords should be OR-ed; false,
                        if they should be AND-ed.
        """
        self.orKw = ored

    def willOrKeywords(self):
        """
        set true if the keywords will be OR-ed or AND-ed together
        in the query.  True is returned if the keywords will be 
        OR-ed.  
        """
        return self.orKw

    def getKeywords(self):
        """
        return the current set of keyword constraints
        """
        return list(self.kw)

    def getKeywordCount(self):
        """
        return the number of currently set keyword constraints
        """
        return len(self.kw)

    def setServiceTypeConstraint(self, serviceType):
        """
        restrict the results to contain services of the given type.
        @param serviceType   the desired type of service, one of 
                                "catalog", "table", "image", or 
                                "spectra".
        """
        if not serviceType:
            raise ValueError("missing serviceType value");
        if len(serviceType) < 2:
            raise ValueError("unrecognized serviceType value: " + 
                             serviceType);

        # uncapitalize
        if serviceType[0].upper() == serviceType[0]:
            serviceType = serviceType[0].lower() + service[1:]

        if serviceType not in self.ALLOWED_CAPS.keys():
            raise ValueError("unrecognized serviceType value: " + 
                             serviceType);
        self.svctype = serviceType

    def clearServiceTypeConstraint(self):
        """
        remove any currently set service type constraint.  The query
        then will not be restricted to a particular type of service.
        """
        self.svctype = None

    def setWavebandConstraint(self, band):
        """
        restrict the results to contain resources provides data 
        covering a given waveband.  Allowed values 
        """
        if not band:
            raise ValueError("missing waveband value");
        if len(band) < 2:
            raise ValueError("unrecognized waveband: " + band);                             

        band = band[0].upper() + band[1:]
        if band not in self.ALLOWED_WAVEBANDS:
            raise ValueError("unrecognized waveband: " + band)
        self.band = band

    def clearWavebandConstraint(self):
        """
        remove any currently set waveband constraint.  The query
        then will not be restricted to a particular type of service.
        """
        self.band = None

    def addPredicate(self, pred):
        """
        add an SQL search predicate to the query.  This predicate should
        be of form supported by STScI VOTable search services.  This 
        predicate will be AND-ed with all other constraints (including
        previously added predicates); that is, this constraint must be
        satisfied in addition to the other constraints to match a 
        particular resource record.
        """
        self.preds.append(pred)

    def removePredicate(self, pred):
        """
        remove the give predicate from the current set of predicate
        constraints.  
        """
        self.preds.remove(pred)

    def clearPredicates(self):
        """
        remove all previously added predicates.
        """
        self.preds = []

    def getPredicates(self):
        """
        return (a copy of) the list of predicate constraints that will 
        be applied to the query.  These will be AND-ed with all other 
        constraints (including previously added predicates); that is, 
        this constraint must be satisfied in addition to the other 
        constraints to match a particular resource record.
        """
        return list(self.preds)

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
        return RegistryResults(self.executeVotable())

    def executeRaw(self):
        """
        submit the query and return the raw VOTable XML as a string
        """
        f = self.executeStream();
        return f.read();

    def executeStream(self):
        """
        submit the query and return the raw VOTable XML as a file stream
        """
        try:
            url = self.getQueryURL()
            return urlopen(url)
        except IOError, ex:
            raise RegistryServiceError("%s: %s" % (str(ex), url))

    def executeFile(self, tofilename):
        """
        submit the query and return the raw VOTable XML as a file stream
        """
        try:
            url = self.getQueryURL()
            return urlretrieve(url, tofilename);
        except IOError, ex:
            raise RegistryServiceError("%s: %s" % (str(ex), url))

    def executeVotable(self):
        """
        submit the query and return the results as
        """
        return _votableparse(self.executeStream().read)

    def getQueryURL(self):
        """
        return the GET URL that will submit the query and return the 
        results as a VOTable
        """
        url = "%s%s?%s" % (self.reg.url, self.SERVICE_NAME, 
                           self.RESULTSET_TYPE_ARG)

        preds = list(self.preds)
        if (self.kw): 
            preds.append(self.keywordsToPredicate(self.kw, self.orKw))
        if (preds):
            url += "&predicate=%s" % \
                quote_plus(" AND ".join(map(lambda p: "(%s)" % p, preds)))
                              
        else:
            url += "&predicate=1"

        if (self.svctype):
            url += "&capability=%s" % self._toCapConst(self.svctype)
        else:
            url += "&capability="

        if (self.band):
            url += "&waveband=%s" % self.band
        else:
            url += "&waveband="

        return url
        
    def _toCapConst(self, stype):
        return self.ALLOWED_CAPS[stype]

    def keywordsToPredicate(self, keywords, ored=True):
        """
        return the given keywords as a predicate that can be added to
        the current query.  This function can be overridden to change
        how keyword searches are implemented.  
        """
        textcols = ["Title", "ShortName", "Identifier", 
                    "[content/subject]", "[curation/publisher]", 
                    "[content/Description]"]

        conjunction = (ored and " OR ") or " AND "

        const = []
        for kw in keywords:
            keyconst = []
            for col in textcols:
                keyconst.append("%s LIKE '%%%s%%'" % (col, kw))
            const.append(" OR ".join(keyconst))
        return conjunction.join(const)


            


class RegistryAccessError(Exception):
    """
    a base class for registry access failures
    """
    pass

class RegistryServiceError(RegistryAccessError):
    """
    an exception indicating a failure communicating with a registry 
    service.
    """
    pass

class RegistryQueryError(RegistryAccessError):
    """
    an exception indicating an error by the registry in processing a
    query, including query-syntax errors.
    """
    pass

class RegistryResults():
    """
    an iterable set of results from a registry query.  Each record is
    returned as SimpleResource instance
    """

    def __init__(self, votable):
        self.tbl = votable.get_first_table()
        self.fnames = None

    def __iter__(self):
        return RegistryCursor(self.tbl);

    def getRecordCount(self):
        """
        return the total number of records returned in this result
        """
        return self.tbl.nrows

    def meta(self):
        """
        List table metadata.
        """
        # Note: it doesn't look like the C interface provides this 
        #       itself.
        return self.tbl.fields

    def attributeNames(self):
        """
        return the names of the available record attributes.
        """
        if not self.fnames:
            self.fnames = map(lambda f: f.name or f.ID, self.tbl.fields)
        return list(self.fnames)

    def getAttribute(self, name, index):
        """
        return the value of an attribute from a particular record in 
        the results
        @param name   the name of the attribute
        @param index  the zero-based index of the record
        """
        return self.tbl.array[name][index]

    def getRecord(self, index):
        """
        return all the attributes of a record with the given index
        as SimpleResource instance
        @param index  the zero-based index of the record
        """
        return SimpleResource(self, index)

class RegistryCursor():
    """
    a class for iterating through the result of a registry query
    """

    def __init__(self, table, initpos=0):
        self.tbl = table
        self.rec = initpos

    def getRecordCount(self):
        """
        return the number of records left to access by this result cursor
        """
        return self.tbl.nrows - self.rec

    def next(self):
        """
        return the next available resource record as a SimpleResource
        object.  This is equivalent to fetch.
        """
        return fetch()

    def fetch(self):
        """
        return the next available resource record as a SimpleResource
        object
        """
        out = SimpleResource(self.tbl, self.rec)
        self.rec += 1
        return out

class SimpleResource(dict):
    """
    a container for the resource attributes returned by a registry query.
    A SimpleResource is a dictionary, so in general, all attributes can 
    be accessed by name via the [] operator, and the attribute names can 
    by returned via the keys() function.  For convenience, it also stores 
    key values as public python attributes; these include:

       title         the title of the resource
       shortName     the resource's short name
       ivoid         the IVOA identifier for the resource
       accessURL     when the resource is a service, the service's access 
                       URL.
    """

    def __init__(self, table=None, index=1):
        self.title = None
        self.shortName = None
        self.ivoid = None
        self.accessURL = None

        if table:
            for att in table.attributeNames():
                self[att] = table.getAttribute(att, index)
            self._updateAtts()

    def _updateAtts(self):
        self.title = self.get("title")
        self.shortName = self.get("shortName")
        self.ivoid = self.get("identifier")
        self.accessURL = self.get("accessURL")


def _votableparse(source, columns=None, invalid='mask', pedantic=False,
                  table_number=None, filename="registry_query", version="1.1"):
    try:
        import astropy.io.vo.tree as votabletree
        import astropy.io.vo.table as votabletable
        from astropy.utils.xml import iterparser
        from astropy.io.vo.exceptions import W20, W49
        warnings.simplefilter("ignore", W20)
        warnings.simplefilter("ignore", W49)
    except ImportError, ex:
        raise RuntimeError("astropy votable not available")

    invalid = invalid.lower()
    assert invalid in ('exception', 'mask')

    chunk_size=votabletree.DEFAULT_CHUNK_SIZE

    if pedantic is None:
        pedantic = votabletable.PEDANTIC()

    config = {
        'columns'      :      columns,
        'invalid'      :      invalid,
        'pedantic'     :     pedantic,
        'chunk_size'   :   chunk_size,
        'table_number' : table_number,
        'filename'     :     filename}

    if filename is None and isinstance(source, basestring):
        config['filename'] = source

    with iterparser.get_xml_iterator(source) as iterator:
        return votabletree.VOTableFile(
          config=config, pos=(1, 1), version=version).parse(iterator, config)
   


