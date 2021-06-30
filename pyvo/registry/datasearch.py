# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
data discovery searches in the VO registry.

Searches are built using constraints, which should generally derive
from Constraint; see its docstring for how to write your own constraints.
"""

import datetime

import numpy

from ..dal import tap


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

    elif isinstance(value, int):
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

    To implement a new constraint, set ``_condition`` to a string with
    {}-type replacement fields (assume all parameters are strings), and define
    ``fillers`` to be a dictionary with values for the _condition template.
    Don't worry about SQL-serialising the values, Constraint takes care of that.

    If your constraints need extra tables, give them in a list
    in _extra_tables.
    """
    _extra_tables = []
    _condition = None
    _fillers = None

    def get_search_condition(self):
        if self._condition is None:
            raise NotImplementedError("{} is an abstract Constraint"
                .format(self.__class__.__name__))

        return self._condition.format(**self._get_sql_literals())
  
    def _get_sql_literals(self):
        return {k: make_sql_literal(v) for k, v in self._fillers.items()}


class Freetext(Constraint):
    """plain text to match against title, description, and person names.

    Note that in contrast to regsearch, this will not do a pattern
    search in subjects.

    You can pass in phrases (i.e., multiple words separated by space),
    but behaviour can then change quite significantly between different
    registries.
    """
    def __init__(self, word:str):
        self._condition = ("1=ivo_hasword(res_description, {word})"
            " OR 1=ivo_hasword(res_title, {word})"
            " OR 1=ivo_hasword(role_name, {word})")
        self._fillers = {"word": word}


class Author(Constraint):
    """constrain by a pattern for the creator (“author”) of a resource.

    Note that regrettably there are no guarantees as to how authors
    are written in the VO.  This means that you will generally have
    to write things like ``%Hubble%`` (% being “zero or more characters”
    in SQL) here.

    The match is case-sensitive.
    """
    def __init__(self, name:str):
        self._condition = "role_name LIKE {auth} AND base_role='creator'"
        self._fillers = {"auth": name}


def _build_regtap_query(constraints):
    """returns a RegTAP query ready for submission from a list of
    Constraint instances.
    """
    serialized = []
    for constraint in constraints:
        serialized.append("("+constraint.get_search_condition()+")")

    fragments = ["SELECT ivoid, res_title, res_description",
        "FROM rr.resource",
        "NATURAL JOIN rr.capabilities",
        "WHERE",
        "\n  AND ".join(serialized)]

    return "\n".join(fragments)


def datasearch(*constraints:Constraint):
    """...

    Pass in one or more constraints; a resource matches when it matches
    all of them.
    """
    tap_query = _build_regtap_query(constraints)
