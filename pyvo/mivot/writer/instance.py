# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
MivotInstance is a simple API for building MIVOT instances step by step.

Features
--------
- Model-agnostic: The implementation is independent of any specific data model.
- Syntax validation: Ensures basic MIVOT syntax rules are followed.
- Context-agnostic: Ignores context-dependent syntax rules.

MivotInstance builds <INSTANCE> elements that can contain <ATTRIBUTE>, <INSTANCE>, and <REFERENCE>.
Support for <COLLECTION> elements is not yet implemented.

Usage Example
-------------
.. code-block:: python

    position = MivotInstance(dmtype="model:mango:EpochPosition", dmid="position")
    position.add_attribute(dmtype="ivoa.RealQuantity",
                           dmrole="mango:EpochPosition.longitude",
                           unit="deg", ref="_RA_ICRS")
    position.add_attribute(dmtype="ivoa.RealQuantity", dmrole="mango:EpochPosition.latitude",
                           unit="deg", ref="_DFEC_ICRS")

    position_error = MivotInstance(dmtype="mango:EpochPositionErrors",
                                   dmrole="mango:EpochPosition.errors", dmid="id2")
    position_error.add_attribute(dmtype="model:type2.att1",
                                 dmrole="model:type2.inst.role1", value="value3", unit="m/s")
    position_error.add_attribute(dmtype="model:type2.att2",
                                 dmrole="model:type2.inst.role2", value="value4", unit="m/s")

    position.add_instance(position_error)

    mb = MivotAnnotations()
    mb.add_templates(position)
    mb.build_mivot_block()
    print(mb.mivot_block)
"""

from pyvo.utils.prototype import prototype_feature
from pyvo.mivot.utils.exceptions import MappingError


@prototype_feature("MIVOT")
class MivotInstance:
    """
    API for building <INSTANCE> elements of a MIVOT annotation step by step.

    This class provides methods for adding attributes, references, and nested instances,
    allowing incremental construction of a MIVOT instance.
    """

    def __init__(self, dmtype=None, dmrole=None, dmid=None):
        """
        Initialize a MivotInstance object.

        Parameters
        ----------
        dmtype : str
            The dmtype of the INSTANCE (mandatory).
        dmrole : str, optional
            The dmrole of the INSTANCE.
        dmid : str, optional
            The dmid of the INSTANCE.

        Raises
        ------
        MappingError
            If `dmtype` is not provided.
        """
        if not dmtype:
            raise MappingError("Cannot build an instance without dmtype")
        self._dmtype = dmtype
        self._dmrole = dmrole
        self._dmid = dmid
        self._content = []

    def add_attribute(self, dmtype=None, dmrole=None, ref=None, value=None, unit=None):
        """
        Add an <ATTRIBUTE> element to the instance.

        Parameters
        ----------
        dmtype : str
            The dmtype of the ATTRIBUTE (mandatory).
        dmrole : str
            The dmrole of the ATTRIBUTE (mandatory).
        ref : str, optional
            ID of the column to set the attribute value.
        value : str, optional
            Default value of the attribute.
        unit : str, optional
            Unit of the attribute.

        Raises
        ------
        MappingError
            If `dmtype` or `dmrole` is not provided, or if both `ref` and `value` are not defined.
        """
        if not dmtype:
            raise MappingError("Cannot add an attribute without dmtype")
        if not dmrole:
            raise MappingError("Cannot add an attribute without dmrole")
        if not ref and not value:
            raise MappingError("Cannot add an attribute without ref or value")

        xml_string = f'<ATTRIBUTE dmtype="{dmtype}" dmrole="{dmrole}" '
        if unit:
            xml_string += f'unit="{unit}" '
        if value:
            xml_string += f'value="{value}" '
        if ref:
            xml_string += f'ref="{ref}" '
        xml_string += " />"
        self._content.append(xml_string)

    def add_reference(self, dmrole=None, dmref=None):
        """
        Add a <REFERENCE> element to the instance.

        Parameters
        ----------
        dmrole : str
            The dmrole of the REFERENCE (mandatory).
        dmref : str
            The dmref of the REFERENCE (mandatory).

        Raises
        ------
        MappingError
            If `dmrole` or `dmref` is not provided.
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
            The INSTANCE to be added.

        Raises
        ------
        MappingError
            If `mivot_instance` is not of type `MivotInstance`.
        """
        if not isinstance(mivot_instance, MivotInstance):
            raise MappingError("Instance added must be of type MivotInstance")
        self._content.append(mivot_instance.xml_string())

    def xml_string(self):
        """
        Build and serialize the INSTANCE element to a string.

        Returns
        -------
        str
            The string representation of the INSTANCE element.
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