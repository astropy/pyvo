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
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

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

from astropy.extern import six
from astropy.table.table import Table
from astropy.io.votable import parse as votableparse

if six.PY3:
    _mimetype_re = re.compile(b'^\w[\w\-]+/\w[\w\-]+(\+\w[\w\-]*)?(;[\w\-]+(\=[\w\-]+))*$')
else:
    _mimetype_re = re.compile(r'^\w[\w\-]+/\w[\w\-]+(\+\w[\w\-]*)?(;[\w\-]+(\=[\w\-]+))*$')

def is_mime_type(val):
    if type(val) == six.text_type:
        val = val.encode('utf-8')

    return bool(_mimetype_re.match(val))


class DALService(object):
    """
    an abstract base class representing a DAL service located a particular 
    endpoint.
    """

    def __init__(self, baseurl):
        """
        instantiate the service connecting it to a base URL

        Parameters
        ----------
        baseurl :  str 
           the base URL that should be used for forming queries to the service.
        """
        self._baseurl = baseurl

    @property
    def baseurl(self):
        """
        the base URL identifying the location of the service and where 
        queries are submitted (read-only)
        """
        return self._baseurl

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
        q = DALQuery(self.baseurl, **keywords)
        return q

    # TODO: move to pyvo.registry
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


class DALQuery(dict):
    """
    a class for preparing a query to a particular service.  Query constraints
    are added via its service type-specific methods. The various execute()
    functions will submit the query and return the results.  

    The base URL for the query can be changed via the baseurl property.
    """

    _ex = None

    def __init__(self, baseurl, **keywords):
        """
        initialize the query object with a baseurl
        """
        self._baseurl = baseurl.rstrip("?")
        self.update({key.upper(): value for key, value in keywords.items()})

    @property
    def baseurl(self):
        """
        the base URL that this query will be sent to when one of the 
        execute functions is called. 
        """
        return self._baseurl

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
        return DALResults(self.execute_votable(), self.queryurl)

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
        Submit the query and return the raw VOTable XML as a file stream.
        No exceptions are raised here because non-2xx responses might still
        contain payload.
        """
        r = self.submit()

        try:
            r.raise_for_status()
        except requests.RequestException as ex:
            # save for later use
            self._ex = ex
        finally:
            return r.raw

    def submit(self):
        """
        does the actual request
        """
        url = self.queryurl
        params = {k: v for k, v in self.items()}

        r = requests.get(url, params = params, stream = True)
        r.raw.read = functools.partial(r.raw.read, decode_content=True)
        return r

    def execute_votable(self):
        """
        Submit the query and return the results as an AstroPy votable instance.
        As this is the level where qualified error messages are available,
        they are raised here instead of in the underlying execute_stream.

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
            return self._votableparse(self.execute_stream().read)
        except DALAccessError:
            raise
        except Exception as e:
            if self._ex:
                e = self._ex
                raise DALServiceError(
                    str(e), e.response.status_code, e, self.queryurl)
            else:
                raise DALServiceError.from_except(e, self.queryurl)

    @property
    def queryurl(self):
        """
        The URL that encodes the current query. This is the
        URL that the execute functions will use if called next.
        """
        return self.baseurl

    def _votableparse(self, fobj):
        """
        takes a file like object and returns a VOTable instance
        override in subclasses for service specifica.
        """
        return votableparse(fobj, _debug_python_based_parser=True)


class DALResults(object):
    """
    Results from a DAL query.  It provides random access to records in
    the response.  Alternatively, it can provide results via a Cursor
    (compliant with the Python Database API) or an iterable.
    """

    def __init__(self, votable, url=None):
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

        Raises
        ------
        DALFormatError
           if the response VOTable does not contain a response table

        See Also
        --------
        DALFormatError
        """
        self._url = url
        self._status = self._findstatus(votable)
        if self._status[0].upper() not in ("OK", "OVERFLOW"):
            raise DALQueryError(self._status[1], self._status[0], url)

        self.votable = self._findresultstable(votable)
        if not self.votable:
            raise DALFormatError(
                reason="VOTable response missing results table", url=url)

        self._fldnames = [field.name for field in self.votable.fields]
        if not self._fldnames:
            raise DALFormatError(
                reason="response table missing column descriptions.", url=url)

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
    def queryurl(self):
        """
        the URL query that produced these results.  None is returned if unknown
        """
        return self._url

    @property
    def table(self):
        """
        the astropy table object
        """
        return self.votable.to_table()

    def __len__(self):
        """
        return the record count
        """
        return len(self.table)

    def __getitem__(self, indx):
        """
        if indx is a string, r[indx] will return the field with the name of 
        indx; if indx is an integer, r[indx] will return the indx-th record.  
        """
        if isinstance(indx, int):
            return self.getrecord(indx)
        else:
            return self.getcolumn(indx)

    @property
    def fieldnames(self):
        """
        return the names of the columns.  These are the names that are used 
        to access values from the dictionaries returned by getrecord().  They 
        correspond to the column name.
        """
        return self._fldnames[:]

    @property
    def fielddescs(self):
        """
        return the full metadata the columns as a list of Field instances,
        a simple object with attributes corresponding the the VOTable FIELD
        attributes, namely: name, id, type, ucd, utype, arraysize, description
        """
        return self.votable.fields

    def fieldname_with_ucd(self, ucd):
        """
        return the field name that has a given UCD value or None if the UCD 
        is not found.
        """
        try:
            iterchain = (
                self.getdesc(fieldname) for fieldname in self.fieldnames)
            iterchain = (field for field in iterchain if field.ucd == ucd)
            return next(iterchain).name
        except StopIteration:
            return None

    def fieldname_with_utype(self, utype):
        """
        return the field name that has a given UType value or None if the UType 
        is not found.
        """
        try:
            iterchain = (
                self.getdesc(fieldname) for fieldname in self.fieldnames)
            iterchain = (field for field in iterchain if field.utype == utype)
            return next(iterchain).name
        except StopIteration:
            return None

    def getcolumn(self, name):
        """
        return a numpy array containing the values for the column with the 
        given name
        """
        if name not in self.fieldnames:
            raise KeyError("No such column name: " + name)
        return self.votable.array[name]

    def getrecord(self, index):
        """
        return a representation of a result record that follows dictionary
        semantics.  The keys of the dictionary are those returned by this
        instance's fieldnames attribute.The returned record may have additional
        accessor methods for getting at stardard DAL response metadata
        (e.g. ra, dec).

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
        return Record(self, index)

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
        return self.getrecord(index)[name]

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
        def _iter(res):
            pos = 0

            while True:
                try:
                    out = res.getrecord(pos)
                except IndexError:
                    break

                yield out
                pos += 1

        return _iter(self)

    def cursor(self):
        """
        return a cursor that is compliant with the Python Database API's 
        :class:`.Cursor` interface.  See PEP 249 for details.  
        """
        from .dbapi2 import Cursor
        return Cursor(self)


class Record(dict):
    """
    one record from a DAL query result.  The column values are accessible 
    as dictionary items.  It also provides special added functions for 
    accessing the dataset the record corresponds to.  Subclasses may provide
    additional functions for access to service type-specific data.
    """

    def __init__(self, results, index):
        self._results = results

        super(Record, self).__init__()

        self.update(zip(
            results.fieldnames,
            results.votable.array.data[index]
        ))

    def get(self, key, default=None, decode=False):
        """
        This method mimics the dict get method and adds a decode parameter
        to allow decoding of binary strings.
        """
        out = super(Record, self).get(key, default)

        if decode and type(out) == six.binary_type:
            out = out.decode('utf-8')

        return out

    def getbyucd(self, ucd, default=None, decode=False):
        """
        return the column with the given ucd.
        """
        return self.get(
            self._results.fieldname_with_ucd(ucd), default, decode)

    def getbyutype(self, utype, default=None, decode=False):
        """
        return the column with the given utype.

        Raises
        ------
        KeyError
            if theres no column with the given utype.
        """
        return self.get(
            self._results.fieldname_with_utype(utype), default, decode)

    def getdataurl(self):
        """
        return the URL contained in the access URL column which can be used 
        to retrieve the dataset described by this record.  None is returned
        if no such column exists.
        """
        for fieldname in self._results.fieldnames.items():
            field = self._results.getdesc(fieldname)
            if (field.utype and "Access.Reference" in field.utype) or \
               (field.ucd   and "meta.dataset" in field.ucd
                          and "meta.ref.url" in field.ucd):
                out = self[fieldname]
                if type(out) == six.binary_type:
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


class Iter(object):
    def __init__(self, res):
        self.resultset = res
        self.pos = 0

    def __iter__(self):
        return self

    def __next__(self):
        try:
            out = self.resultset.getrecord(self.pos)
            self.pos += 1
            return out
        except IndexError:
            raise StopIteration()

    next = __next__


class Upload(object):
    """
    This class represents a DALI Upload as described in
    http://www.ivoa.net/documents/DALI/20161101/PR-DALI-1.1-20161101.html#tth_sEc3.4.5
    """

    def __init__(self, name, content):
        """
        Initialise the Upload object with the given parameters

        Parameters
        ----------
        name : str
            Tablename for use in queries
        content : object
            If its a file-like object, a string pointing to a local file,
            a `DALResults` object or a astropy table, `is_inline` will be true
            and it will expose a file-like object under `fileobj`

            Otherwise it exposes a URI under `uri`
        """
        try:
            self._is_file = os.path.isfile(content)
        except Exception:
            self._is_file = False
        self._is_fileobj = hasattr(content, "read")
        self._is_table = isinstance(content, Table)
        self._is_resultset = isinstance(content, DALResults)

        self._inline = any((
            self._is_file,
            self._is_fileobj,
            self._is_table,
            self._is_resultset,
        ))

        self._name = name
        self._content = content

    @property
    def is_inline(self):
        """
        True if the upload can be inlined
        """
        return self._inline

    @property
    def name(self):
        return self._name

    def fileobj(self):
        """
        A file-like object for a local resource

        Raises
        ------
        ValueError
            if theres no valid local resource
        """

        if not self.is_inline:
            raise ValueError(
                "Upload {name} doesn't refer to a local resource".format(
                    name = self.name))

        # astropy table
        if isinstance(self._content, Table):
            from io import BytesIO
            fileobj = BytesIO()

            self._content.write(output = fileobj, format = "votable")
            fileobj.seek(0)

            return fileobj
        elif isinstance(self._content, DALResults):
            from io import BytesIO
            fileobj = BytesIO()

            table = self._content.table
            table.write(output = fileobj, format = "votable")
            fileobj.seek(0)

            return fileobj

        fileobj = self._content
        try:
            fileobj = open(self._content)
        finally:
            return fileobj

    def uri(self):
        """
        The URI pointing to the result
        """

        # TODO: use a async job base class instead of hasattr for inspection
        if hasattr(self._content, "result_uri"):
            self._content.raise_if_error()
            uri = self._content.result_uri
        else:
            uri = six.text_type(self._content)

        return uri

    def query_part(self):
        """
        The query part for use in DALI requests
        """

        if self.is_inline:
            value = "{name},param:{name}"
        else:
            value = "{name},{uri}"

        return value.format(name = self.name, uri = self.uri())


class UploadList(list):
    """
    This class extends the native python list with utility functions for
    upload handling
    """

    @classmethod
    def fromdict(cls, dct):
        """
        Constructs a upload list from a dictionary with table_name: content
        """
        return cls(Upload(key, value) for key, value in dct.items())

    def param(self):
        """
        Returns a string suitable for use in UPLOAD parameters
        """
        return ";".join(upload.query_part() for upload in self)


if six.PY3:
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
    if type(mimetype) == six.text_type:
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
        if six.PY3:
            out = out.decode('utf-8')
        return out

    m = _text_mt_re.match(mimetype)     # r'^text/(\w+)'
    if m:
        if m.group(1) == b'html' or m.group(1) == b'xml':
            out = m.group(1)
            if six.PY3:
                out = out.decode('utf-8')
            return out
        return "txt"

    return default
        
    

class DALAccessError(Exception):
    """
    a base class for failures while accessing a DAL service
    """
    _defreason = "Unknown service access error"

    def __init__(self, reason=None, url=None):
        """
        initialize the exception with an error message

        Parameters
        ----------
        reason : str
           a message describing the cause of the error
        url : str
           the query URL that produced the error
        """
        if not reason: reason = self._defreason
        super(DALAccessError, self).__init__(reason)
        self._reason = reason
        self._url = url

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

    @property
    def url(self):
        """
        the URL that produced the error.  If None, the URL is unknown or unset
        """
        return self._url


class DALProtocolError(DALAccessError):
    """
    a base exception indicating that a DAL service responded in an
    erroneous way.  This can be either an HTTP protocol error or a
    response format error; both of these are handled by separate
    subclasses.  This base class captures an underlying exception
    clause. 
    """
    _defreason = "Unknown DAL Protocol Error"

    def __init__(self, reason=None, cause=None, url=None):
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
        """
        super(DALProtocolError, self).__init__(reason, url)
        self._cause = cause

    @property
    def cause(self):
        """
        a string description of what went wrong
        """
        return self._cause

class DALFormatError(DALProtocolError):
    """
    an exception indicating that a DAL response contains fatal format errors.
    This would include XML or VOTable format errors.  
    """
    _defreason = "Unknown VOTable Format Error"

    def __init__(self, cause=None, url=None, reason=None):
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
        """
        if cause and not reason:  
            reason = "{0}: {0}".format(DALAccessError._typeName(cause), 
                                       str(cause))

        super(DALFormatError, self).__init__(reason, cause, url)


class DALServiceError(DALProtocolError):
    """
    an exception indicating a failure communicating with a DAL
    service.  Most typically, this is used to report DAL queries that result 
    in an HTTP error.  
    """
    _defreason = "Unknown service error"
    
    def __init__(self, reason=None, code=None, cause=None, url=None):
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
        """
        super(DALServiceError, self).__init__(reason, cause, url)
        self._code = code

    @property
    def code(self):
        """
        the HTTP error code that resulted from the DAL service query,
        indicating the error.  If None, the service did not produce an HTTP 
        response.
        """
        return self._code

    @classmethod
    def from_except(cls, exc, url=None):
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

            return DALServiceError(message, code, exc, url)
        elif isinstance(exc, Exception):
            return DALServiceError("{0}: {1}".format(cls._typeName(exc), 
                                                     str(exc)), 
                                   cause=exc, url=url)
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

    def __init__(self, reason=None, label=None, url=None):
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
        """
        super(DALQueryError, self).__init__(reason, url)
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

    
        
