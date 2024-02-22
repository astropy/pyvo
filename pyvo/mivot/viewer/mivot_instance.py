# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
MivotClass keep as an attribute dictionary __dict__ all XML objects.
"""
from astropy import time
from pyvo.mivot.utils.vocabulary import unit_mapping
from pyvo.utils.prototype import prototype_feature
from pyvo.mivot.utils.mivot_utils import MivotUtils


@prototype_feature('MIVOT')
class MivotInstance:
    """
    MIVOT class is a dictionary (__dict__) with only essential information of the ModelViewerLevel3._dict.
    The dictionary keeps the hierarchy of the XML :
    "key" : {not a leaf} means key is the dmtype of an INSTANCE
    "key" : {leaf}       means key is the dmrole of an ATTRIBUTE
    "key" : "value"      means key is an element of ATTRIBUTE
    "key" : []           means key is the dmtype of a COLLECTION
    """
    def __init__(self, **instance_dict):
        """
        Constructor of the MIVOT class.
        Parameters
        ----------
        kwargs : dict
            Dictionary of the XML object.
        """
        self._create_class(**instance_dict)

    def _create_class(self, **kwargs):
        """
        Recursively initialize the MIVOT class with the dictionary of the XML object got in ModelViewerLevel3.
        For the unit of the ATTRIBUTE, we add the astropy unit or the astropy time equivalence by comparing
        the value of the unit with values in time.TIME_FORMATS.keys() which is the list of time formats.
        We do the same with the unit_mapping dictionary, which is the list of astropy units.
        Parameters
        ----------
        kwargs : dict
            Dictionary of the XML object.
        """
        for key, value in kwargs.items():
            if isinstance(value, list):  # COLLECTION
                setattr(self, self._remove_model_name(key), [])
                for item in value:
                    getattr(self, self._remove_model_name(key)).append(MivotInstance(**item))
            elif isinstance(value, dict):  # INSTANCE
                if not self._is_leaf(**value):
                    setattr(self, self._remove_model_name(key, True), MivotInstance(**value))
                if self._is_leaf(**value):
                    setattr(self, self._remove_model_name(key), MivotInstance(**value))
            else:  # ATTRIBUTE
                if key == 'value':  # We cast the value read in the row
                    setattr(self, self._remove_model_name(key),
                            MivotUtils.cast_type_value(value, getattr(self, 'dmtype')))
                else:
                    setattr(self, self._remove_model_name(key), self._remove_model_name(value))
                if key == 'unit':  # We convert the unit to astropy unit or to astropy time format if possible
                    # The first Vizier implementation used mas/year for the mapped pm unit: let's correct it
                    value = value.replace("year", "yr") if value else None
                    if value in unit_mapping.keys():
                        setattr(self, "astropy_unit", unit_mapping[value])
                    elif value in time.TIME_FORMATS.keys():
                        setattr(self, "astropy_unit_time", value)

    def update(self, row, ref=None):
        """
        Update the MIVOT class with the new data row.
        For each leaf of the MIVOT class, we update the value with the new data row, comparing the reference.
        Parameters
        ----------
        row : astropy.table.row.Row
            The new data row.
        ref : str, optional
            The reference of the data row, default is None.
        """
        for key, value in vars(self).items():
            if isinstance(value, list):
                for item in value:
                    item.update(row=row)
            elif isinstance(value, MivotInstance):
                if isinstance(vars(value), dict):
                    if 'value' not in vars(value):
                        value.update(row=row)
                    if 'value' in vars(value):
                        value.update(row=row, ref=getattr(value, 'ref'))
            else:
                if key == 'value':
                    if ref is not None and ref != 'null':
                        setattr(self, self._remove_model_name(key),
                                MivotUtils.cast_type_value(row[ref], getattr(self, 'dmtype')))

    @staticmethod
    def _remove_model_name(value, role_instance=False):
        """
        Remove the model name before each colon ":" as well as the type of the object before each point ".".
        If it is an INSTANCE of INSTANCEs, the dmrole represented as the key needs to keep his type object.
        In this case (`role_instance=True`), we just replace the point "." With an underscore "_".
        Parameters
        ----------
        value : str
            The string to process.
        role_instance : bool, optional
            If True, keeps the type object for dmroles representing an INSTANCE of INSTANCEs.
            Default is False.
        """
        if isinstance(value, str):
            # We first find the model_name before the colon
            index_underscore = value.find(":")
            if index_underscore != -1:
                # Then we find the object type before the point
                next_index_underscore = value.find(".", index_underscore + 1)
                if next_index_underscore != -1 and role_instance is False:
                    value_after_underscore = value[next_index_underscore + 1:]
                else:
                    value_after_underscore = (value[index_underscore + 1:]
                                              .replace(':', '_').replace('.', '_'))
                return value_after_underscore
            return value  # Returns unmodified string if "_" wasn't found
        else:
            return value

    def _is_leaf(self, **kwargs):
        """
        Check if the dictionary is an ATTRIBUTE.
        Parameters
        ----------
        **kwargs : dict
            The dictionary to check.
        Returns
        -------
        bool
            True if the dictionary is an ATTRIBUTE, False otherwise.
        """
        if isinstance(kwargs, dict):
            for _, value in kwargs.items():
                if isinstance(value, dict):
                    return False
        return True

    def display_class_dict(self, obj, classkey=None):
        """
        Recursively displays a serializable dictionary.
        This function is only used for debugging purposes.
        Parameters
        ----------
        obj : dict or object
            The dictionary or object to display.
        classkey : str, optional
            The key to use for the object's class name in the dictionary, default is None.
        Returns
        -------
        dict or object
            The serializable dictionary representation of the input.
        """
        if isinstance(obj, dict):
            data = {}
            for (k, v) in obj.items():
                data[k] = self.display_class_dict(v, classkey)
            return data
        elif hasattr(obj, "_ast"):
            return self.display_class_dict(obj._ast())
        elif hasattr(obj, "__iter__") and not isinstance(obj, str):
            return [self.display_class_dict(v, classkey) for v in obj]
        elif hasattr(obj, "__dict__"):
            data = dict([(key, self.display_class_dict(value, classkey))
                         for key, value in obj.__dict__.items()
                         if not callable(value) and not key.startswith('_')])
            if classkey is not None and hasattr(obj, "__class__"):
                data[classkey] = obj.__class__.__name__
            return data
        else:
            return obj
        

