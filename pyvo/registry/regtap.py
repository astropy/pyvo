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

This module provides basic, low-level access to the RegTAP Registry using
standardized TAP-based services.
"""
from __future__ import print_function, division
from ..dal import tap, query as dalq

__all__ = ["search"]

REGISTRY_BASEURL = "http://dc.g-vo.org/tap"

def search(keywords=None, servicetype=None, waveband=None, sqlpred=None):
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
       'scs', 
       'sia' ,
       'ssa',
       'sla',
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
    sqlpred : str
       an SQL WHERE predicate (without the leading "WHERE") 
       that further contrains the search against supported 
       keywords.

    Returns
    -------
    RegistryResults
       a container holding a table of matching resource (e.g. services)

    See Also
    --------
    RegistryResults
    """
    if not any((keywords, servicetype, waveband, sqlpred)):
        raise dalq.DALQueryError(
            "No search parameters passed to registry search")

    joins = set(["rr.interface"])
    wheres = list()

    if keywords:
        joins.add("rr.res_subject")
        joins.add("rr.resource")
        wheres.extend(["({})".format(" OR ".join("""
            1=ivo_nocasematch(res_subject, '%{0}%') OR
            1=ivo_hasword(res_description, '{0}') OR
            1=ivo_hasword(res_title, '{0}')
            """.format(tap.escape(keyword)) for keyword in keywords
        ))])
    
    if servicetype:
        joins.add("rr.interface")
        wheres.append("standard_id LIKE 'ivo://ivoa.net/std/{}%'".format(
            tap.escape(servicetype)))
        wheres.append("intf_type = 'vs:paramhttp'")
    else:
        wheres.append("""(
            standard_id LIKE 'ivo://ivoa.net/std/scs%' OR
            standard_id LIKE 'ivo://ivoa.net/std/sia%' OR
            standard_id LIKE 'ivo://ivoa.net/std/ssa%' OR
            standard_id LIKE 'ivo://ivoa.net/std/sla%' OR
            standard_id LIKE 'ivo://ivoa.net/std/tap%'
        )""")
    
    if waveband:
        joins.add("rr.resource")
        wheres.append("1 = ivo_hashlist_has('{}', waveband)".format(waveband))

    query = """SELECT *
    FROM rr.capability
    {}
    {}
    {}
    """

    query = query.format(
        ''.join("NATURAL JOIN {} ".format(j) for j in joins),
        ("WHERE " if wheres else "") + " AND ".join(wheres),
        sqlpred if sqlpred else ""
    )
    print (query)

    service = tap.TAPService(REGISTRY_BASEURL)
    return service.run_sync(query, maxrec=service.hardlimit)
