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
    """
    Check if any key in the key_set starts with the searched_key.

    Parameters
    ----------
    searched_key : str
        The key to search for.
    key_set : str, list, or odict_keys
        The set of keys to check.

    Returns
    -------
    str or None
        The matched key if found, otherwise None.
    """
    if isinstance(key_set, str):
        return key_set.startswith(searched_key)
    else:
        # May be a list or an odict_keys
        for key in key_set:
            if key.startswith(searched_key) is True:
                return key
    return None
