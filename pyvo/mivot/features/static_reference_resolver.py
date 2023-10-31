"""
Created on 22 Dec 2021

@author: laurentmichel
"""
from copy import deepcopy
from pyvo.mivot.utils.exceptions import MappingException
from pyvo.mivot.utils.xml_utils import XmlUtils
from pyvo.utils.prototype import prototype_feature


@prototype_feature('MIVOT')
class StaticReferenceResolver(object):
    """
    Namespace for the function processing the static REFERENCEs
    """

    @staticmethod 
    def resolve(annotation_seeker, templates_ref, instance):
        """
        Resolve all static REFERENCEs found in instance.
        The referenced objects are first searched in GLOBALS and then
        in the templates_ref table.
        REFERENCE elements are replaced with the referenced objects set with the roles of the REFERENCEs
        - An exception is risen if the reference cannot be resolved
        - Works even if REFERENCE tags are numbered by the former processing
        :param annotation_seeker: utility to extract desired elements from the mapping block
        :param templates_ref: Identifier of the table where instance comes from
        :param instance: etree Element
        :return : the number of references resolved
        """
        retour = 0
        for ele in instance.xpath(".//*[starts-with(name(), 'REFERENCE_')]"):
            dmref = ele.get("dmref")
            # If we have no @dmref in REFERENCE, we consider this is a ref based on a keys 
            if dmref == None:
                StaticReferenceResolver.resolve_from_forein_key(ele, annotation_seeker)
                continue
            
            target = annotation_seeker.get_globals_instance_by_dmid(dmref)
            found_in_global = True
            if target is None and templates_ref is not None:
                target = annotation_seeker.get_templates_instance_by_dmid(templates_ref, dmref)
                found_in_global = False
            if target is None:
                raise MappingException(f"Cannot resolve reference={dmref}")
            # Resolve static references recursively
            if found_in_global is False:
                StaticReferenceResolver.resolve(annotation_seeker, templates_ref, ele)
            else:
                StaticReferenceResolver.resolve(annotation_seeker, None, ele)
            # Set the reference role to the copied instance
            target_copy = deepcopy(target)
            #if the reference is within a collection: no role
            if ele.get('dmrole'):
                target_copy.attrib["dmrole"] = ele.get('dmrole')
            parent = ele.getparent()
            # Insert the referenced object
            parent.append(target_copy)
            # Drop the reference
            parent.remove(ele)
            if target_copy.get("dmid") == "GenericMeasure_@flag.variability":
                print(target_copy.tag)
                XmlUtils.pretty_print(ele)
                XmlUtils.pretty_print(target_copy)
                XmlUtils.pretty_print(parent)
            retour += 1
        return retour
            
    @staticmethod 
    def resolve_from_forein_key(ref_element, annotation_seeker):
        """
        Resolve a static reference based on a key mechanism
        e.g.
        <REFERENCE_4 dmrole="coords:Coordinate.coordSys" sourceref="_CoordinateSystems">
            <FOREIGN_KEY ref="_band" value="G"/>
        </REFERENCE_4>
        
        - The target table is meant to be in GLOBALS
        - FOREIGN_KEY@value is not pas of the mapping, it is meant
          to be added by the caller while reading the data rows.

        :param annotation_seeker: Utility to extract desired elements from the mapping block.
        :param ref_element: <REFERENCE> element
        """
        pk_value = None
        for ele in ref_element.xpath(".//FOREIGN_KEY"):
            pk_value = ele.get("value")
            break
        # No pkvalue: likely a dynamic reference (TEMPLATES -> GLOBALS)
        if pk_value is None:
            return
        target = annotation_seeker.get_globals_instance_from_collection(ref_element.get("sourceref"), pk_value)
        StaticReferenceResolver.resolve(annotation_seeker, None, ref_element)
        # Set the reference role to the copied instance
        target_copy = deepcopy(target)
        target_copy.attrib["dmrole"] = ref_element.get('dmrole')
        # Insert the referenced object
        ref_element.getparent().append(target_copy)
        # Drop the reference
        ref_element.getparent().remove(ref_element)
