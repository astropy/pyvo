"""
Created on 30 août 2021

author: michel
"""
from pyvo.utils import prototype_feature


@prototype_feature('MIVOT')
class Ele(object):
    """
    classdocs
    """
    namespace = ""
    VODML = namespace + "VODML"    
    MODEL = namespace + "MODEL"    
    GLOBALS = namespace + "GLOBALS"    
    TEMPLATES = namespace + "TEMPLATES"
    INSTANCE = namespace + "INSTANCE"
    ATTRIBUTE = namespace + "ATTRIBUTE"
    COLLECTION = namespace + "COLLECTION"
    JOIN = namespace + "JOIN"
    REFERENCE = namespace + "REFERENCE"
    WHERE = namespace + "WHERE"
    NOROLE = "NOROLE"


@prototype_feature('MIVOT')
class Att(object):
    """
    classdocs
    """
    dmrole = "dmrole"
    dmtype = "dmtype"
    dmid = "dmid"
    name = "name"
    value = "value"
    dmref = "dmref"
    tableref = "tableref"
    sourceref = "sourceref"
    ref = "ref"
    primarykey = "primarykey"
    foreignkey = "foreignkey"


@prototype_feature('MIVOT')
def key_match(searched_key, key_set):
    if isinstance(key_set, str):
        return key_set.startswith(searched_key)
    else:
        # May be a list or an odict_keys
        for key in key_set:
            if key.startswith(searched_key) is True:
                return key
    return None
