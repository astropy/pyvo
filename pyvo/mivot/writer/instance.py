# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
MivotInstance is a simple API for building MIVOT instances step by step.

A MIVOT instance is a MIVOT serialisation of an object whose attributes are set
with column values or literals.
A MIVOT instance can contain ATTRIBUTEs elements, COLLECTIONs of elements, or other INSTANCEs.
The MIVOT INSTANCE structure is defined by the data model on which the data is mapped.
"""

from pyvo.utils.prototype import prototype_feature
from pyvo.mivot.utils.exceptions import MappingError
from pyvo.mivot.utils.mivot_utils import MivotUtils

__all__ = ["MivotInstance"]


@prototype_feature("MIVOT")
class MivotInstance:
    """
    API for building <INSTANCE> elements of MIVOT annotation step by step.

    This class provides methods for incremental construction of a MIVOT instance.
    It builds <INSTANCE> elements that can contain <ATTRIBUTE>, <INSTANCE>, and <REFERENCE>.
    Support for <COLLECTION> elements is not yet implemented.

    The main features are:

    - Model-agnostic: The implementation is independent of any specific data model.
    - Syntax validation: Ensures basic MIVOT syntax rules are followed.
    - Context-agnostic: Ignores context-dependent syntax rules.

    attributes
    ----------
    _dmtype : string
              Instance type (class VO-DML ID)
    _dmrole : string
              Role played by the instance in the context where it is used
              (given by the VO-DML serialization of the model)
    _dmid : string
            Free identifier of the instance

    """
    def __init__(self, dmtype, *, dmrole=None, dmid=None):
        """
        Parameters
        ----------
        dmtype : str
            dmtype of the INSTANCE (mandatory)
        dmrole : str, optional
            dmrole of the INSTANCE
        dmid : str, optional
            dmid of the INSTANCE

        Raises
        ------
        MappingError
            If ``dmtype`` is not provided
        """
        if not dmtype:
            raise MappingError("Cannot build an instance without dmtype")
        self._dmtype = dmtype
        self._dmrole = dmrole
        self._dmid = MivotUtils.format_dmid(dmid)
        self._content = []

    @property
    def dmid(self):
        return self._dmid

    def add_attribute(self, dmtype=None, dmrole=None, *, value=None, unit=None):
        """
        Add an <ATTRIBUTE> element to the instance.

        Parameters
        ----------
        dmtype : str
            dmtype of the ATTRIBUTE (mandatory)
        dmrole : str
            dmrole of the ATTRIBUTE (mandatory)
        value : str or numerical, optional
            ID of the column to set the attribute value.
            If ref is a string starting with a * or is numerical,
            it is considered as a value (* stripped)
            as a ref otherwise
        unit : str, optional
            Unit of the attribute

        Raises
        ------
        MappingError
            If ``dmtype`` or ``dmrole`` is not provided, or if both ``ref`` and ``value`` are not defined
        """
        if not dmtype:
            raise MappingError("Cannot add an attribute without dmtype")
        if not dmrole:
            raise MappingError("Cannot add an attribute without dmrole")
        ref, literal = MivotUtils.get_ref_or_literal(value)
        if not ref and not value:
            raise MappingError("Cannot add an attribute without ref or value")

        xml_string = f'<ATTRIBUTE dmtype="{dmtype}" dmrole="{dmrole}" '
        if unit and unit != "None":
            xml_string += f'unit="{unit}" '
        if literal:
            xml_string += f'value="{literal}" '
        else:
            xml_string += f'ref="{ref}" '
        xml_string += " />"
        self._content.append(xml_string)

    def add_reference(self, dmrole=None, dmref=None):
        """
        Add a <REFERENCE> element to the instance.

        Parameters
        ----------
        dmrole : str
            dmrole of the REFERENCE (mandatory)
        dmref : str
            dmref of the REFERENCE (mandatory)

        Raises
        ------
        MappingError
            If ``dmrole`` or ``dmref`` is not provided
        """
        if not dmref:
            raise MappingError("Cannot add a reference without dmref")
        if not dmrole:
            raise MappingError("Cannot add a reference without dmrole")

        xml_string = f'<REFERENCE dmrole="{dmrole}" dmref="{dmref}" />'
        self._content.append(xml_string)

    def add_instance(self, mivot_instance):
        """
        Add a nested <INSTANCE> element to the instance.

        Parameters
        ----------
        mivot_instance : MivotInstance
            INSTANCE to be added

        Raises
        ------
        MappingError
            If ``mivot_instance`` is not of type ``MivotInstance``
        """
        if not isinstance(mivot_instance, MivotInstance):
            raise MappingError("Instance added must be of type MivotInstance")
        self._content.append(mivot_instance.xml_string())

    def add_collection(self, dmrole, mivot_instances):
        """
        to be documented
        """
        dm_att = ""
        if dmrole:
            dm_att = f"dmrole=\"{dmrole}\""

        self._content.append(f'<COLLECTION {dm_att}>')
        for mivot_instance in mivot_instances:
            if isinstance(mivot_instance, MivotInstance):
                self._content.append(mivot_instance.xml_string())
            else:
                self._content.append(mivot_instance)
            self._content.append("\n")
        self._content.append("</COLLECTION>")

    def xml_string(self):
        """
        Build and serialize the <INSTANCE> element as a string.

        Returns
        -------
        str
            The string representation of the <INSTANCE> element
        """
        xml_string = f'<INSTANCE dmtype="{self._dmtype}" '
        if self._dmrole:
            xml_string += f'dmrole="{self._dmrole}" '
        if self._dmid:
            xml_string += f'dmid="{self._dmid}" '
        xml_string += ">\n"
        for element in self._content:
            xml_string += "   " + element + "\n"
        xml_string += "</INSTANCE>\n"
        return xml_string
