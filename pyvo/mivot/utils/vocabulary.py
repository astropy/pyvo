"""
MIVOT vocabulary.
"""
from pyvo.utils import prototype_feature


@prototype_feature('MIVOT')
class Ele:
    """
    Constant used to identify MIVOT Element
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
class Att:
    """
    Constant used to identify attributes in MIVOT Element
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
    primarykey = "PRIMARY_KEY"
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
