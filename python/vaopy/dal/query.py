"""
A module for walking through the query response of VO data access layer
(DAL) queries and general VOTable-based datasets.

Most data queries in the VO return a table as a result, usually
formatted as a VOTable.  Each row of the table describes a single
physical or virtual dataset which can be retrieved.  For uniformity,
datasets are described via standard metadata defined by a data model
specific to the type of data being queried.  The fields of the data
model are identified most generally by their VOClient alias as defined
in this interface, or at a lower level by the Utype or UCD of the
specific standard and version of the standard being queried.  While
the data model differs depending upon the type of data being queried,
the form of the query response is the same for all classes of data,
allowing a common query response interface to be used.

An exception to this occurs when querying an astronomical catalog or
other externally defined table.  In this case there is no VO defined
standard data model.  Usually the field names are used to uniquely
identify table columns.
"""
__all__ = [ "ensure_baseurl", "DALService", "DALQuery" ]

import copy, re, warnings, socket
from urllib2 import urlopen, URLError, HTTPError
from urllib import quote_plus

def ensure_baseurl(url):
    """
    ensure a well formed DAL base URL that ends either with a '?' or a '&'
    """
    if '?' in url:
        if url[-1] == '?' or url[-1] == '&':
            return url
        else:
            return url+'&'
    else:
        return url+'?'

class DalService(object):
    """
    an abstract base class representing a DAL service located a particular 
    endpoint.
    """

    def __init__(self, baseurl, protocol=None, version=None, resmeta=None):
        """
        instantiate the service connecting it to a base URL

        :Args: 
           *baseurl*:  the base URL that should be used for forming queries to
                           the service.
           *protocol*: The protocol implemented by the service, e.g., "scs", "sia",
                           "ssa", and so forth.
           *version*:  The protocol version, e.g, "1.0", "1.2", "2.0".
           *resmeta*:  a dictionary containing resource metadata describing the 
                           service.  This is usually provided a registry record.
        """
        self._baseurl = baseurl
        self._protocol = protocol
        self._version = version
        if not resmeta:  
            self._desc = {}
        elif isinstance(resmeta, dict):
            self._desc = copy.deepcopy(resmeta)

    @property
    def baseurl(self):
        """
        the base URL to use for submitting queries (read-only)
        """
        return self._baseurl

    @property
    def protocol(self):
        """
        The service protocol implemented by the service read-only).
        """
        return self._protocol

    @property
    def version(self):
        """
        The version of the service protocol implemented by the service read-only).
        """
        return self._version

    @property
    def description(self):
        """
        an optional dictionary of resource metadata that describes the 
        service.  This is generally information stored in a VO registry.  
        """
        return self._desc

    def create_query(self):
        """
        create a query object that constraints can be added to and then 
        executed.
        """
        # this must be overridden to return a Query subclass appropriate for 
        # the service type
        return DalQuery(self.baseurl, self.protocol, self.version)


class DalQuery(object):
    """
    a class for preparing a query to a particular service.  Query constraints
    are typically added via its service type-specific methods; however, they 
    can be added generically (including custom parameters) via the setparam()
    function.  The various execute() functions will submit the query and 
    return the results.  

    The base URL for the query can be changed via the baseurl property.
    """

    def __init__(self, baseurl, protocol=None, version=None):
        """
        initialize the query object with a baseurl
        """
        self._baseurl = baseurl
        self._protocol = protocol
        self._version = version
        self._param = { }

    @property
    def baseurl(self):
        """
        the base URL that this query will be sent to when one of the 
        execute functions is called. 
        """
        return self._baseurl
    @baseurl.setter
    def baseurl(self, baseurl):
        self._baseurl = baseurl

    @property
    def protocol(self):
        """
        The service protocol which generated this query response (read-only).
        """
        return self._protocol

    @property
    def version(self):
        """
        The version of the service protocol which generated this query response
        (read-only).
        """
        return self._version

    def setparam(self, name, val):
        """
        add a parameter constraint to the query.

        :Args:
            *name*:  the name of the parameter.  This should be a name that 
                     is recognized by the service itself.  
            *val*:   the value for the constraint.  This value must meet the 
                     requirements set by the standard or by the service.  If 
                     the constraint consists of multiple values, it should be 
                     passed as a sequence.  
        """
        self._param[name] = val

    def unsetparam(self, name):
        """
        unset the parameter constraint having the given name (if it is set)
        """
        if name in self._param.keys():
            del self._param[name]

    def getparam(self, name):
        """
        return the current value of the parameter with the given name or None
        if it is not set.
        """
        return self._param.get(name)

    def paramnames(self):
        """
        return the names of the parameters set so far
        """
        return self._param.keys()

    def execute(self):
        """
        submit the query and return the results as a Results subclass instance

        :Raises:
           *DalServiceError*: for errors connecting to or 
                              communicating with the service
           *DalQueryError*:   for errors either in the input query syntax or 
                              other user errors detected by the service
           *DalFormatError*:  for errors parsing the VOTable response
        """
        return DalResults(self.execute_votable(), self.getqueryurl())

    def execute_raw(self):
        """
        submit the query and return the raw VOTable XML as a string.

        :Raises:
           *DalServiceError*: for errors connecting to or 
                              communicating with the service
           *DalQueryError*:   for errors in the input query syntax
        """
        f = self.execute_stream()
        out = None
        try:
            out = f.read()
        finally:
            f.close()
        return out

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
            return urlopen(url)
        except IOError, ex:
            raise DalServiceError.from_except(ex, url, self.protocol, 
                                              self.version)

    def execute_votable(self):
        """
        submit the query and return the results as an AstroPy votable instance

        :Raises:
           *DalServiceError*: for errors connecting to or 
                              communicating with the service
           *DalFormatError*:  for errors parsing the VOTable response
           *DalQueryError*:   for errors in the input query syntax
        """
        try:
            return _votableparse(self.execute_stream().read)
        except DalAccessError:
            raise
        except Exception, e:
            raise DalFormatError(e, self.getqueryurl(), 
                                 self.protocol, self.version)

    def getqueryurl(self, lax=False):
        """
        return the GET URL that encodes the current query.  This is the 
        URL that the execute functions will use if called next.  

        :Args:
           *lax*:  if False (default), a DalQueryError exception will be 
                      raised if the current set of parameters cannot be 
                      used to form a legal query.  This implementation does 
                      no syntax checking; thus, this argument is ignored.

        :Raises:
           *DalQueryError*:   when lax=False, for errors in the input query 
                      syntax
        """
        return ensure_baseurl(self.baseurl) + \
            "&".join(map(lambda p: "%s=%s"%(p,self._paramtostr(self._param[p])),
                         self._param.keys()))

    def _paramtostr(self, pval):
        if isinstance(pval, tuple) or isinstance(pval, list):
            return ",".join(map(lambda p: quote_plus(str(p)), pval))
        return quote_plus(str(pval))
        

class DalResults(object):
    """
    Results from a DAL query.  It provides random access to records in 
    the response.  Alternatively, it can provide results via a Cursor 
    (compliant with the Python Database API) or an iterable.
    """

    def __init__(self, votable, url=None, protocol=None, version=None):
        """
        initialize the cursor.  This constructor is not typically called 
        by directly applications; rather an instance is obtained from calling 
        a DalQuery's execute().
        :Raises:
           *DalFormatError*:  if the response VOTable does not contain a 
                                response table
        """
        self._url = url
        self._protocol = protocol
        self._version = version
        self._status = self._findstatus(votable)
        if self._status[0] != "OK":
            raise DalQueryError(self._status[1], self._status[0], url,
                                self.protocol, self.version)

        self._tbl = self._findresultstable(votable)
        if not self._tbl:
            raise DalFormatError(reason="VOTable response missing results table",
                                 url=self._url)
        self._fldnames = []
        for field in self.fielddesc():
            if field.ID:
                self._fldnames.append(field.ID)
            else:
                self._fldnames.append(field.name)
        if len(self._fldnames) == 0:
            raise DalFormatError(reason="response table missing column " +
                                 "descriptions.", url=self._url,
                                protocol=self.protocol, version=self.version)

        self._infos = self._findinfos(votable)

    def _findresultstable(self, votable):
        # this can be overridden to specialize for a particular DAL protocol
        res = self._findresultsresource(votable)
        if not res or len(res.tables) < 1:
            return None
        return res.tables[0]

    def _findresultsresource(self, votable):
        # this can be overridden to specialize for a particular DAL protocol
        if len(votable.resources) < 1:
            return None
        for res in votable.resources:
            if res.type.lower() == "results":
                return res
        return votable.resources[0]

    def _findstatus(self, votable):
        # this can be overridden to specialize for a particular DAL protocol
        
        # look first in the result resource
        res = self._findresultsresource(votable)
        if res:
            # should be a RESOURCE/INFO
            info = self._findstatusinfo(res.infos)
            if info:
                return (info.value, info.content)

            # if not there, check inside first table
            if len(res.tables) > 0:
                info = self._findstatusinfo(res.tables[0].infos)
                if info:
                    return (info.value, info.content)

        # otherwise, look just below the root element
        info = self._findstatusinfo(votable.infos)
        if info:
            return (info.value, info.content)

        # assume it's okay
        return ("OK", "QUERY_STATUS not specified")

    def _findstatusinfo(self, infos):
        # this can be overridden to specialize for a particular DAL protocol
        for info in infos:
            if info.name == "QUERY_STATUS":
                return info

    def _findinfos(self, votable):
        # this can be overridden to specialize for a particular DAL protocol
        infos = {}
        res = self._findresultsresource(votable)
        for info in res.infos:
          infos[info.name] = info.value
        for info in votable.infos:
          infos[info.name] = info.value
        return infos

                
    @property
    def protocol(self):
        """
        The service protocol which generated this query response (read-only).
        """
        return self._protocol

    @property
    def version(self):
        """
        The version of the service protocol which generated this query response
        (read-only).
        """
        return self._version

    @property
    def queryurl(self):
        """
        the URL query that produced these results.  None is returned if unknown
        """
        return self._url

    @property
    def rowcount(self):
        """
        the number of records returned in this result (read-only)
        """
        return self._tbl.nrows

    def fielddesc(self):
        """
        return the full metadata for a column as Field instance, a simple 
        object with attributes corresponding the the VOTable FIELD attributes,
        namely: name, id, type, ucd, utype, arraysize, description
        """
        return self._tbl.fields

    def fieldnames(self):
        """
        return the names of the columns.  These are the names that are used 
        to access values from the dictionaries returned by getrecord().  They 
        correspond the ID of the column, if it is set, or otherwise to the 
        column name.
        """
        return self._fldnames[:]

    def fieldname_with_ucd(self, ucd):
        """
        return the field name that has a given UCD value or None if the UCD 
        is not found.  None is also returned if the UCD is None or an empty 
        stirng
        """
        if not ucd: return None

        for fld in self.fieldnames():
            desc = self.getdesc(fld)
            if desc.ucd == ucd:
                return fld

        return None

    def fieldname_with_utype(self, utype):
        """
        return the field name that has a given UType value or None if the UType 
        is not found.  None is also returned if UType is None or an empty stirng
        """
        if not utype: return None

        for fld in self.fieldnames():
            desc = self.getdesc(fld)
            if desc.utype == utype:
                return fld

        return None

    def getrecord(self, index):
        """
        return a representation of a result record that follows dictionary
        semantics.  The keys of the dictionary are those returned by this
        instance's fieldNames() function: either the column IDs or name, if 
        the ID is not set.  The returned record may have additional accessor 
        methods for getting at stardard DAL response metadata (e.g. ra, dec).
        :Args:
           *index*:  the integer index of the desired record where 0 returns
                        the first record

        :Raises:
           IndexError  if index is negative or equal or larger than the 
                       number of rows in the result table.
        """
        return Record(self, index)

    def getvalue(self, name, index):
        """
        return the value of a record attribute--a value from a column and row.
        :Args:
           *name*:   the name of the attribute (column)
           *index*:  the zero-based index of the record

        :Raises:
           IndexError  if index is negative or equal or larger than the 
                         number of rows in the result table.
           KeyError    if name is not a recognized column name
        """
        return self._tbl.array[name][index]

    def getdesc(self, name):
        """
        return the field description for the record attribute (column) with 
        the given name
        :Args:
           *name*:   the name of the attribute (column), chosen from those 
                        in fieldnames()

        :Returns:
           object   with attributes (name, id, datatype, unit, ucd, utype,
                      arraysize) which describe the column
        """
        if name not in self._fldnames:
            raise KeyError(name)
        return self._tbl.get_field_by_id_or_name(name)

    def __iter__(self):
        """
        return a python iterable for stepping through the records in this
        result
        """
        return Iter(self)

    def cursor(self):
        """
        return a cursor that is compliant with the Python Database API's 
        Cursor interface.
        """
        from .dbapi2 import Cursor
        return Cursor(self)

class Iter(object):
    def __init__(self, res):
        self.resultset = res
        self.pos = 0

    def __iter__(self):
        return self

    def next(self):
        try:
            out = self.resultset.getrecord(self.pos)
            self.pos += 1
            return out
        except IndexError:
            raise StopIteration()

class Record(dict):
    """
    one record from a DAL query result.  The column values are accessible 
    as dictionary items.  It also provides special added functions for 
    accessing the dataset the record corresponds to.  Subclasses may provide
    additional functions for access to service type-specific data.
    """

    def __init__(self, results, index):
        self._fdesc = {}
        if results:
            for fld in results.fieldnames():
                self[fld] = results.getvalue(fld, index)
                self._fdesc[fld] = results.getdesc(fld)

    def fielddesc(self, name):
        """
        return an object with attributes (name, id, datatype, unit, ucd, 
        utype, arraysize) that describe the record attribute with the given 
        name.  
        """
        return self._fdesc[name]

    def getdataurl(self):
        """
        return the URL contained in the access URL column which can be used 
        to retrieve the dataset described by this record.  None is returned
        if no such column exists.
        """
        for fld in self._fdesc:
            if fld.utype.contains("Access.Reference") or \
               (fld.ucd.contains("meta.dataset") and \
               fld.ucd.contains("meta.ref.url")):
                return self[fld]
        return None

    def getdataset(self, timeout=None):
	"""
        Get the dataset described by this record from the server.

        :Args:
            *timeout*:    the time in seconds to allow for a successful 
                            connection with server before failing with an 
                            IOError (specifically, socket.timeout) exception

	:Returns:
	    A file-like object which may be read to retrieve the referenced 
            dataset.

        :Raises:
            *KeyError*:   if no datast access URL is included in the record
            *URLError*:   if the dataset access URL is invalid (note: subclass
                             of IOError)
            *HTTPError*:  if an HTTP error occurs while accessing the dataset
                             (note: subclass of IOError)
            *socket.timeout*:  if the timeout is exceeded before a connection
                             is established.  (note: subclass of IOError)
            *IOError*:    if some other error occurs while establishing the 
                             data stream.
	"""
	url = self.getdataurl()
        if not url:
            raise KeyError("no dataset access URL recognized in record")
        if timeout:
            return urlopen(url, timeout=timeout)
        else:
            return urlopen(url)

    def cachedataset(self, filename=None, timeout=None, bufsize=524288):
        """
        retrieve the dataset described by this record and write it out to 
        a file with the given name.  If the file already exists, it will be
        over-written.

        :Args:  
            *filename*:   the path to a file to write to.  If None, a default
                            name is attempted based on the record title and 
                            format
            *timeout*:    the time in seconds to allow for a successful 
                            connection with server before failing with an 
                            IOError (specifically, socket.timeout) exception
            *bufsize*:    a buffer size for copying the data to disk (default:
                            0.5 MB)

        :Raises:
            *KeyError*: if no datast access URL is included in the record
            *URLError*:   if the dataset access URL is invalid
            *HTTPError*:  if an HTTP error occurs while accessing the dataset
            *socket.timeout*:  if the timeout is exceeded before a connection
                             is established.  (note: subclass of IOError)
            *IOError*:    if an error occurs while writing out the dataset
        """
        if not bufsize: bufsize = 524288
        try:
            inp = self.getdataset(timeout)
            with open(filename, 'w') as out:
                buf = inp.read(bufsize)
                while buf:
                    out.write(buf)
                    buf = inp.read(bufsize)
        finally:
            inp.close()


    def suggest_extension(self, default=None):
        """
        returns a recommended filename extension for the dataset described 
        by this record.  Typically, this would look at the column describing 
        the format and choose an extension accordingly.  
        """
        # abstract; specialized for the different service types
        return default

class DalAccessError(Exception):
    """
    a base class for failures while accessing a DAL service
    """
    _defreason = "Unknown service access error"

    def __init__(self, reason=None, url=None, protocol=None, version=None):
        """
        initialize the exception with an error message
        :Args:
           *reason*:    a message describing the cause of the error
           *url*:       the query URL that produced the error
           *protocol*:  the label indicating the type service that produced 
                          the error
           *version*:   version of the protocol of the service that produced 
                          the error
        """
        if not reason: reason = self._defreason
        Exception.__init__(self, reason)
        self._reason = reason
        self._url = url
        self._protocol = protocol
        self._version = version

    @classmethod
    def _typeName(cls, exc):
        return re.sub(r"'>$", '', re.sub(r"<type '.*\.", '', str(type(exc))))
    def __str__(self):
        return self._reason
    def __repr__(self):
        return "%s: %s" % (self._typeName(self), self._reason)
   
    @property
    def reason(self):
        """
        a string description of what went wrong
        """
        return self._reason
    @reason.setter
    def reason(self, val):
        if val is None: val = self._defreason
        self._reason = val
    @reason.deleter
    def reason(self):
        self._reason = self._defreason

    @property
    def url(self):
        """
        the URL that produced the error.  If None, the URL is unknown or unset
        """
        return self._url
    @url.setter
    def url(self, val):
        self._url = val
    @url.deleter
    def url(self):
        self._url = None

    @property
    def protocol(self):
        """
        A label indicating the type service that produced the error
        """
        return self._protocol
    @protocol.setter
    def protocol(self, protocol):
        self._protocol = protocol
    @protocol.deleter
    def protocol(self):
        self._protocol = None

    @property
    def version(self):
        """
        The version of the protocol of the service that produced the error
        """
        return self._version
    @version.setter
    def version(self, version):
        self._version = version
    @version.deleter
    def version(self):
        self._version = None


class DalProtocolError(DalAccessError):
    """
    a base exception indicating that a DAL service responded in an
    erroneous way.  This can be either an HTTP protocol error or a
    response format error; both of these are handled by separate
    supclasses.  This base class captures an underlying exception
    clause. 
    """
    _defreason = "Unknown DAL Protocol Error"

    def __init__(self, reason=None, cause=None, url=None, 
                 protocol=None, version=None):
        """
        initialize with a string message and an optional HTTP response code
        :Args:
           *reason*:  a message describing the cause of the error
           *code*:    the HTTP error code (as an integer)
           *cause*:   an exception issued as the underlying cause.  A value
                        of None indicates that no underlying exception was 
                        caught.
           *url*:     the query URL that produced the error
           *protocol*:  the label indicating the type service that produced 
                          the error
           *version*:   version of the protocol of the service that produced 
                          the error
        """
        DalAccessError.__init__(self, reason, url, protocol, version)
        self._cause = cause

    @property
    def cause(self):
        """
        a string description of what went wrong
        """
        return self._cause
    @cause.setter
    def cause(self, val):
        self._cause = val
    @cause.deleter
    def cause(self):
        self._cause = None


class DalFormatError(DalProtocolError):
    """
    an exception indicating that a DAL response contains fatal format errors.
    This would include XML or VOTable format errors.  
    """
    _defreason = "Unknown VOTable Format Error"

    def __init__(self, cause=None, url=None, reason=None, 
                 protocol=None, version=None):
        """
        create the exception
        :Args:
           *cause*:   an exception issued as the underlying cause.  A value
                        of None indicates that no underlying exception was 
                        caught.
           *url*:     the query URL that produced the error
           *reason*:  a message describing the cause of the error
           *protocol*:  the label indicating the type service that produced 
                          the error
           *version*:   version of the protocol of the service that produced 
                          the error
        """
        if cause and not reason:  
            reason = "%s: %s" % (DalAccessError._typeName(cause), str(cause))
        DalProtocolError.__init__(self, reason, cause, url, protocol, version)


class DalServiceError(DalProtocolError):
    """
    an exception indicating a failure communicating with a DAL
    service.  Most typically, this is used to report DAL queries that result 
    in an HTTP error.  
    """
    _defreason = "Unknown service error"
    
    def __init__(self, reason=None, code=None, cause=None, url=None, 
                 protocol=None, version=None):
        """
        initialize with a string message and an optional HTTP response code
        :Args:
           *reason*:  a message describing the cause of the error
           *code*:    the HTTP error code (as an integer)
           *cause*:   an exception issued as the underlying cause.  A value
                        of None indicates that no underlying exception was 
                        caught.
           *url*:     the query URL that produced the error
           *protocol*:  the label indicating the type service that produced 
                          the error
           *version*:   version of the protocol of the service that produced 
                          the error
        """
        DalProtocolError.__init__(self, reason, cause, url, protocol, version)
        self._code = code

    @property
    def code(self):
        """
        the HTTP error code that resulted from the DAL service query,
        indicating the error.  If None, the service did not produce an HTTP 
        response.
        """
        return self._code
    @code.setter
    def code(self, val):
        self._code = val
    @code.deleter
    def code(self):
        self._code = None

    @classmethod
    def from_except(cls, exc, url=None, protocol=None, version=None):
        """
        create and return DalServiceError exception appropriate
        for the given exception that represents the underlying cause.
        """
        if isinstance(exc, HTTPError):
            # python 2.7 has message as reason attribute; 2.6, msg
            reason = (hasattr(exc, 'reason') and exc.reason) or exc.msg
            if isinstance(reason, IOError):
                reason = reason.strerror
            elif not isinstance(reason, str):
                reason = str(reason)

            if not url: 
                if hasattr(exc, 'url'):
                    url = exc.url
                else:
                    url = exc.filename
            return DalServiceError(reason, exc.code, exc, url, protocol, version)
        elif isinstance(exc, URLError):
            reason = exc.reason
            if isinstance(reason, IOError):
                reason = reason.strerror
            elif not isinstance(reason, str):
                reason = str(reason)

            return DalServiceError(reason, cause=exc, url=url, 
                                   protocol=protocol, version=version)
        elif isinstance(exc, Exception):
            return DalServiceError("%s: %s" % (cls._typeName(exc), str(exc)), 
                                   cause=exc, url=url, 
                                   protocol=protocol, version=version)
        else:
            raise TypeError("from_except: expected Exception")

class DalQueryError(DalAccessError):
    """
    an exception indicating an error by a working DAL service while processing
    a query.  Generally, this would be an error that the service successfully 
    detected and consequently was able to respond with a legal error response--
    namely, a VOTable document with an INFO element contains the description
    of the error.  Possible errors will include bad usage by the client, such
    as query-syntax errors.
    """
    _defreason = "Unknown DAL Query Error"

    def __init__(self, reason=None, label=None, url=None, 
                 protocol=None, version=None):
        """
        :Args:
           *reason*:  a message describing the cause of the error.  This should 
                        be set to the content of the INFO error element.
           *label*:   the identifying name of the error.  This should be the 
                        value of the INFO element's value attribute within the 
                        VOTable response that describes the error.
           *url*:     the query URL that produced the error
           *protocol*:  the label indicating the type service that produced 
                          the error
           *version*:   version of the protocol of the service that produced 
                          the error
        """
        DalAccessError.__init__(self, reason, url, protocol, version)
        self._label = label
                          
    @property
    def label(self):
        """
        the identifing name for the error given in the DAL query response.
        DAL queries that produce an error which is detectable on the server
        will respond with a VOTable containing an INFO element that contains 
        the description of the error.  This property contains the value of 
        the INFO's value attribute.  
        """
        return self._label
    @label.setter
    def label(self, val):
        self._label = val
    @label.deleter
    def label(self):
        self._label = None

def _votableparse(source, columns=None, invalid='mask', pedantic=False,
                  table_number=None, filename=None, version="1.1"):
    try:
        import astropy.io.votable.tree as votabletree
        import astropy.io.votable.table as votabletable
        from astropy.utils.xml import iterparser
        from astropy.io.votable.exceptions import W22
        from astropy.io.votable.exceptions import W03,W06,W20,W21,W42,W46,W47,W49,E10
        for warning in (W03, W06, W20, W21, W42, W46, W47, W49, E10):
            warnings.simplefilter("ignore", warning)
# MJG : 021913 - commented out to get CDS responses to work
#        warnings.simplefilter("error", W22)
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
        'filename'     :     filename,
        'version_1_1_or_later': True   }

    if filename is None and isinstance(source, basestring):
        config['filename'] = source
    if filename is None:
        config['filename'] = 'dal_query'

    with iterparser.get_xml_iterator(source) as iterator:
        return votabletree.VOTableFile(
          config=config, pos=(1, 1), version=version).parse(iterator, config)




