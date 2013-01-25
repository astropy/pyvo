"""
The DAL Query interface specialized for Simple Line Access (SLA) services.
"""

import numbers
import re
from . import query

__all__ = [ "sla", "SLAService", "SLAQuery" ]

def sla(url, wavelength):
    """
    submit a simple SLA query that requests spectral lines within a wavelength range
    :Args:
       *url*:  the base URL for the SLA service
       *wavelength*:  a 2-element sequence giving the wavelength spectral range to search in meters
    """
    service = SLAService(url)
    return service.search(wavelength)

class SLAService(query.DalService):
    """
    a representation of an SLA service
    """

    def __init__(self, baseurl, resmeta=None, version="1.0"):
        """
        instantiate an SLA service

        :Args:
           *baseurl*:  the base URL for submitting search queries to the 
                         service.
           *resmeta*:  an optional dictionary of properties about the 
                         service
        """
        query.DalService.__init__(self, baseurl, "sla", version, resmeta)

    def search(self, wavelength, format=None):
        """
        submit a simple SLA query to this service with the given constraints.  

        This method is provided for a simple but typical SLA queries.  For 
        more complex queries, one should create an SLAQuery object via 
        create_query()

        :Args:
           *wavelength*: a 2-element sequence giving the wavelength spectral
                           range to search in meters
           *format*:     the spectral format(s) of interest. "metadata" indicates that no
                           spectra should be returned--only an empty table with complete metadata.
        """
        q = self.create_query(wavelength, format)
        return q.execute()

    def create_query(self, wavelength=None, format=None):
        """
        create a query object that constraints can be added to and then 
        executed.  The input arguments will initialize the query with the 
        given values.

        :Args:
           *wavelength*: a 2-element tuple giving the wavelength spectral
                           range to search in meters
           *format*:     the spectral format(s) of interest. "metadata" indicates that no
                           spectra should be returned--only an empty table with complete metadata.

        :Returns: 
           *SLAQuery*:  the query instance
        """
        q = SLAQuery(self.baseurl, self.version)
        if wavelength is not None: q.wavelength = wavelength
        if format: q.format = format
        return q

class SLAQuery(query.DalQuery):
    """
    a class for preparing an query to an SLA service.  Query constraints
    are added via its service type-specific methods.  The various execute()
    functions will submit the query and return the results.  

    The base URL for the query can be changed via the baseurl property.
    """
    
    def __init__(self, baseurl,  version="1.0", request="queryData"):
        """
        initialize the query object with a baseurl and request type
        """
        query.DalQuery.__init__(self, baseurl, "sla", version)
        self.setparam("REQUEST", request)
        
    @property
    def wavelength(self):
        """
        the wavelength range given in a range-list format
        """
        return self.getparam("WAVELENGTH")
    @wavelength.setter
    def wavelength(self, val):
        regex = "\\d+\\.?\\d*([eE][-+]?\\d+)?/?\\d*\\.?\\d*([eE][-+]?\\d+)?$"
        for part in val.split(","):
           if re.match(regex, part) is None:
               raise ValueError("range syntax is wrong")
        
        self.setparam("WAVELENGTH", val)
    @wavelength.deleter
    def wavelength(self):
        self.unsetparam("WAVELENGTH")

    @property
    def format(self):
        """
        the desired format of the images to be returned.  This will be in the 
        form of a commna-separated lists of MIME-types or one of the following special
        values. 

        :Special Values:
           metadata: no images requested; only an empty table with fields
                          properly specified

        """
        return self.getparam("FORMAT")
    @format.setter
    def format(self, val):
        # check values
        formats = val.split(",")
        for f in formats:
            f = f.lower()
            if f not in ["metadata"]:
                raise ValueError("format type not valid: " + f)

        self.setparam("FORMAT", val)
    @format.deleter
    def format(self):
        self.unsetparam("FORMAT")


    def execute(self):
        """
        submit the query and return the results as a Results subclass instance.
        This implimentation returns an SSAResults instance

        :Raises:
           *DalServiceError*: for errors connecting to or 
                              communicating with the service
           *DalQueryError*:   if the service responds with 
                              an error, including a query syntax error.  
        """
        return SLAResults(self.execute_votable(), self.getqueryurl())


class SLAResults(query.DalResults):
    """
    Results from an SLA query.  It provides random access to records in 
    the response.  Alternatively, it can provide results via a Cursor 
    (compliant with the Python Database API) or an iterator.
    """

    def __init__(self, votable, url=None):
        """
        initialize the cursor.  This constructor is not typically called 
        by directly applications; rather an instance is obtained from calling 
        a SLAQuery's execute().
        """
        query.DalResults.__init__(self, votable, url, "sla", "1.0")
        self._slacols = {


            "ssldm:Line.title": self.fieldname_with_utype("ssldm:Line.title"),
            "ssldm:Line.wavelength.value": self.fieldname_with_utype("ssldm:Line.wavelength.value"),
            "ssldm:Line.initialLevel.energy.value": self.fieldname_with_utype("ssldm:Line.initialLevel.energy.value"),
            "ssldm:Line.finalLevel.energy.value": self.fieldname_with_utype("ssldm:Line.finalLevel.energy.value"),
            "ssldm:Line.environment.temperature.value": self.fieldname_with_utype("ssldm:Line.environment.temperature.value"),
            "ssldm:Line.einsteinA.value": self.fieldname_with_utype("ssldm:Line.einsteinA.value"),
            "ssldm:Process.type": self.fieldname_with_utype("ssldm:Process.type"),
            "ssldm:Process.name": self.fieldname_with_utype("ssldm:Process.name"),
            "ssldm:Line.identificationStatus": self.fieldname_with_utype("ssldm:Line.identificationStatus"),
            "ssldm:Line.initialLevel.name": self.fieldname_with_utype("ssldm:Line.initialLevel.name"),
            "ssldm:Line.finalLevel.name": self.fieldname_with_utype("ssldm:Line.finalLevel.name"),
            "ssldm:Line.observedWavelength.value": self.fieldname_with_utype("ssldm:Line.observedWavelength.value"),
            "slap:Query.Score": self.fieldname_with_utype("slap:Query.Score"),
            "ssldm:Line.initialLevel.configuration": self.fieldname_with_utype("ssldm:Line.initialLevel.configuration"),
            "ssldm:Line.finalLevel.configuration": self.fieldname_with_utype("ssldm:Line.finalLevel.configuration"),
            "ssldm:Line.initialLevel.quantumState": self.fieldname_with_utype("ssldm:Line.initialLevel.quantumState"),
            "ssldm:Line.finalLevel.quantumState": self.fieldname_with_utype("ssldm:Line.finalLevel.quantumState"),
            "Target.Name": self.fieldname_with_utype("Target.Name"),
            "char:SpatialAxis.Coverage.Location.Value": self.fieldname_with_utype("char:SpatialAxis.Coverage.Location.Value"),
            "char:TimeAxis.Coverage.Bounds.Start": self.fieldname_with_utype("char:TimeAxis.Coverage.Bounds.Start"),
            "char:TimeAxis.Coverage.Bounds.Stop": self.fieldname_with_utype("char:TimeAxis.Coverage.Bounds.Stop")
        }
        self._recnames = { "title":   self._slacols["ssldm:Line.title"]}
        
        
    def getrecord(self, index):
        """
        return an SLA result record that follows dictionary
        semantics.  The keys of the dictionary are those returned by this
        instance's fieldNames() function: either the column IDs or name, if 
        the ID is not set.  The returned record has additional accessor 
        methods for getting at standard SLA response metadata (e.g. ra, dec).
        """
        return SLARecord(self, index)

class SLARecord(query.Record):
    """
    a dictionary-like container for data in a record from the results of an
    SLA query, describing an available spectrum.
    """

    def __init__(self, results, index):
        query.Record.__init__(self, results, index)
        self._utypecols = results._slacols
        self._names = results._recnames

    @property
    def title(self):
        """
        return the title of the image
        """
        return self.get(self._names["title"])


        
