# Licensed under a 3-clause BSD style license - see LICENSE.rst
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
from __future__ import print_function, division

__all__ = ["DALAccessError", "DALProtocolError",
            "DALFormatError", "DALServiceError", "DALQueryError",
            "DALService", "DALQuery", "DALResults", "Record"]

import sys
import os
import re
import warnings
import textwrap
import requests
import functools

if sys.version_info[0] >= 3:
    _mimetype_re = re.compile(b'^\w[\w\-]+/\w[\w\-]+(\+\w[\w\-]*)?(;[\w\-]+(\=[\w\-]+))*$')
    _is_python3 = True
else:
    _mimetype_re = re.compile(r'^\w[\w\-]+/\w[\w\-]+(\+\w[\w\-]*)?(;[\w\-]+(\=[\w\-]+))*$')
    _is_python3 = False

def is_mime_type(val):
    if _is_python3 and isinstance(val, str):
        val = val.encode('utf-8')

    return bool(_mimetype_re.match(val))

class Record(dict):
    """
    one record from a DAL query result.  The column values are accessible 
    as dictionary items.  It also provides special added functions for 
    accessing the dataset the record corresponds to.  Subclasses may provide
    additional functions for access to service type-specific data.
    """

    def __init__(self, results, index, fielddesc=None):
        self._fdesc = fielddesc
        if not self._fdesc: 
            self._fdesc = {}

        if fielddesc is None:
            for fld in results.fieldnames():
                self._fdesc[fld] = results.getdesc(fld)

        super(Record, self).__init__()

        self.update(zip(
            results.fieldnames(),
            results.votable.array.data[index]
        ))

    def get_str(self, key, default=None):
        # Needed for python3 support, this will convert to a native string 
        # if it is not already
        try:
            out = self.__getitem__(key)
        except KeyError:
            return default
        if isinstance(out, str):
            return out
        if _is_python3: 
            if isinstance(out, bytes):
                out = out.decode('utf-8')
        else:
            if isinstance(out, unicode):
                out = out.decode('utf-8')
        return out

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
        for name,fld in self._fdesc.iteritems():
            if (fld.utype and "Access.Reference" in fld.utype) or \
               (fld.ucd   and "meta.dataset" in fld.ucd 
                          and "meta.ref.url" in fld.ucd):
                out = self[name]
                if _is_python3 and isinstance(out, bytes):
                    out = out.decode('utf-8')
                return out
        return None

    def getdataset(self, timeout=None):
        """
        Get the dataset described by this record from the server.

        Parameters
        ----------
        timeout : float   
           the time in seconds to allow for a successful 
           connection with server before failing with an 
           IOError (specifically, socket.timeout) exception

        Returns
        -------
            A file-like object which may be read to retrieve the referenced 
            dataset.

        Raises
        ------
        KeyError
           if no datast access URL is included in the record
        URLError
           if the dataset access URL is invalid (note: subclass of IOError)
        HTTPError
           if an HTTP error occurs while accessing the dataset
           (note: subclass of IOError)
        socket.timeout  
           if the timeout is exceeded before a connection is established.  
           (note: subclass of IOError)
        IOError
           if some other error occurs while establishing the data stream.
        """
        url = self.getdataurl()
        if not url:
            raise KeyError("no dataset access URL recognized in record")
        if timeout:
            r = requests.get(url, stream = True, timeout = timeout)
        else:
            r = requests.get(url, stream = True)

        r.raise_for_status()
        r.raw.read = functools.partial(r.raw.read, decode_content=True)
        return r.raw

    def cachedataset(self, filename=None, dir=".", timeout=None, bufsize=524288):
        """
        retrieve the dataset described by this record and write it out to 
        a file with the given name.  If the file already exists, it will be
        over-written.

        Parameters
        ----------
        filename : str
           the name of the file to write dataset to.  If the
           value represents a relative path, it will be taken
           to be relative to the value of the ``dir`` 
           parameter.  If None, a default name is attempted 
           based on the record title and format.  
        dir : str
           the directory to write the file into.  This value
           will be ignored if filename is an absolute path.
        timeout : int
           the time in seconds to allow for a successful 
           connection with server before failing with an 
           IOError (specifically, socket.timeout) exception
        bufsize : int
           a buffer size in bytes for copying the data to disk 
           (default: 0.5 MB)

        Raises
        ------
        KeyError
            if no datast access URL is included in the record
        URLError
           if the dataset access URL is invalid
        HTTPError
           if an HTTP error occurs while accessing the dataset
        socket.timeout
           if the timeout is exceeded before a connection is established.  
           (note: subclass of IOError)
        IOError
            if an error occurs while writing out the dataset
        """
        if not bufsize: bufsize = 524288

        if not filename:
            filename = self.make_dataset_filename(dir)

        inp = self.getdataset(timeout)
        try:
            with open(filename, 'wb') as out:
                buf = inp.read(bufsize)
                while buf:
                    out.write(buf)
                    buf = inp.read(bufsize)
        finally:
            inp.close()

    _dsname_no = 0  # used by make_dataset_filename

    def make_dataset_filename(self, dir=".", base=None, ext=None):
        """
        create a viable pathname in a given directory for saving the dataset
        available via getdataset().  The pathname that is returned is 
        guaranteed not to already exist (under single-threaded conditions).  

        This implementation will first try combining the base name with the 
        file extension (with a dot).  If this file already exists in the 
        directory, a name that appends an integer suffix ("-#") to the base
        before joining with the extension will be tried.  The integer will
        be incremented until a non-existent filename is created.

        Parameters
        ----------
        dir : str
           the directory to save the dataset under.  This must already exist.
        base : str
           a basename to use to as the base of the filename.  If 
           None, the result of ``suggest_dataset_basename()``
           will be used.
        ext : str
           the filename extension to use.  If None, the result of 
           ``suggest_extension()`` will be used.
        """
        if not dir:
          raise ValueError("make_dataset_filename(): no dir parameter provided")
        if not os.path.exists(dir):
            raise IOError("{0}: directory not found".format(dir))
        if not os.path.isdir(dir):
            raise ValueError("{0}: not a directory".format(dir))

        if not base:
            base = self.suggest_dataset_basename()
        if not ext:
            ext = self.suggest_extension("dat")

        # be efficient when writing a bunch of files into the same directory
        # in succession
        n = self._dsname_no
        mkpath = lambda i: os.path.join(dir, "{0}-{1}.{2}".format(base, n, ext))
        if n > 0:
            # find the last file written of the form, base-n.ext
            while n > 0 and not os.path.exists(mkpath(n)):
                n -= 1
        if n > 0:
            n += 1
        if n == 0:
            # never wrote a file of form, base-n.ext; try base.ext
            path = os.path.join(dir, "{0}.{1}".format(base, ext))
            if not os.path.exists(path):
                return path
            n += 1
        # find next available name
        while os.path.exists(mkpath(n)):
            n += 1
        self._dsname_no = n
        return mkpath(n)
                

    def suggest_dataset_basename(self):
        """
        return a default base filename that the dataset available via 
        ``getdataset()`` can be saved as.  This function is 
        specialized for a particular service type this record originates from
        so that it can be used by ``cachedataset()`` via 
        ``make_dataset_filename()``.
        """
        # abstract; specialized for the different service types
        return "dataset"

    def suggest_extension(self, default=None):
        """
        returns a recommended filename extension for the dataset described 
        by this record.  Typically, this would look at the column describing 
        the format and choose an extension accordingly.  This function is 
        specialized for a particular service type this record originates from
        so that it can be used by ``cachedataset()`` via 
        ``make_dataset_filename()``.
        """
        # abstract; specialized for the different service types
        return default


class DALResults(object):
    """
    Results from a DAL query.  It provides random access to records in 
    the response.  Alternatively, it can provide results via a Cursor 
    (compliant with the Python Database API) or an iterable.
    """

    RECORD_CLASS = Record

    def __init__(self, votable, url=None, protocol=None, version=None):
        """
        initialize the cursor.  This constructor is not typically called 
        by directly applications; rather an instance is obtained from calling 
        a DALQuery's execute().

        Parameters
        ----------
        votable : str
           the service response parsed into an
           astropy.io.votable.tree.VOTableFile instance.
        url : str
           the URL that produced the response
        protocol : str
           the name of the protocol that this response (supposedly) complies with
        version : str
           the version of the protocol that this response (supposedly) complies 
           with

        Raises
        ------
        DALFormatError
           if the response VOTable does not contain a response table

        See Also
        --------
        DALFormatError
        """
        self._url = url
        self._protocol = protocol
        self._version = version
        self._status = self._findstatus(votable)
        if self._status[0] != "OK":
            raise DALQueryError(self._status[1], self._status[0], url,
                                self.protocol, self.version)

        self.votable = self._findresultstable(votable)
        if not self.votable:
            raise DALFormatError(reason="VOTable response missing results table",
                                 url=self._url)
        self._fldnames = []
        for field in self.fielddesc():
            if field.ID:
                self._fldnames.append(field.ID)
            else:
                self._fldnames.append(field.name)
        if len(self._fldnames) == 0:
            raise DALFormatError(reason="response table missing column " +
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
    def nrecs(self):
        """
        the number of records returned in this result (read-only)
        """
        return len(self.votable.to_table())

    @property
    def table(self):
        """
        the astropy table object
        """
        return self.votable.to_table()

    def __len__(self):
        """
        return the value of the nrecs property
        """
        return self.nrecs

    def __getitem__(self, indx):
        """
        if indx is a string, r[indx] will return the field with the name of 
        indx; if indx is an integer, r[indx] will return the indx-th record.  
        """
        if isinstance(indx, int):
            return self.getrecord(indx)
        else:
            return self.getcolumn(indx)

    def fielddesc(self):
        """
        return the full metadata for a column as Field instance, a simple 
        object with attributes corresponding the the VOTable FIELD attributes,
        namely: name, id, type, ucd, utype, arraysize, description
        """
        return self.votable.fields

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

    def getcolumn(self, name):
        """
        return a numpy array containing the values for the column with the 
        given name
        """
        if name not in self.fieldnames():
            raise ValueError("No such column name: " + name)
        return self.votable.array[name]

    def getrecord(self, index):
        """
        return a representation of a result record that follows dictionary
        semantics.  The keys of the dictionary are those returned by this
        instance's fieldNames() function: either the column IDs or name, if 
        the ID is not set.  The returned record may have additional accessor 
        methods for getting at stardard DAL response metadata (e.g. ra, dec).

        Parameters
        ----------
        index : int
           the integer index of the desired record where 0 returns the first 
           record

        Returns
        -------
        Record
           a dictionary-like wrapper containing the result record metadata.

        Raises
        ------
        IndexError  
           if index is negative or equal or larger than the number of rows in 
           the result table.

        See Also
        --------
        Record
        """
        return self.RECORD_CLASS(self, index)

    def getvalue(self, name, index):
        """
        return the value of a record attribute--a value from a column and row.

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
        return self.votable.array[name][index]

    def getdesc(self, name):
        """
        return the field description for the record attribute (column) with 
        the given name

        Parameters
        ----------
        name : str
           the name of the attribute (column), chosen from those in fieldnames()

        Returns
        -------
        object   
           with attributes (name, id, datatype, unit, ucd, utype, arraysize) 
           which describe the column

        """
        if name not in self._fldnames:
            raise KeyError(name)
        return self.votable.get_field_by_id_or_name(name)

    def __iter__(self):
        """
        return a python iterable for stepping through the records in this
        result
        """
        return Iter(self)

    def cursor(self):
        """
        return a cursor that is compliant with the Python Database API's 
        :class:`.Cursor` interface.  See PEP 249 for details.  
        """
        from .dbapi2 import Cursor
        return Cursor(self)


class DALQuery(dict):
    """
    a class for preparing a query to a particular service.  Query constraints
    are added via its service type-specific methods. The various execute()
    functions will submit the query and return the results.  

    The base URL for the query can be changed via the baseurl property.
    """

    RESULTS_CLASS = DALResults

    std_parameters = [ ]

    def __init__(self, baseurl, protocol=None, version=None):
        """
        initialize the query object with a baseurl
        """
        self._baseurl = baseurl
        self._protocol = protocol
        self._version = version

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
        The service protocol supported by this query object (read-only).
        """
        return self._protocol

    @property
    def version(self):
        """
        The version of the service protocol supported by this query object
        (read-only).
        """
        return self._version

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
        return self.RESULTS_CLASS(self.execute_votable(), self.getqueryurl())

    def execute_raw(self):
        """
        submit the query and return the raw VOTable XML as a string.

        Raises
        ------
        DALServiceError
           for errors connecting to or communicating with the service
        DALQueryError
           for errors in the input query syntax
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

        Raises
        ------
        DALServiceError
           for errors connecting to or communicating with the service
        DALQueryError
           for errors in the input query syntax
        """
        try:
            return self.submit().raw
        except requests.RequestException as ex:
            raise DALServiceError.from_except(
                ex, self.getqueryurl(), self.protocol, self.version)

    def submit(self):
        """
        does the actual request
        """
        def urlify_param(param):
            if type(param) in (list, tuple):
                return ",".join(map(str, param))
            else:
                return param

        url = self.getqueryurl()
        params = {k: urlify_param(v) for k, v in self.items()}

        r = requests.get(url, params = params, stream = True)
        r.raise_for_status()
        r.raw.read = functools.partial(r.raw.read, decode_content=True)
        return r

    def execute_votable(self):
        """
        submit the query and return the results as an AstroPy votable instance

        Returns
        -------
        astropy.io.votable.tree.Table
           an Astropy votable Table instance

        Raises
        ------
        DALServiceError
           for errors connecting to or communicating with the service
        DALFormatError
           for errors parsing the VOTable response
        DALQueryError
           for errors in the input query syntax

        See Also
        --------
        astropy.io.votable
        DALServiceError
        DALFormatError
        DALQueryError
        """
        try:
            return _votableparse(self.execute_stream().read)
        except DALAccessError:
            raise
        except Exception as e:
            raise DALFormatError(e, self.getqueryurl(), 
                                 protocol=self.protocol, version=self.version)

    def getqueryurl(self):
        """
        return the GET URL that encodes the current query.  This is the 
        URL that the execute functions will use if called next.  

        Returns
        -------
        str
           the encoded query URL

        Parameters
        ----------
        lax : bool
           if False (default), a DALQueryError exception will be 
           raised if the current set of parameters cannot be 
           used to form a legal query.  This implementation does 
           no syntax checking; thus, this argument is ignored.

        Raises
        ------
        DALQueryError
           when lax=False, for errors in the input query syntax

        See Also
        --------
        DALQueryError

        """
        return self.baseurl


class DALService(object):
    """
    an abstract base class representing a DAL service located a particular 
    endpoint.
    """

    QUERY_CLASS = DALQuery

    def __init__(self, baseurl, protocol=None, version=None, resmeta=None):
        """
        instantiate the service connecting it to a base URL

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
           a dictionary containing resource metadata describing the 
           service.  This is usually provided a registry record.
        """
        self._baseurl = baseurl
        self._protocol = protocol
        self._version = version
        self._info = {}
        if resmeta and hasattr(resmeta, "__getitem__"):
            # since this might be (rather, is likely) a Record object, we need 
            # to hand copy it (as the astropy votable bits won't deepcopy).
            for key in resmeta.keys():
                self._info[key] = resmeta[key]  # assuming immutable values

    @property
    def baseurl(self):
        """
        the base URL identifying the location of the service and where 
        queries are submitted (read-only)
        """
        return self._baseurl

    @property
    def protocol(self):
        """
        The service protocol implemented by the service (read-only).
        """
        return self._protocol

    @property
    def version(self):
        """
        The version of the service protocol implemented by the service read-only).
        """
        return self._version

    @property
    def info(self):
        """
        an optional dictionary of resource metadata that describes the 
        service.  This is generally information stored in a VO registry.  
        """
        return self._info

    def search(self, **keywords):
        """
        send a search query to this service.  

        This implementation has no knowledge of the type of service being 
        queried.  The query parameters are given as arbitrary keywords which 
        will be assumed to be understood by the service (i.e. there is no
        argument checking).  The response is a generic DALResults object.  

        Raises
        ------
        DALServiceError
           for errors connecting to or communicating with the service
        DALQueryError  
           for errors either in the input query syntax or other user errors 
           detected by the service
        DALFormatError  
           for errors parsing the VOTable response
        """
        q = self.create_query(**keywords)
        return q.execute()

    def create_query(self, **keywords):
        """
        create a query object that constraints can be added to and then 
        executed.

        Returns
        -------
        DALQuery
           a generic query object
        """
        # this must be overridden to return a Query subclass appropriate for 
        # the service type
        q = self.QUERY_CLASS(self.baseurl, self.protocol, self.version)
        q.update(keywords)
        return q

    def describe(self, verbose=False, width=78, file=None):
        """
        Print a summary description of this service.  

        At a minimum, this will include the service protocol and 
        base URL.  If there is metadata associated with this service, 
        the summary will include other information, such as the 
        service title and description.

        Parameters
        ----------
        verbose : bool
            If false (default), only user-oriented information is 
            printed; if true, additional information will be printed
            as well.
        width : int
            Format the description with given character-width.
        file : writable file-like object
            If provided, write information to this output stream.
            Otherwise, it is written to standard out.  
        """
        if not file:
            file = sys.stdout
        print("{0} v{1} Service".format(self.protocol.upper(), self.version))
        if self.info.get("title"):
            print(para_format_desc(self.info["title"]), file=file)
        if self.info.get("shortName"):
            print("Short Name: " + self.info["shortName"], file=file)
        if self.info.get("publisher"):
            print(para_format_desc("Publisher: " + self.info["publisher"]), 
                  file=file)
        if self.info.get("identifier"):
            print("IVOA Identifier: " + self.info["identifier"], file=file)
        print("Base URL: " + self.baseurl, file=file)

        if self.info.get("description"):
            print(file=file)
            print(para_format_desc(self.info["description"]), file=file)
            print(file=file)

        if self.info.get("subjects"):
            val = self.info.get("subjects")
            if not hasattr(val, "__getitem__"):
                val = [val]
            val = (str(v) for v in val)
            print(para_format_desc("Subjects: " + ", ".join(val)), file=file)
        if self.info.get("waveband"):
            val = self.info.get("waveband")
            if not hasattr(val, "__getitem__"):
                val = [val]
            val = (str(v) for v in val)
            print(para_format_desc("Waveband Coverage: " + ", ".join(val)), 
                  file=file)

        if verbose:
            if self.info.get("capabilityStandardID"):
                print("StandardID: " + self.info["capabilityStandardID"], 
                      file=file)
            if self.info.get("referenceURL"):
                print("More info: " + self.info["referenceURL"], file=file)


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

# Note: this is for Iter subclassess (i.e. .dbapi2.Cursor) and python3
if _is_python3 and not hasattr(Iter, "next"):
    setattr(Iter, "next", lambda self: self.__next__())

if _is_python3:
    _image_mt_re = re.compile(b'^image/(\w+)')
    _text_mt_re = re.compile(b'^text/(\w+)')
    _votable_mt_re = re.compile(b'^(\w+)/(x-)?votable(\+\w+)?')
else:
    _image_mt_re = re.compile(r'^image/(\w+)')
    _text_mt_re = re.compile(r'^text/(\w+)')
    _votable_mt_re = re.compile(r'^(\w+)/(x-)?votable(\+\w+)?')

def mime2extension(mimetype, default=None):
    """
    return a recommended file extension for a file with a given MIME-type.

    This function provides some generic mappings that can be leveraged in 
    implementations of ``suggest_extension()`` in ``Record`` subclasses.

      >>> mime2extension('application/fits')
      fits
      >>> mime2extension('image/jpeg')
      jpg
      >>> mime2extension('application/x-zed', 'dat')
      dat

    Parameters
    ----------
    mimetype : str
       the file MIME-type byte-string to convert
    default : str
       the default extension to return if one could not be 
       recommended based on ``mimetype``.  By convention, 
       this should not include a preceding '.'

    Returns
    -------
    str 
       the recommended extension without a preceding '.', or the 
       value of ``default`` if no recommendation could be made.
    """
    if not mimetype:  
        return default
    if _is_python3 and isinstance(mimetype, str):
        mimetype = mimetype.encode('utf-8')

    if mimetype.endswith(b"/fits") or mimetype.endswith(b'/x-fits'):
        return "fits"
    if mimetype == b"image/jpeg":
        return "jpg"

    m = _votable_mt_re.match(mimetype)  # r'^(\w+)/(x-)?votable(\+\w+)'
    if m:
        return "xml"

    m = _image_mt_re.match(mimetype)    # r'^image/(\w+)'
    if m:
        out = m.group(1).lower()
        if _is_python3:
            out = out.decode('utf-8')
        return out

    m = _text_mt_re.match(mimetype)     # r'^text/(\w+)'
    if m:
        if m.group(1) == b'html' or m.group(1) == b'xml':
            out = m.group(1)
            if _is_python3:
                out = out.decode('utf-8')
            return out
        return "txt"

    return default
        
    

class DALAccessError(Exception):
    """
    a base class for failures while accessing a DAL service
    """
    _defreason = "Unknown service access error"

    def __init__(self, reason=None, url=None, protocol=None, version=None):
        """
        initialize the exception with an error message

        Parameters
        ----------
        reason : str
           a message describing the cause of the error
        url : str
           the query URL that produced the error
        protocol : str
           the label indicating the type service that produced the error
        version : str
           version of the protocol of the service that produced the error
        """
        if not reason: reason = self._defreason
        super(DALAccessError, self).__init__(reason)
        self._reason = reason
        self._url = url
        self._protocol = protocol
        self._version = version

    @classmethod
    def _typeName(cls, exc):
        return re.sub(r"'>$", '', 
                      re.sub(r"<(type|class) '(.*\.)?", '', 
                             str(type(exc))))
    def __str__(self):
        return self._reason
    def __repr__(self):
        return "{0}: {1}".format(self._typeName(self), self._reason)
   
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


class DALProtocolError(DALAccessError):
    """
    a base exception indicating that a DAL service responded in an
    erroneous way.  This can be either an HTTP protocol error or a
    response format error; both of these are handled by separate
    subclasses.  This base class captures an underlying exception
    clause. 
    """
    _defreason = "Unknown DAL Protocol Error"

    def __init__(self, reason=None, cause=None, url=None, 
                 protocol=None, version=None):
        """
        initialize with a string message and an optional HTTP response code

        Parameters
        ----------
        reason : str
           a message describing the cause of the error
        code : int
           the HTTP error code (as an integer)
        cause : str
           an exception issued as the underlying cause.  A value
           of None indicates that no underlying exception was 
           caught.
        url : str
           the query URL that produced the error
        protocol : str
           the label indicating the type service that produced the error
        version : str
           version of the protocol of the service that produced the error
        """
        super(DALProtocolError, self).__init__(reason, url, protocol, version)
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


class DALFormatError(DALProtocolError):
    """
    an exception indicating that a DAL response contains fatal format errors.
    This would include XML or VOTable format errors.  
    """
    _defreason = "Unknown VOTable Format Error"

    def __init__(self, cause=None, url=None, reason=None, 
                 protocol=None, version=None):
        """
        create the exception

        Parameters
        ----------
        cause : str
           an exception issued as the underlying cause.  A value
           of None indicates that no underlying exception was 
           caught.
        url
           the query URL that produced the error
        reason
           a message describing the cause of the error
        protocol
           the label indicating the type service that produced the error
        version
           version of the protocol of the service that produced the error
        """
        if cause and not reason:  
            reason = "{0}: {0}".format(DALAccessError._typeName(cause), 
                                       str(cause))
        super(DALFormatError, self).__init__(reason, cause, url, 
                                             protocol, version)


class DALServiceError(DALProtocolError):
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

        Parameters
        ----------
        reason : str
           a message describing the cause of the error
        code : int
           the HTTP error code (as an integer)
        cause : str
           an exception issued as the underlying cause.  A value
           of None indicates that no underlying exception was 
           caught.
        url : str
           the query URL that produced the error
        protocol : str
           the label indicating the type service that produced the error
        version : str
           version of the protocol of the service that produced the error
        """
        super(DALServiceError, self).__init__(reason, cause, url, 
                                              protocol, version)
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
        create and return DALServiceError exception appropriate
        for the given exception that represents the underlying cause.
        """
        if isinstance(exc, requests.exceptions.RequestException):
            message = str(exc)
            try:
                code = exc.response.status_code
            except AttributeError:
                code = 0

            return DALServiceError(
                message, code, exc, url, protocol, version)
        elif isinstance(exc, Exception):
            return DALServiceError("{0}: {1}".format(cls._typeName(exc), 
                                                     str(exc)), 
                                   cause=exc, url=url, 
                                   protocol=protocol, version=version)
        else:
            raise TypeError("from_except: expected Exception")

class DALQueryError(DALAccessError):
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
        Parameters
        ----------
        reason : str
           a message describing the cause of the error.  This should 
           be set to the content of the INFO error element.
        label : str
           the identifying name of the error.  This should be the 
           value of the INFO element's value attribute within the 
           VOTable response that describes the error.
        url : str
           the query URL that produced the error
        protocol : str
           the label indicating the type service that produced the error
        version : str
           version of the protocol of the service that produced the error
        """
        super(DALQueryError, self).__init__(reason, url, protocol, version)
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
        #from astropy.io.votable.exceptions import W22
        from astropy.io.votable.exceptions import W03,W06,W20,W21,W42,W46,W47,W49,E10
        for warning in (W03, W06, W20, W21, W42, W46, W47, W49, E10):
            warnings.simplefilter("ignore", warning)
# MJG : 021913 - commented out to get CDS responses to work
#        warnings.simplefilter("error", W22)
    except ImportError:
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

# routines used by DALService describe to format metadata

_parasp = re.compile(r"(?:[ \t\r\f\v]*\n){2,}[ \t\r\f\v]*")
_ptag = re.compile(r"\s*(?:<p\s*/?>)|(?:\\para(?:\\ )*)\s*")
def para_format_desc(text, width=78):
    """
    format description text into paragraphs suiteable for display in the 
    shell.  That is, the output will be one or more plain text paragraphs 
    of the prescribed width (78 characters, the default).  The text will 
    be split into separate paragraphs whwre there occurs (1) a two or more 
    consecutive carriage return, (2) an HTMS paragraph tag, or (2) 
    a LaTeX parabraph control sequence.  It will attempt other substitutions
    of HTML and LaTeX markup that sometimes find their way into resource
    descriptions.  
    """
    paras = _parasp.split(text)
    for i in range(len(paras)):
        para = paras.pop(0)
        for p in _ptag.split(para):
            if len(p) > 0:
                p = "\n".join( (l.strip() for l in 
                                (t for t in p.splitlines() if len(t) > 0)) )
                paras.append(deref_markup(p))

    return "\n\n".join( (textwrap.fill(p, width) for p in paras) )

_musubs = [ (re.compile(r"&lt;"), "<"),  (re.compile(r"&gt;"), ">"), 
            (re.compile(r"&amp;"), "&"), (re.compile(r"<br\s*/?>"), ''),
            (re.compile(r"</p>"), ''), (re.compile(r"&#176;"), " deg"),
            (re.compile(r"\$((?:[^\$]*[\*\+=/^_~><\\][^\$]*)|(?:\w+))\$"), 
             r'\1'),
            (re.compile(r"\\deg"), " deg"),
           ]
_alink = re.compile(r'''<a .*href=(["])([^\1]*)(?:\1).*>\s*(\S.*\S)\s*</a>''')
def deref_markup(text):
    """
    perform some substitutions of common markup suitable for text display.
    This includes HTML escape sequence
    """
    for pat, repl in _musubs:
        text = pat.sub(repl, text)
    text = _alink.sub(r"\3 <\2>", text)
    return text

    
        
