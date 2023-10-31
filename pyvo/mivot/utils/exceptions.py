"""
Created on 11 Dec 2021

@author: laurentmichel
"""
from pyvo.utils import prototype_feature


@prototype_feature('MIVOT')
class MappingException(Exception):
    pass


class NotImplementedException(Exception):
    pass


class ResourceNotFound(Exception):
    pass


class MivotNotFound(Exception):
    pass
