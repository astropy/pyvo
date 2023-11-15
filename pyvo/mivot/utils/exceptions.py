"""
MIVOT Exceptions.
"""
from pyvo.utils import prototype_feature


@prototype_feature('MIVOT')
class MappingException(Exception):
    """
    Exception raised if a Resource or MIVOT element can't be mapped for one of these reasons:
    - It doesn't match with any Resource/MIVOT element expected.
    - It matches with too many Resource/MIVOT elements than expected.
    """
    pass


class ResourceNotFound(Exception):
    """
    Exception raised if any kind of Resource is not found.
    """
    pass


class MivotElementNotFound(Exception):
    """
    Exception raised if any kind of Mivot Element is not found such as:
    - TEMPLATES
    - INSTANCE
    - COLLECTION
    - ATTRIBUTE
    - Element of ATTRIBUTE (dmtype, dmrole, value, ref)
    """
    pass


class MivotNotFound(Exception):
    """
    Exception raised if the MIVOT block can't be found.
    """
    pass


class ResolveException(Exception):
    """
    Exception raised if the reference can't be resolved.
    """
    pass


class DataFormatException(Exception):
    """
    Exception raised if the format is wrong.
    """
    pass


class NotImplementedException(Exception):
    """
    Exception raised if an un-implemented feature is invoked.
    """
    pass
