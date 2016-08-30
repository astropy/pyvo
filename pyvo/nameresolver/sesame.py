# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
The CDS Sesame service interface.  This service provides basic information 
about sources--most importantly, its position in the sky--given any of
their official names.  One can resolve names into J2000 positions via the 
functions object2pos() (returning R.A.-Dec. decimal tuples) and 
object2sexapos() (returning positions formated into sexagesimal strings).  
More metadata about the source is available via the resolve() function. 

Full access to the Sesame service capabilities (documented at 
http://cdsweb.u-strasbg.fr/doc/sesame.htx) is available via the SesameQuery 
class.  Sesame can consult three object databases: Simbad, NED, and Vizier; 
Simbad is consulted by default.  

The Sesame service is mirrored at multiple locations; the service
endpoints are listed in this module the ``endpoints`` dictionary where
the keys are short labels indicating the location.  The default one
that will be used is given  by the symbol ``default_endpoint``.  The
function ``set_default_endpoint()`` will set the default endpoint given
its name.  
"""
from __future__ import print_function, division

__all__ = [ "resolve", "object2pos", "object2sexapos", "set_default_endpoint",
            "SesameQuery", "ObjectData" ]

import re
from urllib2 import urlopen
from urllib import quote_plus
import xml.etree.ElementTree as ET
from xml.parsers.expat import ExpatError

from ..dal.query import DALQueryError, DALFormatError, DALServiceError

endpoints = { "cds": "http://cdsweb.u-strasbg.fr/cgi-bin/nph-sesame",
              "cfa": "http://vizier.cfa.harvard.edu/viz-bin/nph-sesame" }
default_endpoint = endpoints["cds"]

def set_default_endpoint(name):
    """
    set the endpoint for the sesame service that will be used by default
    given a short label representing its location.  Currently available 
    labels can be listed via ``endpoints.keys()``; these include "cds"
    and "cfa".  
    """
    global default_endpoint
    try:
        default_endpoint = endpoints[name]
    except KeyError:
        raise LookupError("unrecognized sesame endpoint label: " + name)

def resolve(names, db="Simbad", include="", mirror=None):
    """
    resolve one or more object names each to an :class:`.ObjectData` 
    instance containing metadata about the object.  

    Parameters
    ----------
    names : str or list of str
        either a single object name (as a string) or a list of 
        object names (as in a list of strings).  
    db : str
        the object database to consult as a case-insennitive, 
        minimum match to one of ["Simbad", "NED", "Vizier"].  
    include : str
       strextra data to include (if available) given either as a 
       string or list of stirngs.  If a value is a string, it 
       will be split into a list of words, where each should 
       be a case-insensitive, minimum match to one of "aliases" 
       (additional identifiers that the object is known by) or 
       "fluxes" (flux magnitudes).  
    mirror : str
       Choose the service mirror by a name that is one of 
       "cds" or "cfa".  The default will be service
       pointed to by the modeule attribute, default_endpoint.
       (see also set_default_endpoint().)

    Returns
    -------
    ObjectData
       if a single name was provided, or a 
    list of ObjectData
       if a list of names was given.  See :class:`.ObjectData` for details 
       of the object's contents. 
    """
    baseurl = default_endpoint
    if mirror:
        try:
            baseurl = endpoints[mirror]
        except KeyError:
            raise LookupError("unrecognized sesame mirror: " + mirror)

    q = SesameQuery(baseurl)
    q.useDatabases(db)

    if not isinstance(include, list):
        include = include.strip().split()
    for inc in include:
        opt = filter(lambda i: i.startswith(inc.lower()), 
                     "fluxes aliases".split())
        if len(opt) > 1:
            raise ValueError("Ambiguous include parameter value: " + inc)
        if len(opt) == 0:
            raise ValueError("Unrecognized include parameter value: " + inc)
        if opt[0] == "fluxes":
            q.fluxes = True
        elif opt[0] == "aliases":
            q.aliases = True

    objs = names
    if not isinstance(objs, list):
        objs = [objs]
    q.names = objs

    targets = q.execute()
    out = []
    for t in targets:
        out.append(t.responses[0])

    if isinstance(names, list):
        return out
    return out[0]

def object2pos(names, db="Simbad", mirror=None):
    """
    resolve one or more object names each to a position.

    Parameters
    ----------
    names : str
       either a single object name (as a string) or a list of object names 
       (as in a list of strings).  
    db : str
       the object database to consult as a case-insennitive, 
       minimum match to one of ["Simbad", "NED", "Vizier"].  
    mirror : str
       Choose the service mirror by a name that is one of 
       "cds" or "cfa".  The default will be service
       pointed to by the modeule attribute, default_endpoint.
       (see also set_default_endpoint().)

    Returns
    -------
    tuple
        2-element floating point position if a single name was provided
    list of tuples 
        if a list of names was given
    """
    targetdata = resolve(names, db, mirror=mirror)
    if isinstance(targetdata, list):
        return map(lambda t: t.pos, targetdata)
    else:
        return targetdata.pos

def object2sexapos(names, db="Simbad", mirror=None):
    """
    resolve one or more object names each to a sesagesimal-formatted 
    position.

    Parameters
    ----------
    names : str or list of str
       either a single object name (as a string) or a list of 
       object names (as in a list of strings).  
    db : str
       the object database to consult as a case-insennitive, 
       minimum match to one of ["Simbad", "NED", "Vizier"].  
    mirror : str
       Choose the service mirror by a name that is one of 
       "cds" or "cfa".  The default will be service
       pointed to by the modeule attribute, default_endpoint.
       (see also set_default_endpoint().)

    Returns
    -------
    tuple
       2-element floating point position if a single name was provided
    list of tuples
       if a list of names was given
    """
    targetdata = resolve(names, db, mirror=mirror)
    if isinstance(targetdata, list):
        return map(lambda t: t.sexapos, targetdata)
    else:
        return targetdata.sexapos

class SesameQuery(object):
    """
    a class for preparing a query to a sesame service.  Query constraints 
    are added via properties.  The execute() function will submit the query 
    and return the results.

    The base URL for the query can be changed via the baseurl property.
    """

    database_codes = { "simbad": "S", "vizier": "V",  "ned": "N", "all": "A" }
    

    def __init__(self, baseurl=None):
        """
        initialize the query object with a baseurl

        Parameters
        ----------
        baseurl : str
            the service endpoint.  If None, the value of the 
            module attribute, default_endpoint will be used.
            (see also set_default_endpoint().)
        """
        if not baseurl:
            baseurl = default_endpoint
        self._baseurl = baseurl
        self._dbs = ""
        self._opts = ""
        self._names = []

    @property
    def baseurl(self):
        """
        the base URL that this query will be sent to when one of the 
        execute functions is called. 
        """
        return self._baseurl
    @baseurl.setter
    def baseurl(self, val):
        self._baseurl = val

    @property
    def dbs(self):
        """
        the database selection argument.  This is a sequence of any of the 
        following characters, indicating which databases to query:

           =    ================
           S    Simbad
           V    Vizier
           N    NED
           A    All of the above
           =    ================

        Without ``A`` included, only the result from the database returning 
        a matched result will be returned.  A value preceded by a '~' 
        requests that the result cache be ignored.  

        No syntax checking is done on this value upon setting (though it is
        done via getqueryurl when lax=false); consider using useDatabases().
        """
        return self._dbs
    @dbs.setter
    def dbs(self, val):
        if not isinstance(val, str):
            raise TypeError("dbs must be of type str; given " + type(val))
        self._dbs = val
    @dbs.deleter
    def dbs(self):
        self._dbs = ""

    @property
    def opts(self):
        """
        the options that control the content and format of the output.
        """
        return self._opts
    @opts.setter
    def opts(self, val):
        if val.startswith("-o"):
            val = val[2:]
        self._opts = val
    @opts.deleter
    def opts(self):
        self._opts = ""

    @property
    def ignorecache(self):
        """
        boolean indicating  whether the database caches will be ignored when 
        retrieving results.  If true, the databases will queried directly; 
        otherwise, the cache will be consulted first.  
        """
        return '~' in self._dbs
    @ignorecache.setter
    def ignorecache(self, tf):
        if isinstance(tf, int):
            tf = bool(tf)
        if not isinstance(tf, bool):
            raise TypeError("ignorecache requires bool or int, got: " + 
                            type(tf))

        if '~' in self._dbs:
            if not tf:
                self._dbs = filter(lambda c: c != '~', self._dbs)
        elif tf:
            self._dbs = '~' + self._dbs

    @property
    def aliases(self):
        """
        a boolean indicating whether to return all known identifiers for 
        the resolved source.  If false, only the main designation will be 
        returned.
        """
        return 'I' in self._opts

    @aliases.setter
    def aliases(self, tf):
        if isinstance(tf, int):
            tf = bool(tf)
        if not isinstance(tf, bool):
            raise TypeError("aliases requires bool or int, got: " + 
                            type(tf))
        if 'I' in self._opts:
            if not tf:
                self._opts = filter(lambda c: c != 'I', self._opts)
        elif tf:
            self._opts += 'I'

    
    @property
    def fluxes(self):
        """
        a boolean indicating whether to return all known identifiers for 
        the resolved source.  If false, only the main designation will be 
        returned.
        """
        return self._fluxes
    @fluxes.setter
    def fluxes(self, tf):
        if isinstance(tf, int):
            tf = bool(tf)
        if not isinstance(tf, bool):
            raise TypeError("fluxes requires bool or int, got: " + 
                            type(tf))
        if 'F' in self._opts:
            if not tf:
                self._opts = filter(lambda c: c != 'F', self._opts)
        elif tf:
            self._opts += 'F'

    def useDatabases(self, *args):
        """
        use the given databases to resolve the names.  The arguments are 
        database names that are case-insensitive, minimum matches to any of 
        ``["Simbad", "NED", "Vizier", "all"]``.  The order indicates the 
        order that the databases will be checked.  Unless "all" is included,
        Only the result from the first database returning a positive result
        will be returned by the query.
        """
        bad = []
        use = []
        for arg in args:
            abr = arg.lower()
            db = filter(lambda d: d.startswith(abr), self.database_codes.keys())
            if len(db) != 1:
                bad.append(arg)
            elif db[0] not in use:
                use.append(db[0])

        if len(bad) > 0:
            raise ValueError("Unrecognized or ambiguous database name(s): " + 
                             str(bad))

        self._dbs = "".join(map(lambda d: self.database_codes[d], use))

    def useDefaultDatabase(self):
        """
        clear any previously set database selection so as to use the 
        default database (Simbad) to resolve the targets.  
        """
        self._dbs = ""

    @property
    def names(self):
        """
        the list of the object names to resolve
        """
        return self._names
    @names.setter
    def names(self, names):
        if not isinstance(names, list):
            names = [names]
        self._names = names[:]

    def getqueryurl(self, lax=False, format=None, astext=False):
        """
        return the GET URL that encodes the current query.  This is the 
        URL that the execute functions will use if called next.  

        Parameters
        ----------
        lax : bool
           if False (default), a DALQueryError exception will be 
           raised if the current set of parameters cannot be 
           used to form a legal query.  This implementation does 
           no syntax checking; thus, this argument is ignored.
        format : str
           a format code for the return results, overriding the 
           default XML format.  The value should be one or "x",
           "x4", "x2", "t".  The first three are different 
           versions of the XML formats, and "pc" is the default 
           percent-code format.  
        astext : bool
           request results be returned with a MIME-type of 
           text/plain", regardless of the format.
                      
                   
        Raises
        ------
        DALQueryError
           when lax=False, for errors in the input query syntax
        """
    
        if not lax:
            bad = filter(lambda c: c != '~' and 
                                   c not in set(self.database_codes.values()), 
                         set(self._dbs))
            if len(bad) > 0:
                raise DALQueryError(("database selection, {0}, includes " +
                                    "unrecognized databases: {1}.").format(
                                     self._dbs, str(tuple(bad))))

            bad = filter(lambda c: c not in set("IF"), 
                         set(self._opts))
            if len(bad) > 0:
                raise DALQueryError(("options, {0}, includes " +
                                    "unrecognized items: {0}.").format(
                                     self._opts, str(tuple(bad))))

            if format and format not in "x x2 x4 pc".split():
                raise DALQueryError("unrecognized format: " + format)

            if not self._names:
                raise DALQueryError("No source names provided")

        out = self._baseurl
        opts = "/-o"
        if not format:
            opts += "x"
        elif format and format != "pc":
            opts += format
        if astext:
            opts += 'p'
        if self._opts:
            opts += self._opts
        if len(opts) > 3:
            out += opts

        if self._dbs:
            out += '/' + self._dbs
        out += "?" + "&".join(map(lambda n: quote_plus(n), self._names))

        return out

    def execute_stream(self, format=None, astext=False, lax=False):
        """
        submit the query and return the raw file stream

        Parameters
        ----------
        format : str
           a format code for the return results, overriding the 
           default XML format.  The value should be one or "x",
           "x4", "x2", "t".  The first three are different 
           versions of the XML formats, and "pc" is the default 
           percent-code format.  
        astext : bool
           request results be returned with a MIME-type of 
           "text/plain", regardless of the format.
        lax : bool
           if False (default), a DALQueryError exception will be 
           raised if the current set of parameters cannot be 
           used to form a legal query.  This implementation does 
           no syntax checking; thus, this argument is ignored.

        Raises
        ------
        DALServiceError
           for errors connecting to or communicating with the service
        DALQueryError
           for errors in the input query syntax
        """
        try:
            url = self.getqueryurl(lax, format, astext)
            return urlopen(url)
        except IOError as ex:
            raise DALServiceError.from_except(ex, url)

    def execute(self):
        """
        execute the query and return a list Target instances, one for 
        each requested target.  

        Raises
        ------
        DALServiceError
           for errors connecting to or communicating with the service
        DALQueryError
           for errors in the input query syntax
        DALFormatError
           if the XML response is corrupted
        """
        resp = self.execute_stream(lax=False)
        out = []
        try:
            root = ET.parse(resp).getroot()
            if root.tag != "Sesame":
                raise DALServiceError("Unexpected output: " + ET.dump(root))
            for tel in root.findall('Target'):
                out.append(Target(tel))
        except ExpatError as e:
            raise DALFormatError(e)

        if len(out) == 0:
            raise DALServiceError("No targets resolved")
        return out

class Target(object):
    """
    a result from the name resolver
    """

    def __init__(self, etreeEl):
        """
        Wrap sn XML Target element
        """
        self._data = etreeEl
        resolves = []
        self._lookup = {}
        for resolve in self._data.findall("Resolver"):
            resolves.append(ObjectData(resolve))
            keys = self._parse_resolver_name(resolves[-1].resolver_name)
            self._lookup[keys[1].lower()] = resolves[-1]
        self._responses = tuple(resolves)

    _res_name_pat = re.compile(r'^(\w+)=(\w+)')
    def _parse_resolver_name(self, label):
        m = self._res_name_pat.match(label)
        if m:
            return (m.group(1), m.group(2))
        else:
            return (label[0], label)
        

    @property
    def dbcodes(self):
        """
        the database option codes that were requested in the sesame query
        """
        return self._data.attrib.get("option")

    @property
    def name(self):
        """
        the name of the target that was resolved
        """
        out = self._data.find("name")
        if out is not None: out = out.text
        return out

    @property
    def responses(self):
        """
        the tuple of responses from each of the object databases.  Unless 
        multiple databases were requested (e.g. via SesameQuery.useDatabases())
        this tuple will have only one element.  
        """
        return self._responses

    @property
    def resolved(self):
        """
        a boolean indicating whether the source name was successfully resolved.
        That is, this will be True if at least one database returned a 
        successful response
        """
        return any(map(lambda r: r.success, self._responses))

    def according_to(self, dbname):
        """
        return the object data from a particular resolver given by the 
        case-insensitive, minimum match to one of "Simbad", "NED", and 
        "Vizier".  None is returned if no response from the database is
        available.
        """
        dbn = dbname.lower()
        db = filter(lambda d: d.lower().startswith(dbn), self._lookup.keys())
        if len(db) == 0: return None
        if len(db) > 1:
            raise LookupError("Ambiguous database name: " + dbname)
        return self._lookup[db[0]]
    

class ObjectData(object):
    """
    a container for the target metadata returned from a resolver.  The 
    success attribute will be true if the resolver successfully matched the 
    target name and returned metadata for it.  

    The metadata that gets returned will depend on the resolver, the type of 
    object (and what is known about it), and the input options given in 
    the sesame query.  The full set of possible metadata is given by the 
    class attribute "metadata", a dictionary where the keys are the metadata
    names and each value is a short definition of the corresponding metadatum. 

    A ObjectData instance follows dictionary semantics--i.e. metadata
    can be accessed via the bracket operator ([]) or the get() function.  The
    key() function returns the metadata names that are present.  For most of 
    the metadata, the value will be either a string or a list of strings if 
    more than one value is available (e.g. the alias metadatum).  Exceptions
    are "Vel", "z", "mag", and "plx", which will be of a DocQuantity type, 
    and "pm", which will be of a VecQuantity type.  

    Some important metadata are made available as attributes.  This includes 
    "pos", the decimal J2000 position converted to a 2-elment tuple of floats.
    It also includes "sexapos", the sexagesimal-formatted J2000 position (as 
    a single string), and "oname", the primary name for the target.  If aliases
    were requested, the "aliases" attribute will contain the list of names
    the object is also known as.  
    """

    metadata = {"INFO": "status message from resolver", 
                "ERROR": "error message", 
                "oid": "database-internal object identifier", 
                "otype": "object type code", 
                "jpos": "sexagesimal-formatted J2000 position", 
                "jradeg": "J2000 decimal right ascension", 
                "jdedeg": "J2000 decimal declination", 
                "refPos": "bibcode of reference defining the position", 
                "errRAmas": "milliarcsecond positional error in right ascension", 
                "errDEmas": "milliarcsecond positional error in declination", 
                "pm": "proper motion", 
                "MType": "galaxy classification code", 
                "spType": "", 
                "spNum": "", 
                "Vel": "recessional velocity", 
                "z": "redshift", 
                "mag": "", 
                "plx": "paralax", 
                "oname": "primary name within the resolver database", 
                "alias": "secondary name", 
                "nrefs": "number of literature references consulted for target" 
                }

    _qtype_md = "Vel z mag plx".split()
    _pmtype_md = "pm".split()

    def __init__(self, etreeEl):
        """
        Wrap sn XML Target element
        """
        self._data = etreeEl

    @property
    def resolver_name(self):
        """
        the name of the resolver that produced this information
        """
        return self._data.attrib.get("name")

    def _loadINFOinfo(self):
        for info in self._data.findall('INFO'):
            if info.text == 'from cache':
                self._fromcache = True
            elif info.text == 'Zero (0) answers' or \
                 'Nothing found' in info.text:
                self._success = False
        if not hasattr(self, '_fromcache'):
            self._fromcache = False
        if not hasattr(self, '_success'):
            self._success = True

    @property
    def fromcache(self):
        """
        a boolean indicating as to whether this represents cached information
        """
        if not hasattr(self, '_fromcache'):
            self._loadINFOinfo()
        return self._fromcache

    @property
    def success(self):
        """
        a boolean whether the name was successfully matched (i.e. resolved).
        False indicates that the source name is not found in the resolver's
        database.
        """
        if not hasattr(self, '_success'):
            self._loadINFOinfo()
            if self._success:
                self._success = self.get("ERROR", self._success)
        return self._success

    def get(self, name, defval=None):
        """
        return the target metadata with the given name.  The result will 
        either be a string or a list of strings, depending on whether 
        multiple values were returned with that name. If the name is "alias",
        the response will always be a list.  

        The possible names that can be returned are 
        """
        out = []
        if name in self._qtype_md:
            for el in self._data.findall(name):
                out.append(DocQuantity(el))
        elif name in self._pmtype_md:
            for el in self._data.findall(name):
                out.append(ProperMotion(el))
        else:
            for el in self._data.findall(name):
                out.append(el.text.strip())

        if len(out) == 0:
            return defval
        if len(out) == 1 and name != 'alias':
            out = out[0]
        return out

    def keys(self):
        """
        return the names of the target metadata that are available from 
        this resolver
        """
        out = set()
        for child in self._data.getchildren():
            out.add(child.tag)
        return list(out)

    def __getitem__(self, name):
        return self.get(name)

    @property
    def oname(self):
        return self.get("oname")

    def getpos(self):
        """
        return the decimal J2000 position as a 2-element tuple giving 
        right ascension and declination.  If None, a position 
        was not returned.  

        Raises
        ------
        DALFormatError
           if the position data is incomplete or otherwise contains a 
           formatting error
        """
        ra = self.get("jradeg")
        dec = self.get("jdedeg")
        if ra is None and dec is None:
            return None
        if ra is None:
            raise DALFormatError("Missing RA value (jradeg)")
        if dec is None:
            raise DALFormatError("Missing Dec value (jdedeg)")
        try:
            return (float(ra), float(dec))
        except ValueError:
            raise DALFormatError("Non-float given in ({0}, {1})".format(ra, dec))
        
    @property
    def pos(self):
        """
        the decimal J2000 position as a 2-element tuple giving 
        right ascension and declination.  If None, a valid position 
        was not returned from the resolver.  This differs form getpos() 
        in that accessing will not raise an exception.
        """
        try:
            return self.getpos()
        except Exception:
            return None

    @property
    def sexapos(self):
        """
        the sexagismal formatted position returned by the resolver
        """
        return self.get("jpos")

    @property
    def aliases(self):
        """
        the list of other names the object is known as.  This will be an
        empty list if none were returned 
        """
        return self.get("alias", [])


class DocQuantity(object):
    """
    a documented quantity made up of a value and unit, as well as optionally
    an error, quality flag, and bibcode reference.  If the optional values are 
    not available, the attribute value will be None.

    Attributes
    ----------
    val : float
       the decimal value in the units given by unit
    unit : str
       the string unit
    error : float
       the decimal error in the units given by unit
    qual : str
       a quality code
    ref : str
       a bibcode indicating the literature reference documenting this quantity
    """

    _unit_by_name = { "pm": "mas/yr", "Vel": "km/s", "z": "", "mag": "", 
                      "plx": "mas" }

    def __init__(self, etreeEl):
        d = []
        item = None
        for tag in "veqr":
            item = etreeEl.find(tag)
            if item is not None:
                item = item.text.strip()
            d.append(item)

        if d[0] is None:
            raise DALFormatError("{0}: Missing quantity value".format(
                                  etreeEl.tag))
            
        try:
            self.val = float(d[0])
        except ValueError:
            raise DALFormatError("{0}: non-decimal value: {1}".format(
                                 etreeEl.tag, d[0]))
        self.error = d[1]
        if self.error is not None:
            try:
                self.error = float(d[1])
            except ValueError:
                raise DALFormatError("{0}: non-decimal error: {0}".format(
                                     etreeEl.tag, d[1]))

        self.unit = self._unit_by_name.get(etreeEl.tag)
        self.qual = d[2]
        self.ref = d[3]

    def __str__(self):
        return self.to_string(True)

    def to_string(self, showerr=False):
        """
        convert the quantity to a string, showing the value, unit, and 
        optionally the error

        Parameters
        ----------
        showerr : bool
           if True, the error value will be included; the form
           will be "val +/- error unit".  If False, the error
           will be excluded, as in "val unit".  
        """
        out = "{0}".format(self.val)
        if showerr and self.error:
            out += " +/- {0}".format(self.error)
        if self.unit:
            out += " {0}".format(self.unit)
        return out

    def __repr__(self):
        return "quant({0}, {1}, {2}, {3}, {4})".format(
            self.val, self.unit, self.error, self.qual, self.ref)

class ProperMotion(DocQuantity):
    """
    a documented proper motion quantity made up of a vector magnitude, unit, 
    vector position angle, a vector component along right ascension, and a 
    vector component along declination.  It cann also optionally include
    an error in the magnitude, errors along right ascension and declination, 
    a quality flag, and a bibcode reference.  If the optional values are 
    not available, the attribute value will be None.

    Properties
    ----------
    val : float
       the decimal vector magnitude in the units given by unit
    unit : str
       the string unit
    error : float
       the decimal error in the magnitude in the units given by unit
    qual : str
       a quality code
    ref : str
       a bibcode indicating the literature reference documenting this quantity
    pa : float
       the vector position angle
    pmRA : float
       the vector component along right ascension
    pmDE : float
       the vector component along declination
    epmRA : float
       the error in the vector component along right ascension
    epmDE : float
       the error in the vector component along declination
    """

    def __init__(self, etreeEl):
        super(ProperMotion, self).__init__(etreeEl)

        d = []
        item = None
        for tag in "pa pmRA pmDE epmRA epmDE".split():
            item = etreeEl.find(tag)
            if item is not None:
                try:
                    item = float(item.text.strip())
                except:
                    raise DALFormatError("{0}: non-decimal {0}: {1}".format(
                                         etreeEl.tag, tag, item))
            elif tag in ["pm", "pmRA", "pmDE"]:
                raise DALFormatError("{0}: Missing {1}".format(etreeEl.tag, tag))

            d.append(item)

        self.pa = d[0]
        self.val_ra = d[1]
        self.val_dec = d[2]
        self.error_ra = d[3]
        self.error_dec = d[4]
            
            
    def __repr__(self):
        return "pm({0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9})".format(
             self.val, self.unit, self.error, self.qual, self.ref,
             self.pa, self.val_ra, self.val_dec, self.error_ra, self.error_dec)

