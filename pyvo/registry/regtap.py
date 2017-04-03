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

This module provides basic, low-level access to the RegTAP Registries using
standardized TAP-based services.
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)
import os
from ..dal import scs, sia, ssa, sla, tap, query as dalq

__all__ = ["search", "RegistryResource", "RegistryResults", "ivoid2service"]

REGISTRY_BASEURL = os.environ.get("IVOA_REGISTRY") or "http://dc.g-vo.org/tap"

_service_type_map = {
    "image": "sia",
    "spectrum": "ssa",
    "scs": "conesearch",
    "line": "slap",
    "sla": "slap",
    "table": "tap"
}

def search(keywords=None, servicetype=None, waveband=None, datamodel=None):
    """
    execute a simple query to the RegTAP registry.

    Parameters
    ----------
    keywords : list of str
       keyword terms to match to registry records.  
       Use this parameter to find resources related to a 
       particular topic.
    servicetype : str
       the service type to restrict results to.
       Allowed values include
       'conesearch', 
       'sia' ,
       'ssa',
       'slap',
       'tap'
    waveband : str
       the name of a desired waveband; resources returned 
       will be restricted to those that indicate as having
       data in that waveband.  Allowed values include
       'radio',
       'millimeter',
       'infrared',
       'optical',
       'uv',
       'euv',
       'x-ray'
       'gamma-ray'
    datamodel : str
        the name of the datamodel to search for; makes only sence in conjunction
        with servicetype tap (or no servicetype).

        See http://wiki.ivoa.net/twiki/bin/view/IVOA/IvoaDataModel for more
        informations about data models.

    Returns
    -------
    RegistryResults
       a container holding a table of matching resource (e.g. services)

    See Also
    --------
    RegistryResults
    """
    if not any((keywords, servicetype, waveband, datamodel)):
        raise dalq.DALQueryError(
            "No search parameters passed to registry search")

    joins = set(["rr.interface", "rr.resource"])
    wheres = list()

    if keywords:
        joins.add("rr.res_subject")
        joins.add("rr.resource")
        wheres.extend(["({})".format(" AND ".join("""
            (
                1=ivo_nocasematch(res_subject, '%{0}%') OR
                1=ivo_hasword(res_description, '{0}') OR
                1=ivo_hasword(res_title, '{0}')
            )""".format(tap.escape(keyword)) for keyword in keywords
        ))])
    
    if servicetype:
        servicetype = _service_type_map.get(servicetype, servicetype)

        joins.add("rr.interface")
        wheres.append("standard_id LIKE 'ivo://ivoa.net/std/{}%'".format(
            tap.escape(servicetype)))
        wheres.append("intf_type = 'vs:paramhttp'")
    else:
        wheres.append("""(
            standard_id LIKE 'ivo://ivoa.net/std/conesearch%' OR
            standard_id LIKE 'ivo://ivoa.net/std/sia%' OR
            standard_id LIKE 'ivo://ivoa.net/std/ssa%' OR
            standard_id LIKE 'ivo://ivoa.net/std/slap%' OR
            standard_id LIKE 'ivo://ivoa.net/std/tap%'
        )""")
    
    if waveband:
        joins.add("rr.resource")
        wheres.append("1 = ivo_hashlist_has('{}', waveband)".format(
            tap.escape(waveband)))

    if datamodel:
        joins.add("rr.interface")
        joins.add("rr.res_detail")

        wheres.append("intf_type = 'vs:paramhttp'")
        wheres.append("detail_xpath='/capability/dataModel/@ivo-id'")
        wheres.append(
            "1=ivo_nocasematch(detail_value, 'ivo://ivoa.net/std/{0}%')".format(
                tap.escape(datamodel)))

    query = """SELECT DISTINCT rr.interface.*, rr.capability.*, rr.resource.*
    FROM rr.capability
    {}
    {}
    """.format(
        ''.join("NATURAL JOIN {} ".format(j) for j in joins),
        ("WHERE " if wheres else "") + " AND ".join(wheres)
    )

    service = tap.TAPService(REGISTRY_BASEURL)
    query = RegistryQuery(service.baseurl, query, maxrec=service.hardlimit)
    return query.execute()


class RegistryQuery(tap.TAPQuery):
    def execute(self):
        """
        submit the query and return the results as a RegistryResults instance

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
        return RegistryResults(self.execute_votable(), self.queryurl)


class RegistryResults(dalq.DALResults):
    """
    an iterable set of results from a registry query. Each record is
    returned as RegistryResults
    """
    def getrecord(self, index):
        """
        return all the attributes of a resource record with the given index
        as SimpleResource instance (a dictionary-like object).

        Parameters
        ----------
        index  : int
            the zero-based index of the record
        """
        return RegistryResource(self, index)


class RegistryResource(dalq.Record):
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

    _service = None

    @property
    def ivoid(self):
        """
        the IVOA identifier for the resource.
        """
        return self.get("ivoid", decode=True)

    @property
    def res_type(self):
        """
        the resource types that characterize this resource.
        """
        return self.get("res_type", decode=True)

    @property
    def short_name(self):
        """
        the short name for the resource
        """
        return self.get("short_name", decode=True)

    @property
    def res_title(self):
        """
        the title of the resource
        """
        return self.get("res_title", default=None, decode=True)

    @property
    def content_levels(self):
        """
        a list of content level labels that describe the intended audience
        for this resource.
        """
        return self.get("content_level", default="", decode=True).split("#")

    @property
    def res_description(self):
        """
        the textual description of the resource.

        See Also
        --------
        SimpleResource.describe
        """
        return self.get("res_description", decode=True)

    @property
    def reference_url(self):
        """
        URL pointing to a human-readable document describing this resource.
        """
        return self.get("reference_url", decode=True)

    @property
    def creators(self):
        """
        The creator(s) of the resource
        in the ordergiven by the resource record author
        """
        return self.get("creator_seq", default="", decode=True).split(";")

    @property
    def content_types(self):
        """
        list of natures or genres of the content of the resource.
        """
        return self.get("content_type", decode=True).split("#")

    @property
    def source_format(self):
        """
        The format of source_value.
        """
        return self.get("source_format", decode=True)

    @property
    def region_of_regard(self):
        """
        numeric value representing the angle, given in decimal degrees,
        by which a positional query against this resource should be "blurred"
        in order to get an appropriate match.
        """
        return float(self.get("region_of_regard", 0))

    @property
    def waveband(self):
        """
        a list of names of the wavebands that the resource provides data for
        """
        return self.get("waveband", default="", decode=True).split("#")

    @property
    def access_url(self):
        """
        the URL that can be used to access the service resource.
        """
        return self.get("access_url", decode=True)

    @property
    def standard_id(self):
        """
        the IVOA standard identifier
        """
        return self.get("standard_id", decode=True)

    @property
    def service(self):
        """
        return an appropriate DALService subclass for this resource that
        can be used to search the resource.  Return None if the resource is
        not a recognized DAL service.  Currently, only Conesearch, SIA, SSA,
        and SLA services are supported.
        """
        if self.access_url:
            for key, value in {
                "ivo://ivoa.net/std/conesearch":  scs.SCSService,
                "ivo://ivoa.net/std/sia":  sia.SIAService,
                "ivo://ivoa.net/std/ssa":  ssa.SSAService,
                "ivo://ivoa.net/std/sla":  sla.SLAService,
                "ivo://ivoa.net/std/tap":  tap.TAPService,
            }.items():
                if key in self.standard_id:
                    self._service = value(self.access_url)

        return self._service

    def search(self, *args, **keys):
        """
        assuming this resource refers to a searchable service, execute a
        search against the resource.  This is equivalent to:

           self.to_service().search(*args, **keys)

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
        if not self.service:
            raise dalq.DALServiceError(
                "resource, {0}, is not a searchable service".format(
                    self.short_name))

        return self.service.search(*args, **keys)

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
        restype = "Custom Service"
        stdid = self.get("standard_id").lower()
        if stdid:
            if stdid.startswith("ivo://ivoa.net/std/conesearch"):
                restype = "Catalog Cone-search Service"
            elif stdid.startswith("ivo://ivoa.net/std/sia"):
                restype = "Image Data Service"
            elif stdid.startswith("ivo://ivoa.net/std/ssa"):
                restype = "Spectrum Data Service"
            elif stdid.startswith("ivo://ivoa.net/std/slap"):
                restype = "Spectral Line Database Service"
            elif stdid.startswith("ivo://ivoa.net/std/tap"):
                restype = "Table Access Protocol Service"

        print(restype, file=file)
        print(dalq.para_format_desc(self.res_title), file=file)
        print("Short Name: " + self.short_name, file=file)
        #print("Publisher: " + dalq.para_format_desc(self.publisher), file=file)
        print("IVOA Identifier: " + self.ivoid, file=file)
        if self.access_url:
            print("Base URL: " + self.access_url, file=file)

        if self.res_description:
            print(file=file)
            print(dalq.para_format_desc(self.res_description), file=file)
            print(file=file)

        if self.short_name:
            print(dalq.para_format_desc("Subjects: {}".format(self.short_name)),
                  file=file)
        if self.waveband:
            val = (str(v) for v in self.waveband)
            print(dalq.para_format_desc("Waveband Coverage: " + ", ".join(val)),
                  file=file)

        if verbose:
            if self.standard_id:
                print("StandardID: " + self.standard_id, file=file)
            if self.reference_url:
                print("More info: " + self.reference_url, file=file)

def ivoid2service(ivoid):
    service = tap.TAPService(REGISTRY_BASEURL)
    results = service.run_sync("""
        SELECT DISTINCT access_url, standard_id FROM rr.capability
        NATURAL JOIN rr.interface
        WHERE ivoid = '{}'
    """.format(tap.escape(ivoid)))

    for result in results:
        for ivo, cls in {
            "ivo://ivoa.net/std/conesearch":  scs.SCSService,
            "ivo://ivoa.net/std/sia":  sia.SIAService,
            "ivo://ivoa.net/std/ssa":  ssa.SSAService,
            "ivo://ivoa.net/std/sla":  sla.SLAService,
            "ivo://ivoa.net/std/tap":  tap.TAPService,
        }.items():
            if result["standard_id"] in ivo:
                return cls(result["access_url"])

    return None
