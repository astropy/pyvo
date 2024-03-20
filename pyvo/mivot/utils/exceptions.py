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


class ResourceNotFound(Exception):
    """
    Exception raised if any kind of Resource is not found.
    """


class MivotElementNotFound(Exception):
    """
    Exception raised if any kind of Mivot Element is not found such as:
    - TEMPLATES
    - INSTANCE
    - COLLECTION
    - ATTRIBUTE
    - Element of ATTRIBUTE (dmtype, dmrole, value, ref)
    """


class MivotNotFound(Exception):
    """
    Exception raised if the MIVOT block can't be found.
    """


class ResolveException(Exception):
    """
    Exception raised if the reference can't be resolved.
    """


class DataFormatException(Exception):
    """
    Exception raised if the format is wrong.
    """


class NotImplementedException(Exception):
    """
    Exception raised if an un-implemented feature is invoked.
    """


class AstropyVersionException(Exception):
    """
    Exception raised if the version of astropy is not compatible with MIVOT.
    """
