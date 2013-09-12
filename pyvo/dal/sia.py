# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
A module for searching for images in a remote archive.

A Simple Image Access (SIA) service allows a client to search for
images in an archive whose field of view overlaps with a given
rectangular region on the sky.  The service responds to a search query
with a table in which each row represents an image that is available
for download.  The columns provide metadata describing each image and
one column in particular provides the image's download URL (also
called the *access reference*, or *acref*).  Some SIA services act as
a cut-out service; in this case, the query result is a table of images
whose field of view matches the requested region and which will be
created when accessed via the download URL.

This module provides an interface for accessing an SIA service.  It is 
implemented as a specialization of the DAL Query interface.

The ``search()`` function support the simplest and most common types
of queries, returning an SIAResults instance as its results which
represents the matching imagess from the archive.  The SIAResults
supports access to and iterations over the individual records; these
are provided as SIARecord instances, which give easy access to key
metadata in the response, such as the position of the image's center,
the image format, the size and shape of the image, and its download
URL.

For more complex queries, the SIAQuery class can be helpful which 
allows one to build up, tweak, and reuse a query.  The SIAService
class can represent a specific service available at a URL endpoint.
"""
from __future__ import print_function, division

import numbers, re
from . import query

__all__ = [ "search", "SIAResults", "SIARecord", "SIAQuery", "SIAService" ]

def search(url, pos, size, format='all', intersect="overlaps", verbosity=2,
           **keywords):
    """
    submit a simple SIA query that requests images overlapping a given region

    Parameters
    ----------
    url : str
       the base URL for the SIA service
    pos : 2-element sequence of floats
       the ICRS RA and DEC in decimal degrees
    size : a float or a 2-element sequence of floats
       the size of the rectangular region around pos to search 
       for images, given in decimal degrees.  If a single value is 
       given, the region is a "square".  
    format : str
       the image format(s) of interest.  "all" (default) 
       indicates all available formats; "graphic" indicates
       graphical images (e.g. jpeg, png, gif; not FITS); 
       "metadata" indicates that no images should be 
       returned--only an empty table with complete metadata;
       "image/*" indicates a particular image format where * can 
       have values like "fits", "jpeg", "png", etc. 
    intersect : str
       a case-insensitive token indicating how the returned images should 
       intersect with the search region; recognized values include:

       ========= ======================================================
       COVERS    select images that completely cover the search region
       ENCLOSED  select images that are complete enclosed by the region
       OVERLAPS  select any image that overlaps with the search region
       CENTER    select images whose center is within the search region
       ========= ======================================================

    verbosity : int
       an integer value that indicates the volume of columns
       to return in the result table.  0 means the minimum
       set of columsn, 3 means as many columns as are 
       available.  
    **keywords   
       additional parameters can be given via arbitrary 
       keyword arguments.  These can be either standard 
       parameters (with names drown from the 
       ``SIAQuery.std_parameters`` list) or paramters
       custom to the service.  Where there is overlap 
       with the parameters set by the other arguments to
       this function, these keywords will override.

    Raises
    ------
    DALServiceError
       for errors connecting to or 
       communicating with the service
    DALQueryError
       if the service responds with 
       an error, including a query syntax error.  
    """
    service = SIAService(url)
    return service.search(pos, size, format, intersect, verbosity, **keywords)

class SIAService(query.DALService):
    """
    a representation of an SIA service
    """

    def __init__(self, baseurl, resmeta=None, version="1.0"):
        """
        instantiate an SIA service

        Parameters
        ----------
           *baseurl*:  the base URL for submitting search queries to the 
                         service.
           *resmeta*:  an optional dictionary of properties about the 
                         service
        """
        query.DALService.__init__(self, baseurl, "sia", version, resmeta)

    def search(self, pos, size, format='all', intersect="overlaps", verbosity=2,
               **keywords):
        """
        submit a simple SIA query to this service with the given constraints.  

        This method is provided for a simple but typical SIA queries.  For 
        more complex queries, one should create an SIAQuery object via 
        create_query()

        Parameters
        ----------
           *pos*:        a 2-element tuple giving the ICRS RA and Dec of the 
                           center of the search region in decimal degrees
           *size*:       a 2-element tuple giving the full rectangular size of 
                           the search region along the RA and Dec directions in 
                           decimal degrees
           *format*:     the image format(s) of interest.  "all" (default) 
                           indicates all available formats; "graphic" indicates
                           graphical images (e.g. jpeg, png, gif; not FITS); 
                           "metadata" indicates that no images should be 
                           returned--only an empty table with complete metadata;
                           "image/*" indicates a particular image format where 
                           * can have values like "fits", "jpeg", "png", etc. 
           *intersect*:  a token indicating how the returned images should 
                           intersect with the search region
           *verbosity*:  an integer value that indicates the volume of columns
                           to return in the result table.  0 means the minimum
                           set of columsn, 3 means as many columns as are 
                           available.  
           **keywords:   additional parameters can be given via arbitrary 
                           keyword arguments.  These can be either standard 
                           parameters (with names drown from the 
                           ``SIAQuery.std_parameters`` list) or paramters
                           custom to the service.  Where there is overlap 
                           with the parameters set by the other arguments to
                           this function, these keywords will override.

        Raises
        ------
           *DALServiceError*: for errors connecting to or 
                              communicating with the service
           *DALQueryError*:   if the service responds with 
                              an error, including a query syntax error.  
        """
        q = self.create_query(pos, size, format, intersect, verbosity, 
                              **keywords)
        return q.execute()

    def create_query(self, pos=None, size=None, format=None, intersect=None, 
                     verbosity=None, **keywords):
        """
        create a query object that constraints can be added to and then 
        executed.  The input arguments will initialize the query with the 
        given values.

        Parameters
        ----------
           *pos*:        a 2-element tuple giving the ICRS RA and Dec of the 
                           center of the search region in decimal degrees
           *size*:       a 2-element tuple giving the full rectangular size of 
                           the search region along the RA and Dec directions in 
                           decimal degrees
           *format*:     the image format(s) of interest.  "all" indicates 
                           all available formats; "graphic" indicates
                           graphical images (e.g. jpeg, png, gif; not FITS); 
                           "metadata" indicates that no images should be 
                           returned--only an empty table with complete metadata;
                           "image/*" indicates a particular image format where 
                           * can have values like "fits", "jpeg", "png", etc. 
           *intersect*:  a token indicating how the returned images should 
                           intersect with the search region
           *verbosity*   an integer value that indicates the volume of columns
                           to return in the result table.  0 means the minimum
                           set of columsn, 3 means as many columns as are 
                           available.  
           **keywords:   additional parameters can be given via arbitrary 
                           keyword arguments.  These can be either standard 
                           parameters (with names drown from the 
                           ``SIAQuery.std_parameters`` list) or paramters
                           custom to the service.  Where there is overlap 
                           with the parameters set by the other arguments to
                           this function, these keywords will override.

        :Returns: 
           *SIAQuery*:  the query instance
        """
        q = SIAQuery(self.baseurl, self.version)
        if pos is not None: q.pos = pos
        if size is not None: q.size = size
        if format: q.format = format
        if intersect: q.intersect = intersect
        if verbosity is not None: q.verbosity = verbosity

        for key in keywords.keys():
            q.setparam(key, keywords[key])

        return q

class SIAQuery(query.DALQuery):
    """
    a class for preparing an query to an SIA service.  Query constraints
    are added via its service type-specific methods.  The various execute()
    functions will submit the query and return the results.  

    The base URL for the query can be changed via the baseurl property.
    """
    std_parameters = [ "POS", "SIZE", "INTERSECT", "NAXIS", "CFRAME",
                       "EQUINOX", "CRPIX", "CRVAL", "CDELT", "ROTANG", 
                       "PROJ", "FORMAT", "VERB" ]

    allowed_intersects = "COVERS ENCLOSED CENTER OVERLAPS".split()

    def __init__(self, baseurl, version="1.0"):
        """
        initialize the query object with a baseurl
        """
        query.DALQuery.__init__(self, baseurl, "sia", version)
        

    @property
    def pos(self):
        """
        the position (POS) constraint as a 2-element tuple denoting RA and 
        declination in decimal degrees.  This defaults to None.
        """
        return self.getparam("POS")
    @pos.setter
    def pos(self, pair):
        # do a check on the input
        if (isinstance(pair, list)):
            pair = tuple(pair)
        if (isinstance(pair, tuple)):
            if len(pair) != 2:
                raise ValueError("Wrong number of elements in pos list: " + 
                                 str(pair))
            if (not isinstance(pair[0], numbers.Number) or 
                not isinstance(pair[1], numbers.Number)):
                raise ValueError("Wrong type of elements in pos list: " + 
                                 str(pair))
        else:
            raise ValueError("pos not a 2-element sequence")

        if pair[1] > 90.0 or pair[1] < -90.0:
            raise ValueError("pos declination out-of-range: " + str(pair[1]))

        while pair[0] < 0:
            pair = (pair[0]+360.0, pair[1])
        while pair[0] >= 360.0:
            pair = (pair[0]-360.0, pair[1])


        self.setparam("POS", pair)
    @pos.deleter
    def pos(self):
        self.unsetparam('POS')

    @property
    def ra(self):
        """
        the right ascension part of the position constraint (default: None).
        If this is set but dec has not been set yet, dec will be set to 0.0.
        """
        if not self.pos: return None
        return self.pos[0]
    @ra.setter
    def ra(self, val):
        if not self.pos: self.pos = (0.0, 0.0)
        self.pos = (val, self.pos[1])

    @property
    def dec(self):
        """
        the declination part of the position constraint (default: None).
        If this is set but ra has not been set yet, ra will be set to 0.0.
        """
        if not self.pos: return None
        return self.pos[1]
    @dec.setter
    def dec(self, val):
        if not self.pos: self.pos = (0.0, 0.0)
        self.pos = (self.pos[0], val)

    @property
    def size(self):
        """
        a 2-element tuple giving the size of the rectangular search region
        along the right-ascension and declination directions, measured in 
        decimal degrees.  
        """
        return self.getparam("SIZE")
    @size.setter
    def size(self, val):
        # do a check on the input
        if (isinstance(val, numbers.Number)):
            val = (val, val)
        elif (isinstance(val, list)):
            val = tuple(val)

        if (isinstance(val, tuple)):
            if len(val) != 2:
                raise ValueError("Wrong number of elements in size seq: " + 
                                 str(val))
            if (not isinstance(val[0], numbers.Number) or 
                not isinstance(val[1], numbers.Number)):
                raise ValueError("Wrong type of elements in size seq: " + 
                                 str(val))
        else:
            raise ValueError("size not a 2-element number sequence: " + str(val))

        if val[1] > 180.0 or val[1] <= 0.0:
            raise ValueError("declination size out-of-range: " + str(val[1]))
        if val[0] > 360.0 or val[0] <= 0.0:
            raise ValueError("ra size out-of-range: " + str(val[1]))

        # do check on val; convert single number to a pair
        self.setparam("SIZE", val)
    @size.deleter
    def size(self):
        self.unsetparam("SIZE")

    @property
    def format(self):
        """
        the desired format of the images to be returned.  This will be in 
        the form of a MIME-type (e.g. "image/fits") or one of the following 
        special values.  (Lower case are accepted on setting.)
        :Special Values:
           ALL:  all formats available 
           GRAPHIC:  any graphical format (e.g. JPEG, PNG, GIF)
           GRAPHIC-ALL:  all graphical formats available
           METADATA:  no images reqested; only an empty table with fields 
                          properly specified

        In addition, a value of "GRAPHIC-*fmt[,fmt]*" where *fmt* is graphical 
        format type (e.g. "jpeg", "png", "gif") indicates that a graphical 
        format is desired with a preference for _fmt_ in the order given.
        """
        return self.getparam("FORMAT")
    @format.setter
    def format(self, val):
        if isinstance(val, str):
            uval = val.upper()
            if uval in ["ALL", "GRAPHIC", "GRAPHIC-ALL", "METADATA"]:
                val = uval
            elif uval.startswith("GRAPHIC-"):
                val = uval[:8] + val[8:]
            elif ',' in val:
                # can be a comma-separated list of MIME-types
                self.format = val.split(',')
            elif not query.is_mime_type(val):
                raise ValueError("Not a MIME-type of special value: " + val)

        elif hasattr(val, "__iter__"):
            # accept python iterables of MIME-types
            if len(val) == 0:
                self.unsetparam("FORMAT")
                return
            elif len(val) == 1:
                self.format = list(val)[0]
                return
            bad = filter(lambda f: not query.is_mime_type(f), val)
            if len(bad) > 0:
                raise ValueError("format list can only contain MIME-types; " +
                                 "(bad values: " + ','.join(bad) + ')')
            val = ','.join(val)

        self.setparam("FORMAT", val)
    @format.deleter
    def format(self):
        self.unsetparam("FORMAT")

    @property
    def intersect(self):
        """
        the search constraint that controls how images that overlap the 
        search region are selected.  Allowed (case-insensitive) values 
        include:

        ========= ======================================================
        COVERS    select images that completely cover the search region
        ENCLOSED  select images that are complete enclosed by the region
        OVERLAPS  select any image that overlaps with the search region
        CENTER    select images whose center is within the search region
        ========= ======================================================
        """
        return self.getparam("INTERSECT")
    @intersect.setter
    def intersect(self, val):
        if not isinstance(val, str):
            raise ValueError("intersect value not a string")

        val = val.upper()
        if val not in self.allowed_intersects:
            raise ValueError("unrecogized intersect value: " + val)

        self.setparam("INTERSECT", val)
    @intersect.deleter
    def intersect(self):
        self.unsetparam("INTERSECT")

    @property
    def verbosity(self):
        """
        an integer indicating the amount of metadata (i.e. columns) that will
        be returned by a query where 0 is the minimum amount and 3 is the 
        maximum available.
        """
        return self.getparam("VERB")
    @verbosity.setter
    def verbosity(self, val):
        # do a check on val
        if not isinstance(val, int):
            raise ValueError("verbosity value not an integer: " + val)
        self.setparam("VERB", val)
    @verbosity.deleter
    def verbosity(self):
        self.unsetparam("VERB")


    def execute(self):
        """
        submit the query and return the results as a Results subclass instance.
        This implimentation returns an SIAResults instance

        Raises
        ------
           *DALServiceError*: for errors connecting to or 
                              communicating with the service
           *DALQueryError*:   if the service responds with 
                              an error, including a query syntax error.  
        """
        return SIAResults(self.execute_votable(), self.getqueryurl())


class SIAResults(query.DALResults):
    """
    Results from an SIA query.  It provides random access to records in 
    the response.  Alternatively, it can provide results via a Cursor 
    (compliant with the Python Database API) or an iterable.
    """

    def __init__(self, votable, url=None):
        """
        initialize the cursor.  This constructor is not typically called 
        by directly applications; rather an instance is obtained from calling 
        a SIAQuery's execute().
        """
        query.DALResults.__init__(self, votable, url, "sia", "1.0")
        self._siacols = { 
            "VOX:Image_Title": self.fieldname_with_ucd("VOX:Image_Title"),
            "INST_ID": self.fieldname_with_ucd("INST_ID"),
            "VOX:Image_MJDateObs": self.fieldname_with_ucd("VOX:Image_MJDateObs"),
            "POS_EQ_RA_MAIN":  self.fieldname_with_ucd("POS_EQ_RA_MAIN"),
            "POS_EQ_DEC_MAIN": self.fieldname_with_ucd("POS_EQ_DEC_MAIN"),
            "VOX:Image_Naxes": self.fieldname_with_ucd("VOX:Image_Naxes"),
            "VOX:Image_Naxis": self.fieldname_with_ucd("VOX:Image_Naxis"),
            "VOX:Image_Scale": self.fieldname_with_ucd("VOX:Image_Scale"),
            "VOX:Image_Format": self.fieldname_with_ucd("VOX:Image_Format"),
            "VOX:STC_CoordRefFrame": self.fieldname_with_ucd("VOX:STC_CoordRefFrame"),
            "VOX:STC_CoordEquinox": self.fieldname_with_ucd("VOX:STC_CoordEquinox"),
            "VOX:WCS_CoordProjection": self.fieldname_with_ucd("VOX:WCS_CoordProjection"),
            "VOX:WCS_CoordRefPixel": self.fieldname_with_ucd("VOX:WCS_CoordRefPixel"),
            "VOX:WCS_CoordRefValue": self.fieldname_with_ucd("VOX:WCS_CoordRefValue"),
            "VOX:WCS_CDMatrix": self.fieldname_with_ucd("VOX:WCS_CDMatrix"),
            "VOX:BandPass_ID": self.fieldname_with_ucd("VOX:BandPass_ID"),
            "VOX:BandPass_Unit": self.fieldname_with_ucd("VOX:BandPass_Unit"),
            "VOX:BandPass_RefValue": self.fieldname_with_ucd("VOX:BandPass_RefValue"),
            "VOX:BandPass_HiLimit": self.fieldname_with_ucd("VOX:BandPass_HiLimit"),
            "VOX:BandPass_LoLimit": self.fieldname_with_ucd("VOX:BandPass_LoLimit"),
            "VOX:Image_PixFlags": self.fieldname_with_ucd("VOX:Image_PixFlags"),
            "VOX:Image_AccessReference": self.fieldname_with_ucd("VOX:Image_AccessReference"),
            "VOX:Image_AccessRefTTL": self.fieldname_with_ucd("VOX:Image_AccessRefTTL"),
            "VOX:Image_FileSize": self.fieldname_with_ucd("VOX:Image_FileSize")

            }
        self._recnames = { "title":   self._siacols["VOX:Image_Title"],
                           "ra":      self._siacols["POS_EQ_RA_MAIN"],
                           "dec":     self._siacols["POS_EQ_DEC_MAIN"],
                           "instr":   self._siacols["INST_ID"],
                           "dateobs": self._siacols["VOX:Image_MJDateObs"],
                           "format":  self._siacols["VOX:Image_Format"],
                           "naxes":   self._siacols["VOX:Image_Naxes"],
                           "naxis":   self._siacols["VOX:Image_Naxis"],
                           "acref":   self._siacols["VOX:Image_AccessReference"]
                           }
        
    def getrecord(self, index):
        """
        return an SIA result record that follows dictionary
        semantics.  The keys of the dictionary are those returned by this
        instance's fieldNames() function: either the column IDs or name, if 
        the ID is not set.  The returned record has additional accessor 
        methods for getting at stardard SIA response metadata (e.g. ra, dec).
        """
        return SIARecord(self, index)

class SIARecord(query.Record):
    """
    a dictionary-like container for data in a record from the results of an
    SIA query, describing an available image.
    """

    def __init__(self, results, index):
        query.Record.__init__(self, results, index)
        self._ucdcols = results._siacols
        self._names = results._recnames

    @property
    def ra(self):
        """
        return the right ascension of the center of the image
        """
        return self.get(self._names["ra"])

    @property
    def dec(self):
        """
        return the declination of the center of the image
        """
        return self.get(self._names["dec"])

    @property
    def title(self):
        """
        return the title of the image
        """
        return self.get(self._names["title"])

    @property
    def format(self):
        """
        return the format of the image
        """
        return self.get(self._names["format"])

    @property
    def dateobs(self):
        """
        return the modified Julien date (MJD) of the mid-point of the 
        observational data that went into the image
        """
        return self.get(self._names["dateobs"])

    @property
    def naxes(self):
        """
        return the number of axes in this image.  
        """
        return self.get(self._names["naxes"])

    @property
    def naxis(self):
        """
        return the lengths of the sides along each axis, in pixels, as 
        a sequence
        """
        return tuple(self.get(self._names["naxis"]))

    @property
    def instr(self):
        """
        return the name of the instrument (or instruments) that produced the 
        data that went into this image.
        """
        return self.get(self._names["instr"])

    @property
    def acref(self):
        """
        return the URL that can be used to retrieve the image
        """
        return self.get(self._names["acref"])

    def getdataurl(self):
        """
        return the URL contained in the access URL column which can be used 
        to retrieve the dataset described by this record.  None is returned
        if no such column exists.
        """
        return self.acref

    def suggest_dataset_basename(self):
        """
        return a default base filename that the dataset available via 
        ``getdataset()`` can be saved as.  This function is 
        specialized for a particular service type this record originates from
        so that it can be used by ``cachedataset()`` via 
        ``make_dataset_filename()``.
        """
        out = self.title
        if not out:
            out = "image"
        else:
            out = re.sub(r'\s+', '_', out.strip())
        return out

    def suggest_extension(self, default=None):
        """
        returns a recommended filename extension for the dataset described 
        by this record.  Typically, this would look at the column describing 
        the format and choose an extension accordingly.  
        """
        return query.mime2extension(self.format, default)

        
