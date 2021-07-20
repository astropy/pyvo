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
import functools
import os
from . import rtcons
from ..dal import scs, sia, ssa, sla, tap, query as dalq
from ..utils.formatting import para_format_desc


__all__ = ["search", "RegistryResource", "RegistryResults", "ivoid2service"]

REGISTRY_BASEURL = os.environ.get("IVOA_REGISTRY") or "http://dc.g-vo.org/tap"


# ADQL only has string_agg, where we need string arrays.  We fake arrays
# by joining elements with a token separator that we think shouldn't
# turn up in the things joined.  Of course, people could create
# resources that break us; let's assume there's nothing be gained
# from that ever.
TOKEN_SEP = ":::py VO sep:::"


@functools.lru_cache(1)
def get_RegTAP_service():
    """a lazily created TAP service offering the RegTAP services.

    This uses regtap.REGISTRY_BASEURL.  Always get the TAP service
    there using this function to avoid re-creating the server
    and profit from caching of capabilties, tables, etc.
    """
    return tap.TAPService(REGISTRY_BASEURL)


def search(*constraints:rtcons.Constraint, includeaux=False, **kwargs):
    """
    execute a simple query to the RegTAP registry.

    Parameters
    ----------
    The function accepts query constraint either as Constraint objects
    passed in as positional arguments or as their associated keywords.
    For what constraints are available, see TODO.

    The values of keyword arguments may be tuples or lists when the associated
    Constraint objects take multiple arguments.

    All constraints, whether passed in directly or via keywords, are
    evaluated as a conjunction (i.e., in an AND clause).

    includeaux : boolean
        Flag for whether to include auxiliary capabilities in results.
        This may result in duplicate capabilities being returned,
        especially if the servicetype is not specified.

    Returns
    -------
    RegistryResults
       a container holding a table of matching resource (e.g. services)

    See Also
    --------
    RegistryResults
    """
    constraints = list(constraints)+rtcons.keywords_to_constraints(kwargs)

    # maintain legacy includeaux by locating any Servicetype constraints
    # and replacing them with ones that includes auxiliaries.
    if includeaux:
        for index, constraint in enumerate(constraints):
            if isinstance(constraint, rtcons.Servicetype):
                constraints[index] = constraint.include_auxiliary_services()

    query_sql = rtcons.build_regtap_query(constraints)

    service = get_RegTAP_service()
    query = RegistryQuery(
        service.baseurl, 
        query_sql, 
        maxrec=service.hardlimit)
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
    """

    _service = None

    # the following attribute is used by datasearch._build_regtap_query
    # to figure build the select clause; it is maintained here
    # because this class knows what it expects to get.
    #
    # Each item is either a plain string for a column name, or
    # a 2-tuple for an as clause; all plain strings are used
    # used in the group by, and so it is assumed they are
    # 1:1 to ivoid.
    expected_columns = [
        "ivoid",
        "res_type",
        "short_name",
        "title",
        "content_level",
        "res_description",
        "reference_url",
        "creator_seq",
        "content_type",
        "source_format",
        "region_of_regard",
        "waveband",
        (f"ivo_string_agg(access_url, '{TOKEN_SEP}')", "access_urls"),
        (f"ivo_string_agg(standard_id, '{TOKEN_SEP}')", "standard_ids"),
        (f"ivo_string_agg(intf_role, '{TOKEN_SEP}')", "intf_roles"),]


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

        .. code:: python

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
                "resource, {}, is not a searchable service".format(
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
        stdid = self.get("standard_id", decode=True).lower()
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
        print(para_format_desc(self.res_title), file=file)
        print("Short Name: " + self.short_name, file=file)
        print("IVOA Identifier: " + self.ivoid, file=file)
        if self.access_url:
            print("Base URL: " + self.access_url, file=file)

        if self.res_description:
            print(file=file)
            print(para_format_desc(self.res_description), file=file)
            print(file=file)

        if self.short_name:
            print(
                para_format_desc("Subjects: {}".format(self.short_name)),
                file=file)
        if self.waveband:
            val = (str(v) for v in self.waveband)
            print(
                para_format_desc("Waveband Coverage: " + ", ".join(val)),
                file=file)

        if verbose:
            if self.standard_id:
                print("StandardID: " + self.standard_id, file=file)
            if self.reference_url:
                print("More info: " + self.reference_url, file=file)


def ivoid2service(ivoid, servicetype=None):
    """Return service(s) for a given IVOID.

    The servicetype option specifies the kind of service requested
    (conesearch, sia, ssa, slap, or tap).  By default, if none is
    given, a list of all matching services is returned.

    """
    service = get_RegTAP_service()
    results = service.run_sync("""
        SELECT DISTINCT access_url, standard_id FROM rr.capability
        NATURAL JOIN rr.interface
        WHERE ivoid = '{}'
    """.format(tap.escape(ivoid)))
    services = []
    ivo_cls = {
        "ivo://ivoa.net/std/conesearch":  scs.SCSService,
        "ivo://ivoa.net/std/sia":  sia.SIAService,
        "ivo://ivoa.net/std/ssa":  ssa.SSAService,
        "ivo://ivoa.net/std/sla":  sla.SLAService,
        "ivo://ivoa.net/std/tap":  tap.TAPService
    }
    for result in results:
        thistype = result["standard_id"]
        if thistype not in ivo_cls.keys():
            # This one is not a VO service
            continue
        cls = ivo_cls[thistype]
        if servicetype is not None and servicetype not in thistype:
            # Not the type of service you want
            continue
        elif servicetype is not None:
            # Return only one service, the first of the requested type
            return(cls(result["access_url"]))
        else:
            # Return a list of services
            services.append(cls(result["access_url"]))
    return services
