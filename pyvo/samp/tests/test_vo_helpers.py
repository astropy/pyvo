# Licensed under a 3-clause BSD style license - see LICENSE.rst

from astropy.io.votable import parse
from astropy.io.votable.tree import Info, Param, VOTableFile
from astropy.table import Table
from pyvo.samp.vo_helpers import accessible_table


def make_votable_with_metadata():
    """Return a VOTableFile with a PARAM and INFO to verify metadata survives."""
    vot = VOTableFile()
    vot.params.append(Param(vot, name="TestParam", value="42", datatype="int"))
    vot.infos.append(Info(name="TestInfo", value="hello"))
    return vot


def test_accessible_table_with_votable():
    vot = make_votable_with_metadata()
    with accessible_table(vot) as url:
        assert url.startswith("file://")
        roundtripped = parse(url[len("file://"):])

    assert roundtripped.params[0].name == "TestParam"
    assert roundtripped.infos[0].name == "TestInfo"


def test_accessible_table_with_astropy_table():
    t = Table({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    with accessible_table(t) as url:
        assert url.startswith("file://")
        roundtripped = parse(url[len("file://"):])

    assert len(roundtripped.get_first_table().array) == 3
