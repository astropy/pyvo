# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
MivotInstance is a simple API for building MIVOT instances step by step.
- This code is totally model-agnostic
- The basic syntax rules of MIVOT are checked
- The context dependent syntax rules are ignored

MivotInstance builds <INSTANCE> elements that can contain <ATTRIBUTE>, <INSTANCE> and <REFERENCE>
<COLLECTION> are not supported yet

The code below shows a typical use of MivotInstance:

    .. code-block:: python

    instance1 = MivotInstance(dmtype="model:type.inst", dmid="id1")
    instance1.add_attribute(dmtype="model:type.att1", dmrole="model:type.inst.role1",  value="value1", unit="m/s")
    instance1.add_attribute(dmtype="model:type.att2", dmrole="model:type.inst.role2",  value="value2", unit="m/s")
    
    instance2 = MivotInstance(dmtype="model:type2.inst", dmrole="model:role.instance2", dmid="id2")
    instance2.add_attribute(dmtype="model:type2.att1", dmrole="model:type2.inst.role1", value="value3", unit="m/s")
    instance2.add_attribute(dmtype="model:type2.att2", dmrole="model:type2.inst.role2", value="value4", unit="m/s")
    
    instance1.add_instance(instance2)    
 
    mb =  MivotAnnotations()
    mb.add_templates(instance1)
    mb.build_mivot_block()
    print(mb.mivot_block)

"""
import os
import logging
from pyvo.utils.prototype import prototype_feature
from pyvo.mivot.utils.exceptions import MappingException

@prototype_feature('MIVOT')
class MivotInstance:
    """
    API for building annotations elements step by step.
    """

    def __init__(self, dmtype=None, dmrole=None, dmid=None):
        """
        Constructor
        
        paremeters
        ----------
        dmtype: string
            dmtype of the INSTANCE (mandatory)
        dmrole: string
            dmrole of the INSTANCE (optional)
        dmid: string
            dmid of the INSTANCE (optional)
            
        raise
        -----
        MappingException if no dmtype is provided
        """
        if not dmtype:
            raise MappingException("Cannot build an instance without dmtype")
        self._dmtype = dmtype
        self._dmrole = dmrole
        self._dmid = dmid
        self._content = []
    
    def add_attribute(self, dmtype=None, dmrole=None, ref=None, value=None, unit=None):
        """
        Add an ATTRIBUTE to the instance
        
        paremeters
        ----------
        dmtype: string
            dmtype of the ATTRIBUTE (mandatory)
        dmrole: string
            dmrole of the ATTRIBUTE (optional)
        ref: string
            id of the column to be used to set the attribute value (OPTIONAL)
        value: string
            default value of the attribute value (OPTIONAL)
        unit: string
            attribute unit (OPTIONAL)
            
        raise
        -----
        MappingException if ref and value are both undefined or if no dmtype or no dmrole either
        """
        if not dmtype:
            raise MappingException("Cannot add an attribute without dmtype")
        if not dmrole:
            raise MappingException("Cannot add an attribute without dmrole")
        if not ref and not value:
            raise MappingException("Cannot add an attribute without ref or value either")
        
        xml_string = f'<ATTRIBUTE dmtype="{dmtype}" dmrole="{dmrole}" '
        if unit:
            xml_string += f'unit="{unit}" '
        if value:
            xml_string += f'value="{value}" '
        if ref:
            xml_string += f'ref="{ref}" '
        xml_string += ' />'
        self._content.append(xml_string)

    def add_reference(self, dmrole=None, dmref=None):
        """
        Add an REFERENCE to the instance
        
        paremeters
        ----------
        dmtype: string
            dmtype of the ATTRIBUTE (mandatory)
        dmref: string
            dmrole of the ATTRIBUTE (mandatory)
             
        raise
        -----
        MappingException if dmref or dmrole are undefined
        """
        if not dmref:
            raise MappingException("Cannot add a reference without dmref")
        if not dmrole:
            raise MappingException("Cannot add a reference without dmrole")
        
        xml_string = f'<REFERENCE dmrole="{dmrole}" dmref="{dmref}" />'
        self._content.append(xml_string)
    
    def add_instance(self, mivot_instance):
        """
        Add an INSTANCE to the instance
        
        paremeters
        ----------
        mivot_instance: MivotInstance
            INSTANCE to ab added
        """
        if type(mivot_instance) != MivotInstance:
            raise MappingException("Instance added must be of type MivotInstance")
        self._content.append(mivot_instance.xml_string() )

    
    def xml_string(self):
        """
        Build the XML INSTANCE serialized as a string
        
        returns
        -------
        str
           the string serialization of the XML INSTANCE
        """
        xml_string  = f'<INSTANCE dmtype="{self._dmtype}" '
        if self._dmrole:
            xml_string += f'dmrole="{self._dmrole}" '
        if self._dmid:
            xml_string += f'dmid="{self._dmid}" '
        xml_string += '>\n'
        for element in self._content:
           xml_string += "   " +  element + "\n"
        xml_string += '</INSTANCE>\n'
        return xml_string
        
