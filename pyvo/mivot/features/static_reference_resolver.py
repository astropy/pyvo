"""
Class used to resolve each static REFERENCE found in instance.
"""
from copy import deepcopy
from pyvo.mivot.utils.exceptions import ResolveException, NotImplementedException
from pyvo.mivot.utils.xpath_utils import XPath
from pyvo.utils.prototype import prototype_feature


@prototype_feature('MIVOT')
class StaticReferenceResolver:
    """
    Namespace for the function processing the static REFERENCEs
    """
    @staticmethod
    def resolve(annotation_seeker, templates_ref, instance):
        """
        Resolve all static REFERENCEs found in the instance.
        The referenced objects are first searched in GLOBALS and then in the templates_ref table.
        REFERENCE elements are replaced with the referenced objects set with the roles of the REFERENCEs.
        Works even if REFERENCE tags are numbered by the former processing.
        Parameters
        ----------
        annotation_seeker : AnnotationSeeker
            Utility to extract desired elements from the mapping block.
        templates_ref : str
            Identifier of the table where the instance comes from.
        instance : xml.etree.ElementTree
            The XML element object.
        Returns
        -------
        int
            The number of references resolved.
        Raises
        ------
        MappingException
            If the reference cannot be resolved.
        NotImplementedException
            If the reference is dynamic.
        """
        retour = 0
        for ele in XPath.x_path_startwith(instance, './/REFERENCE_'):
            dmref = ele.get("dmref")
            # If we have no @dmref in REFERENCE, we consider this is a ref based on a keys
            if dmref is None:
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
            # If the reference is within a collection: no role
            if ele.get('dmrole'):
                target_copy.attrib["dmrole"] = ele.get('dmrole')
            parent_map = {c: p for p in instance.iter() for c in p}
            parent = parent_map[ele]
            # Insert the referenced object
            parent.append(target_copy)
            # Drop the reference
            parent.remove(ele)
            retour += 1
        return retour
