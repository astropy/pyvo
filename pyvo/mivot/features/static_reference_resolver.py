"""
Class used to resolve each static REFERENCE found in instance.
"""
from copy import deepcopy
from pyvo.mivot.utils.exceptions import ResolveException, NotImplementedException
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
        The referenced objects are first searched in GLOBALS and then in the templates_ref table.
        REFERENCE elements are replaced with the referenced objects set with the roles of the REFERENCEs.
        Works even if REFERENCE tags are numbered by the former processing.
        :param annotation_seeker: utility to extract desired elements from the mapping block
        :param templates_ref: Identifier of the table where instance comes from
        :param instance: `~lxml.etree._Element` object
        :return: the number of references resolved
        :rtype: int
        :raises MappingException: if the reference cannot be resolved
        """
        retour = 0
        for ele in instance.xpath(".//*[starts-with(name(), 'REFERENCE_')]"):
            dmref = ele.get("dmref")
            # If we have no @dmref in REFERENCE, we consider this is a ref based on a keys 
            if dmref == None:
                raise NotImplementedException("Dynamic reference not implemented")
             
            target = annotation_seeker.get_globals_instance_by_dmid(dmref)
            found_in_global = True
            if target is None and templates_ref is not None:
                target = annotation_seeker.get_templates_instance_by_dmid(templates_ref, dmref)
                found_in_global = False
            if target is None:
                raise ResolveException(f"Cannot resolve reference={dmref}")
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
