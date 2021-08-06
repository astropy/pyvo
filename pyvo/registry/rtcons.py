# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Constraints for doing registry searches.

The Constraint class encapsulates a query fragment in a RegTAP query: A
keyword, a sky location, an author name, a class of services.  They are used
either directly as arguments to registry.search, or by passing keyword
arguments into registry.search.  The mapping from keyword arguments to
constraint classes happens through the _keyword attribute in Constraint-derived
classes.
"""

import datetime

import numpy

from ..dal import tap
from ..dal import query as dalq
from ..utils import vocabularies
from .import regtap


# a mapping of service type shorthands to the ivoids of the
# corresponding standards.  This is mostly to keep legacy APIs.
# In the future, preferably rely on shorten_stdid and expand_stdid
# from regtap.
SERVICE_TYPE_MAP = dict((k, "ivo://ivoa.net/std/"+v)
    for k, v in [
        ("image", "sia"),
        ("sia", "sia"),
        ("spectrum", "ssa"),
        ("ssap", "ssa"),
        ("scs", "conesearch"),
        ("line", "slap"),
        ("table", "tap"),
        ("tap", "tap"),
])


def make_sql_literal(value):
    """returns the python value as a SQL-embeddable literal.

    This is not suitable as a device to ward against SQL injections;
    in what we produce, callers could produce arbitrary SQL anyway.
    The point of this function is to minimize surprises when building
    constraints.
    """
    if isinstance(value, str):
        return "'{}'".format(value.replace("'", "''"))

    elif isinstance(value, bytes):
        return "'{}'".format(value.decode("ascii").replace("'", "''"))

    elif isinstance(value, (int, numpy.integer)):
        return "{:d}".format(value)

    elif isinstance(value, (float, numpy.floating)):
        return repr(value)

    elif isinstance(value, datetime.datetime):
        return "'{}'".format(value.isoformat())

    else:
        raise ValueError("Cannot format {} as a SQL literal"
            .format(repr(value)))


class Constraint:
    """an abstract base class for data discovery contraints.

    These, essentially, are configurable RegTAP query fragments,
    consisting of a where clause, parameters for filling that,
    and possibly additional tables.

    Users construct concrete constraints with whatever they would like
    to constrain things with.

    To implement a new constraint, in the constructor set ``_condition`` to a
    string with {}-type replacement fields (assume all parameters are strings),
    and define ``fillers`` to be a dictionary with values for the _condition
    template.  Don't worry about SQL-serialising the values, Constraint takes
    care of that.  If you need your Constraint to be "lazy" 
    (cf. Servicetype), it's ok to overrride get_search_condition without
    an upcall to Constraint.

    If your constraints need extra tables, give them in a list
    in _extra_tables.

    For the legacy x_search with keywords, define a _keyword
    attribute containing the name of the parameter that should
    generate such a constraint.
    """
    _extra_tables = []
    _condition = None
    _fillers = None
    _keyword = None

    def get_search_condition(self):
        if self._condition is None:
            raise NotImplementedError("{} is an abstract Constraint"
                .format(self.__class__.__name__))

        return self._condition.format(**self._get_sql_literals())
  
    def _get_sql_literals(self):
        if self._fillers:
            return {k: make_sql_literal(v) for k, v in self._fillers.items()}
        return {}


class Freetext(Constraint):
    """
    A contraint using plain text to match against title, description, 
    and person names.

    Note that in contrast to regsearch, this will not do a pattern
    search in subjects.

    You can pass in phrases (i.e., multiple words separated by space),
    but behaviour can then change quite significantly between different
    registries.
    """
    _keyword = "keywords"

    def __init__(self, *words:str):
        # cross-table ORs kill the query planner.  We therefore 
        # write the constraint as an IN condition on a UNION
        # of subqueries; it may look as if this has to be
        # really slow, but in fact it's almost always a lot
        # faster than direct ORs.
        base_queries = [
            "SELECT ivoid FROM rr.resource WHERE"
                " 1=ivo_hasword(res_description, {{{parname}}})",
            "SELECT ivoid FROM rr.resource WHERE"
                " 1=ivo_hasword(res_title, {{{parname}}})",
            "SELECT ivoid FROM rr.res_subject WHERE"
                " res_subject ILIKE {{{parpatname}}}"]
        self._fillers, subqueries = {}, []
        
        for index, word in enumerate(words):
            parname = "fulltext{}".format(index)
            parpatname = "fulltextpar{}".format(index)
            self._fillers[parname] = word
            self._fillers[parpatname] = '%'+word+'%'
            for q in base_queries:
                subqueries.append(q.format(**locals()))

        self._condition = "ivoid IN ({})".format(
            " UNION ".join(subqueries))


class Author(Constraint):
    """
    A constraint for creators (“authors”) of a resource; you can use SQL 
    patterns here.

    Note that regrettably there are no guarantees as to how authors
    are written in the VO.  This means that you will generally have
    to write things like ``%Hubble%`` (% being “zero or more characters”
    in SQL) here.

    The match is case-sensitive.
    """
    _keyword = "author"

    def __init__(self, name:str):
        self._condition = "role_name LIKE {auth} AND base_role='creator'"
        self._fillers = {"auth": name}


class Servicetype(Constraint):
    """
    A constraint for for the availability of a certain kind of service
    on the result.

    The constraint is either a bespoke keyword (of which there are at least
    image, spectrum, scs, line, and table; the full list is in 
    SERVICE_TYPE_MAP) or the standards' ivoid (which generally looks like
    ``ivo://ivoa.net/std/<standardname>`` and have to be URIs with
    a scheme part in any case).

    Multiple service types can be passed in; a match in that case
    is for records having any of the service types passed in.

    The match is literal (i.e., no patterns are allowed); this means
    that you will not receive records that only have auxiliary
    services, which is what you want when enumerating all services
    of a certain type in the VO.  In data discovery (where, however,
    you generally should not have Servicetype constraints), you
    can use ``Servicetype(...).include_auxiliary_services()`` or
    use registry.search's ``includeaux`` parameter.
    """
    _keyword = "servicetype"

    def __init__(self, *stds):
        self.stdids = set()

        for std in stds:
            if std in SERVICE_TYPE_MAP:
                self.stdids.add(SERVICE_TYPE_MAP[std])
            elif "://" in std:
                self.stdids.add(std)
            else:
                raise dalq.DALQueryError("Service type {} is neither a full"
                    " standard URI nor one of the bespoke identifiers"
                    " {}".format(std, ", ".join(SERVICE_TYPE_MAP)))

    def get_search_condition(self):
        # we sort the stdids to make it easy for tests (and it's
        # virtually free for the small sets we have here).
        return "standard_id IN ({})".format(
            ", ".join(make_sql_literal(s) for s in sorted(self.stdids)))

    def include_auxiliary_services(self):
        """returns a Servicetype constraint that has self's
        service types but includes the associated auxiliary services.

        This is a convenience to maintain registry.search's signature.
        """
        return Servicetype(*(self.stdids | set(
            std+'#aux' for std in self.stdids)))


class Waveband(Constraint):
    """
    A constraint on messenger particles.

    This builds a constraint against rr.resource.waveband, i.e.,
    a verbal indication of the messenger particle, coming
    from the IVOA vocabulary http://www.ivoa.net/messenger.

    The Spectral constraint enables selections by particle energy,
    but few resources actually give the necessary metadata (in 2021).

    Multiple wavebands can be given (and are effectively combined with OR).
    """
    _keyword = "waveband"
    _legal_terms = None

    def __init__(self, *bands):
        if self.__class__._legal_terms is None:
            self.__class__._legal_terms = {w.lower() for w in
                vocabularies.get_vocabulary("messenger")["terms"]}

        bands = [band.lower() for band in bands]
        for band in bands:
            if band not in self._legal_terms:
                raise dalq.DALQueryError(
                    f"Waveband {band} is not in the IVOA messenger"
                    " vocabulary http://www.ivoa.net/rdf/messenger.")

        self.bands = list(bands)
        self._condition = " OR ".join(
            "1 = ivo_hashlist_has(rr.resource.waveband, {})".format(
                make_sql_literal(band))
            for band in self.bands)


class Datamodel(Constraint):
    """
    A constraint on the adherence to a data model.

    This constraint only lets resources pass that declare support for
    one of several well-known data models; the SQL produced depends
    on the data model identifier.

    Known data models at this point include:

    * obscore -- generic observational data
    * epntap -- solar system data
    * regtap -- the VO registry.

    DM names are matched case-insensitively here mainly for
    historical reasons.
    """
    _keyword = "datamodel"

    # if you add to this list, you have to define a method
    # _make_<dmname>_constraint.
    _known_dms = {"obscore", "epntap", "regtap"}

    def __init__(self, dmname):
        dmname = dmname.lower()
        if dmname not in self._known_dms:
            raise dalq.DALQueryError("Unknown data model id {}.  Known are: {}."
                .format(dmname, ", ".join(sorted(self._known_dms))))
        self._condition = getattr(self, f"_make_{dmname}_constraint")()

    def _make_obscore_constraint(self):
        # There was a bit of chaos with the DM ids for Obscore.
        # Be lenient here
        self._extra_tables = ["rr.res_detail"]
        obscore_pat = 'ivo://ivoa.net/std/obscore%'
        return ("detail_xpath = '/capability/dataModel/@ivo-id'"
            f" AND 1 = ivo_nocasematch(detail_value, '{obscore_pat}')")

    def _make_epntap_constraint(self):
        self._extra_tables = ["rr.res_table"]
        # we include legacy, pre-IVOA utypes for matches; lowercase
        # any new identifiers (utypes case-fold).
        return " OR ".join(
            f"table_utype LIKE {pat}'" for pat in
                ['ivo://vopdc.obspm/std/epncore#schema-2.%',
                    'ivo://ivoa.net/std/epntap#table-2.%'])

    def _make_regtap_constraint(self):
        self._extra_tables = ["rr.res_detail"]
        regtap_pat = 'ivo://ivoa.net/std/RegTAP#1.%'
        return ("detail_xpath = '/capability/dataModel/@ivo-id'"
            f" AND 1 = ivo_nocasematch(detail_value, '{regtap_pat}')")


class Ivoid(Constraint):
    """
    A constraint selecting a single resource by its IVOA identifier.
    """
    _keyword = "ivoid"

    def __init__(self, ivoid):
        self._condition = "ivoid = {ivoid}"
        self._fillers = {"ivoid": ivoid}


class UCD(Constraint):
    """
    A constraint selecting resources having tables with columns having
    UCDs matching a SQL pattern (% as wildcard).  

    Multiple patterns may be passed in and are joined by OR.
    """
    _keyword = "ucd"

    def __init__(self, *patterns):
        self._extra_tables = ["rr.table_column"]
        self._condition = " OR ".join(
            f"ucd LIKE {{ucd{i}}}" for i in range(len(patterns)))
        self._fillers = dict((f"ucd{index}", pattern)
            for index, pattern in enumerate(patterns))
    

# NOTE: If you add new Contraint-s, don't forget to add them in
# registry.__init__ and in docs/registry/index.rst.


def build_regtap_query(constraints):
    """returns a RegTAP query ready for submission from a list of
    Constraint instances.
    """
    if not constraints:
        raise dalq.DALQueryError(
            "No search parameters passed to registry search")

    serialized, extra_tables = [], set()
    for constraint in constraints:
        serialized.append("("+constraint.get_search_condition()+")")
        extra_tables |= set(constraint._extra_tables)
    
    joined_tables = ["rr.resource", "rr.capability", "rr.interface"
        ]+list(extra_tables)

    # see comment in regtap.RegistryResource for the following
    # oddity
    select_clause, plain_columns = [], []
    for col_desc in regtap.RegistryResource.expected_columns:
        if isinstance(col_desc, str):
            select_clause.append(col_desc)
            plain_columns.append(col_desc)
        else:
            select_clause.append("{} AS {}".format(*col_desc))
    
    fragments = ["SELECT",
        ", ".join(select_clause),
        "FROM",
        "\nNATURAL LEFT OUTER JOIN ".join(joined_tables),
        "WHERE",
        "\n  AND ".join(serialized),
        "GROUP BY",
        ", ".join(plain_columns)]

    return "\n".join(fragments)


def keywords_to_constraints(keywords):
    """returns constraints expressed as keywords as Constraint instances.

    This will raise a DALQueryError for unknown keywords.
    """
    constraints = []
    for keyword, value in keywords.items():
        if keyword not in _KEYWORD_TO_CONSTRAINT:
            raise TypeError(f"{keyword} is not a valid registry"
                " constraint keyword.  Use one of {}.".format(
                    ", ".join(sorted(_KEYWORD_TO_CONSTRAINT))))
        if isinstance(value, (tuple, list)):
            constraints.append(_KEYWORD_TO_CONSTRAINT[keyword](*value))
        else:
            constraints.append(_KEYWORD_TO_CONSTRAINT[keyword](value))
    return constraints


def _make_constraint_map():
    """returns a map of _keyword to constraint classes.

    This is used in module initialisation.
    """
    keyword_to_constraint = {}
    for att_name, obj in globals().items():
        if (isinstance(obj, type)
                and issubclass(obj, Constraint) 
                and obj._keyword):
            keyword_to_constraint[obj._keyword] = obj
    return keyword_to_constraint


_KEYWORD_TO_CONSTRAINT = _make_constraint_map()
